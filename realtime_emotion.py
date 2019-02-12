import numpy as np

from socketIO_client import SocketIO, LoggingNamespace

from os.path import join
from datetime import datetime
from collections import Counter

import time
import threading

# Import implemented parts
from const import *
from system_shares import logger
from webapp.webapp import app, socketio, test_message, set_status_controller

from utils.live_plot import Communicate

from realtime_eeg.headset.emotiv import Emotiv
from realtime_eeg.analyze_eeg import AnalyzeEEG
from obj_models.subject import Subject
from obj_models.status_controller import StatusController
from obj_models.trial import Trial


# Tensorflow debug Log off
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'


class RealtimeEEGAnalyzer:
    def __init__(self, path="./Training Data/", save_path=None):

        self.path = path

        self.emotiv = Emotiv()
        self.status_controller = StatusController()
        self.subject = Subject()
        self.trial = Trial()
        self.analyze_eeg = AnalyzeEEG(self.path)

        self.socket_port = 8080
        self.save_path = save_path

        self.models = list()

    def connect_headset(self):
        self.emotiv.connect_headset()
        self.emotiv.login()
        self.emotiv.authorize()
        self.emotiv.query_headsets()
        self.emotiv.close_old_sessions()
        self.emotiv.create_session()
        self.emotiv.subscribe()

    def disconnect_headset(self):
        self.emotiv.unsubscribe()
        # self.emotiv.close_old_sessions()
        self.emotiv.logout()

    def load_model(self, path):

        # model1 = 'model_json_multiloss4_resnet18_fftstd_3class.json'
        # weight1 = 'model_weights_multiloss4_resnet18_fftstd_3class.h5'
        model1 = 'model_json_multiloss4_3seconds_resnet18_fftstd_2class_type1.json'
        weight1 = 'model_weights_multiloss4_3seconds_resnet18_fftstd_2class_type1.h5'
        model2 = 'model_json_multiloss4_3seconds_resnet18_fftstd_2class_type2.json'
        weight2 = 'model_weights_multiloss4_3seconds_resnet18_fftstd_2class_type2.h5'

        model_list = [[model1, weight1], [model2, weight2]]

        self.analyze_eeg.load_models(model_names=model_list)

    def send_result_to_application(self, emotion_class):
        """
        Send emotion predict to web app.
        Input: Class of emotion between 1 to 5 according to Russel's Circumplex Model.
        Output: Send emotion prediction to web app.
        """
        socket = SocketIO('localhost', self.socket_port, LoggingNamespace)
        socket.emit('realtime emotion', emotion_class)

    def run_process(self, addData_callbackFunc=None):

        if self.status_controller.analyze_status is not None:
            mySrc = Communicate()
            mySrc.data_signal.connect(addData_callbackFunc)
            transmit_data = mySrc.data_signal.emit
        else:
            transmit_data = addData_callbackFunc
            def dummy_func():
                return False
                self.status_controller.analyze_status = dummy_func

        self.load_model(self.path)

        number_of_channel = 14
        sampling_rate = 128
        count = 0
        realtime_eeg_in_second = 3  # Realtime each ... seconds
        number_of_realtime_eeg = sampling_rate * realtime_eeg_in_second

        channel_names = ["AF3", "F7", "F3", "FC5", "T7", "P7", "O1", "O2", "P8", "T8", "FC6", "F4", "F8", "AF4"]
        channel_names = np.array(channel_names)

        # original
        eeg_realtime = np.zeros((number_of_channel, number_of_realtime_eeg), dtype=np.double)

        response_records = list()
        fun_records = list()
        immersion_records = list()
        difficulty_records = list()
        emotion_records = list()

        time_counter = 0
        record_start_time = 0
        final_emotion = 5
        final_emotion2 = 0
        final_fun = 0
        final_immersion = 0
        final_difficulty = 0

        record_status = False
        connection_status = 0
        disconnected_list = list()
        num_frame_check = 16
        num_of_average = int(sampling_rate / num_frame_check)
        arousal_all = [2.0] * num_of_average
        valence_all = [2.0] * num_of_average
        fun_status = [0] * num_of_average
        immersion_status = [0] * num_of_average
        difficulty_status = [0] * num_of_average
        emotion_status = [0] * num_of_average

        # fun_stat_dict = {
        #     0: '지루함',
        #     1: '일반',
        #     2: '재미있음'
        # }

        fun_stat_dict = {
            0: '일반',
            1: '재미있음'
        }

        immersion_stat_dict = {
            0: '일반',
            1: '몰입됨'
        }

        difficulty_stat_dict = {
            0: '쉬움',
            1: '어려움'
        }

        emotion_stat_dict = {
            0: '즐거움',
            1: '일반',
            2: '짜증'
        }

        fun_accum = 0
        immersion_accum = 0
        difficulty_accum = 0
        emotion_accum = 0

        # Try to get if it has next step
        while self.emotiv.is_run:
            if not self.emotiv.is_connect and not self.status_controller.headset_status:
                # wait until connected
                # time.sleep(3)

                # send headset connection status
                continue
            elif not self.emotiv.is_connect and self.status_controller.headset_status:
                # connect
                self.connect_headset()
            elif self.emotiv.is_connect and not self.status_controller.headset_status:
                # disconnect
                print('disconnect !!')
                self.disconnect_headset()


            res = self.emotiv.retrieve_packet()
            current_time = datetime.now()
            # print(res)
            #     res_result.append(res)

            if 'eeg' in res:
                new_data = res['eeg'][3: 3 + number_of_channel]
                eeg_realtime = np.insert(eeg_realtime, number_of_realtime_eeg, new_data, axis=1)
                eeg_realtime = np.delete(eeg_realtime, 0, axis=1)

                if record_status:
                    new_data = [current_time]
                    new_data.append(res['time'])
                    new_data.extend(res['eeg'])
                    # print(new_data)
                    response_records.append(new_data)

                count += 1

                # print('eeg')
            elif 'dev' in res:
                # signal quality 0 None, 1 bad to 4 good
                cnt = 0
                disconnected_list = list()
                for idx, i in enumerate(res['dev'][2]):
                    if i > 0:
                        cnt += 1
                    else:
                        disconnected_list.append(idx)
                connection_status = int(float(cnt / 14) * 100)

                # print('connection status:', connection_status)
                # print(res)

            elif 'error' in res:
                print(res)

                break
            else:
                # print(res)
                continue
                # break

            if count % num_frame_check == 0:
                emotion_class, class_ar, class_va, fun, difficulty, immersion, emotion = self.analyze_eeg.analyze_eeg_data(eeg_realtime)

                if len(valence_all) == num_of_average:
                    valence_all.pop(0)
                    arousal_all.pop(0)
                    fun_status.pop(0)
                    difficulty_status.pop(0)
                    immersion_status.pop(0)
                    emotion_status.pop(0)

                # temp
                arousal_all.append(class_ar)
                valence_all.append(class_va)
                fun_status.append(fun)
                difficulty_status.append(difficulty)
                immersion_status.append(immersion)
                emotion_status.append(emotion)

                # draw graph
                d = eeg_realtime[:, number_of_realtime_eeg - 1]
                # d = np.concatenate([[final_emotion], [connection_status]], axis=0)
                # d = np.concatenate([[final_emotion], [connection_status], [disconnected_list]], axis=0)
                d = {
                    'eeg_realtime': d,
                    'final_emotion': final_emotion,
                    'connection_status': connection_status,
                    'disconnected_list': channel_names[disconnected_list],
                    'arousal_all': np.array(arousal_all),
                    'valence_all': np.array(valence_all),
                    'fun_stat': fun_stat_dict[final_fun],
                    'immersion_stat': immersion_stat_dict[final_immersion],
                    'difficulty_stat': difficulty_stat_dict[final_difficulty],
                    'emotion_stat': emotion_stat_dict[final_emotion2],
                    'fun_stat_record': self.counter(fun_records, fun_stat_dict),
                    'immersion_stat_record': self.counter(immersion_records, immersion_stat_dict),
                    'difficulty_stat_record': self.counter(difficulty_records, difficulty_stat_dict),
                    'emotion_stat_record': self.counter(emotion_records, emotion_stat_dict),
                    'fun_records': fun_records,
                    'immersion_records': immersion_records,
                    'difficulty_records': difficulty_records,
                    'emotion_records': emotion_records,
                    'record_start_time': record_start_time,
                    'fun_accum': fun_accum,
                    'immersion_accum': immersion_accum,
                    'difficulty_accum': difficulty_accum,
                    'emotion_accum': emotion_accum,
                    'is_connected': self.emotiv.is_connect,
                    'fun_status': fun_status,
                    'immersion_status': immersion_status,
                    'difficulty_status': difficulty_status,
                    'emotion_status': emotion_status,
                    'is_analysis': record_status
                }
                transmit_data(d)

            # print('Record status %r' % self.status_controller.analyze_status)
            if self.status_controller.analyze_status and record_status is False:
                record_status = True
                response_records = list()
                emotion_records = list()
                fun_records = list()
                difficulty_records = list()
                immersion_records = list()
                record_start_time = datetime.now()
            elif not self.status_controller.analyze_status and record_status is True:
                record_status = False
                response_records = self.save_data(data=response_records, save_path=self.save_path,
                                         filename=self.trial.trial_name, time_counter=time_counter)
                record_start_time = 0
                time_counter += 1

            if count == sampling_rate:
                emotion_dict = {
                    1: "fear - nervous - stress - tense - upset",
                    2: "happy - alert - excited - elated",
                    3: "relax - calm - serene - contented",
                    4: "sad - depressed - lethargic - fatigue",
                    5: "neutral"
                }
                class_ar = np.round(np.mean(arousal_all))
                class_va = np.round(np.mean(valence_all))

                emotion_class = self.analyze_eeg.fft_conv.determine_emotion_class(class_ar, class_va)
                final_emotion = emotion_class
                final_emotion2 = self.most_common(emotion_status, final_emotion2)
                final_difficulty = self.most_common(difficulty_status, final_difficulty)
                final_fun = self.most_common(fun_status, final_fun)
                final_immersion = self.most_common(immersion_status, final_immersion)

                if final_fun == 2:
                    fun_accum += 1
                elif fun_accum != 0:
                    fun_accum -= 1

                if final_immersion == 1:
                    immersion_accum += 1
                elif immersion_accum != 0:
                    immersion_accum -= 1

                if final_emotion == 2:
                    emotion_accum += 1
                elif emotion_accum != 0:
                    emotion_accum -= 1

                if final_difficulty == 1:
                    difficulty_accum += 1
                elif difficulty_accum != 0:
                    difficulty_accum -= 1

                if record_status:
                    emotion_records.append(final_emotion2)
                    fun_records.append(final_fun)
                    difficulty_records.append(final_difficulty)
                    immersion_records.append(final_immersion)

                count = 0

        self.emotiv.ws.close()

    def most_common(self, target_list, last_status):
        a = Counter(target_list).most_common(2)
        final_status = int(a[0][0])
        if len(a) != 1 and a[0][1] == a[1][1]:
            if int(a[0][0]) == last_status or int(a[1][0]) == last_status:
                final_status = last_status
        return final_status

    def counter(self, data, data_dict):
        counter_dict = dict()
        data = [str(d) for d in data]
        data = Counter(data)
        for k, v in data_dict.items():
            counter_dict[v] = data[str(k)]

        return counter_dict

    def extract_channels(self, signals):
    
        signals = signals[:, 7:]
    
        return signals

    def run_process2(self, test_path):
        #
        number_of_channel = 14
        sampling_rate = 128
        time_interval = 0.001
        show_interval = 10
        is_first = True
        num_channels = 14
        realtime_eeg_in_second = 5  # Realtime each ... seconds
        number_of_realtime_eeg = sampling_rate * realtime_eeg_in_second
    
        eeg_from_file = np.load(test_path) # shape: number_of_realtime_eeg * 20(EEG channels + alpha)
    
        if eeg_from_file.shape[1] != 14:
            eeg = self.extract_channels(eeg_from_file)
        else:
            eeg = eeg_from_file
    
        eeg = eeg.T
    
        for i in range(0, eeg.shape[1], number_of_realtime_eeg):
            self.analyze_eeg_data(eeg[:,i:i+number_of_realtime_eeg])

    def save_data(self, data, save_path, filename, time_counter):
        # print(save_path)
        if save_path is not None:
            # np.save(join(save_path, str(time_counter)), data)
            np.save(join(save_path, filename), data)

        return list()


