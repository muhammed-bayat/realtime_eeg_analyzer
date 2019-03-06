from keras.layers import Multiply, Dense, Permute, Lambda, Input, Dropout, Reshape, Flatten, Conv1D, \
    BatchNormalization, Activation

# from keras.layers.core import *
from keras.models import Model
import tensorflow as tf
import keras.backend.tensorflow_backend as K
from keras import optimizers
from neural_network.utils.lr_controller import LrReducer
from neural_network.utils.custom_function import ScoreActivationFromSigmoid, GetPadMask, GetCountNonZero


# Best Working for Fourier Transform version
class AttentionScoreFourierTransform:
    def __init__(self, input_shape, output_labels, gpu=0):
        with K.tf.device('/gpu:' + str(gpu)):
            inputs = Input(shape=input_shape)

            num_attentions = 64
            num_neurons = 128

            m = inputs
            mask = Lambda(lambda x: GetPadMask(x))(m)
            nonzero_mask_count = Lambda(lambda x: GetCountNonZero(x))(mask)

            m = Dense(num_neurons, activation='relu')(m)
            m = Dropout(0.7)(m)

            all_final_scores = list()
            for label_score in output_labels:
                _m = Dense(num_attentions, activation=ScoreActivationFromSigmoid)(m)  # n attentions
                _m = Multiply()([mask, _m])
                _m = Multiply()([_m, nonzero_mask_count])

                _m = Permute((2, 1))(_m)

                _m = Lambda(lambda x: K.sum(x, axis=2))(_m)  # each attention's average

                _m = Reshape((num_attentions, 1))(_m)
                final_score = Lambda(lambda x: K.mean(x, axis=1, keepdims=True))(
                    _m)  # average of all attention's averages
                #                 final_score = Multiply(name=label_score)([final_score, Lambda(lambda x: K.ones_like(x))(final_score)])
                final_score = Flatten(name=label_score)(final_score)
                all_final_scores.append(final_score)

            model = Model(inputs=inputs, outputs=all_final_scores)

        losses = {'amusement': 'mean_squared_error',
                  'immersion': 'mean_squared_error',
                  'difficulty': 'mean_squared_error',
                  'emotion': 'mean_squared_error'}
        loss_weights = {'amusement': 1.0, 'immersion': 1.0, 'difficulty': 1.0, 'emotion': 1.0}
        adam = optimizers.Adam(lr=0.001)
        model.compile(loss=losses, loss_weights=loss_weights, optimizer=adam, metrics=['accuracy'])

        self.model = model
        print(model.summary())

    def train(self, x_train, y_train, x_test, y_test, epochs=100, batch_size=128, verbose=1):
        print('##########')
        print('MLP Attention Test')
        print('##########')
        #         early_stopping = EarlyStopping(patience = 20)
        early_stopping = LrReducer(patience=5, reduce_rate=0.5, reduce_nb=3, verbose=1)
        self.model.fit(x_train, y_train, validation_data=(x_test, y_test), epochs=epochs, batch_size=batch_size,
                       verbose=verbose,
                       callbacks=[early_stopping])


# For rawdata
class AttentionScore:
    def __init__(self, input_shape, gpu=0):
        with K.tf.device('/gpu:' + str(gpu)):
            inputs = Input(shape=input_shape)

            num_attentions = 128
            num_filters = num_attentions  # used in conv1d
            kernel_size = 128 * 1
            strides = 128 * 1

            m = inputs
            m = Conv1D(num_filters, kernel_size=kernel_size, strides=strides, padding='valid', use_bias=False)(m)
            mask_conv = Lambda(lambda x: GetPadMask(x))(m)
            nonzero_mask_count = Lambda(lambda x: GetCountNonZero(x))(mask_conv)
            m = BatchNormalization()(m)
            # ACTIVATION RELU?
            m = Dense(num_filters)(m)
            # ACTIVATION RELU?
            #             m = Activation(ScoreActivationFromSigmoid)(m)
            #             m = Multiply()([mask_conv, m])
            #             m = Multiply()([m, nonzero_mask_count])

            m_attn = Permute((2, 1))(m)
            m_attn = Activation('softmax')(m_attn)
            m_attn = Permute((2, 1))(m_attn)
            m_attn = Lambda(lambda x: K.sum(x, axis=2, keepdims=True))(m_attn)

            m = Multiply()([m, m_attn])
            m = Dense(1)(m)  # or sum?
            m = Multiply()([m, mask_conv])
            #             m = Multiply()([m, nonzero_mask_count])
            m_attn2 = Reshape((600,))(m)
            m_attn2 = Activation('softmax')(m_attn2)
            m_attn2 = Reshape((600, 1))(m_attn2)
            m = Multiply()([m, m_attn2])
            m = Flatten()(m)
            final_scores = Dense(1, activation=ScoreActivationFromSigmoid)(m)

            model = Model(inputs=inputs, outputs=final_scores)

        adam = optimizers.Adam(lr=0.001)
        model.compile(loss='mean_squared_error', optimizer=adam, metrics=['accuracy'])

        self.model = model
        print(model.summary())

    def train(self, x_train, y_train, x_test, y_test, epochs=100, batch_size=128, verbose=1):
        print('##########')
        print('MLP Attention Test')
        print('##########')
        #         early_stopping = EarlyStopping(patience = 20)
        early_stopping = LrReducer(patience=5, reduce_rate=0.5, reduce_nb=3, verbose=1)
        self.model.fit(x_train, y_train, validation_data=(x_test, y_test), epochs=epochs, batch_size=batch_size,
                       verbose=verbose,
                       callbacks=[early_stopping])