if __name__ == '__main__':
    # print('First Argument', sys.argv[1])
    # parser = argparse.ArgumentParser()
    # parser.add_argument('--realtime', type=lambda x: (str(x).lower() == 'true'), default=True)
    # parser.add_argument('--test_path', type=str, default=None)
    # args = parser.parse_args()
    # realtime = args.realtime
    # test_path = args.test_path
    config = json.load(open(join('.', 'config', 'system_config.json')))
    test_path = config['test_path']
    save_path = config['save_path']
    # print(test_path)

    # print("Starting webapp...")
    # threading.Thread(target=execute_js, args=('./webapp/index.js', )).start()
    # success = execute_js('./webapp/index.js')

    logger.info("Starting realtime emotion engine...")

    realtime_eeg_analyzer = RealtimeEEGAnalyzer(save_path=save_path)
    set_status_controller(realtime_eeg_analyzer.status_controller, realtime_eeg_analyzer.subject,
                          realtime_eeg_analyzer.trial)

    th = threading.Thread(name='myDataLoop', target=realtime_eeg_analyzer.run_process, daemon=True,
                          args=(test_message, ))
    th.start()
    # draw_graph(run_process=realtime_eeg_analyzer.run_process)

    # app.run(host=HOST, port=PORT, debug=True, threaded=False)
    socketio.run(app, host=HOST, port=PORT, debug=True)




