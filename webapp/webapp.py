""" webapp.py: To communicates with UI and Core logics """

__author__ = "Isaac Sim"
__copyright__ = "Copyright 2019, The Realtime EEG Analysis Project"
__credits__ = ["Isaac Sim"]
__license__ = ""
__version__ = "1.0.0"
__maintainer__ = ["Isaac Sim", "Dongjoon Jeon"]
__email__ = "gilgarad@igsinc.co.kr"
__status__ = "Development"

from flask import Flask, request, render_template
from flask_socketio import SocketIO
from socketIO_client import SocketIO as sSocketIO, LoggingNamespace
import numpy as np

from typing import Type
from dao_models.status_controller import StatusController
from dao_models.subject import Subject
from dao_models.trial import Trial

# app = Flask(__name__, template_folder='mdb_free_4.6.1')
app = Flask(__name__)
socketio = SocketIO(app)
app.config['SECRET_KEY'] = 'secret!'


@app.route('/', methods=['GET'])
def index():
    """ Web html root

    :return:
    """
    # return render_template('index.html')
    return render_template('index_demo.html')


# @socketio.on('update_data')
def send_to_html(send_type: int=0, data: dict=None):
    """ Send data to html

    :param send_type:
    :param data:
    :return:
    """
    # print('transmit!!')
    # data = {'username': 'isaacsim',
    #      'data': 'nothing'}

    if send_type == 0: # regular eeg data
        data = make_eeg_analyzed_data(data)
        namespace = '/update_data'
    elif send_type == 1: # headset connection status
        data = make_status_data()
        namespace = '/update_status'
    else:
        print('wrong type')
        return

    # print(data)
    # socketio.emit('notify', data, json=True, namespace=namespace)
    socketio.emit('response', data, json=True, namespace=namespace)
    # socket = sSocketIO('220.95.228.142', 8010, LoggingNamespace)
    # socket.emit('response', data, json=True, namespace=namespace)


def make_status_data():
    """ Builds up the status data

    :return:
    """
    data = {
        'headset': stat_controller.headset_status,
        'analysis': stat_controller.analyze_status,
        'battery_level': stat_controller.battery_level
    }
    # print('Battery Level:', stat_controller.battery_level)
    return data


def make_eeg_analyzed_data(data: dict):
    """ Builds up the eeg analyzed contents

    :param data:
    :return:
    """
    text_display_analysis = '일반분석 (3초 평균)' \
                            + '\n재미: ' + data['fun_stat'] \
                            + '\n몰입감: ' + data['immersion_stat'] \
                            + '\n난이도: ' + data['difficulty_stat'] \
                            + '\n감정: ' + data['emotion_stat']
    text_analysis_final = ''
    analyze_status = data['analyze_status']

    if analyze_status == 1:
        total_played_time = data['record_duration']
        text_display_analysis = text_display_analysis \
                                + '\n------------------------------------------------------------\n' \
                                + '게임 분석 중\n' \
                                + '플레이시간: ' + str(total_played_time) + 's' \
                                + '\n재미: ' + make_analysis_text(data['fun_stat_record'], total_played_time) \
                                + '\n몰입감: ' + make_analysis_text(data['immersion_stat_record'], total_played_time) \
                                + '\n난이도: ' + make_analysis_text(data['difficulty_stat_record'], total_played_time) \
                                + '\n감정: ' + make_analysis_text(data['emotion_stat_record'], total_played_time)

    elif analyze_status == 2:
        # print('final_score_pred:', data['final_score_pred'])
        total_played_time = data['record_duration']
        # text_display_analysis = (text_display_analysis
        #                          + '\n------------------------------------------------------------\n'
        #                            '게임 분석 종료\n'
        #                            '플레이시간: %is\n'
        #                            '재미: %s 최종점수(예측): %.2f'
        #                            '\n몰입감: %s 최종점수(예측): %.2f'
        #                            '\n난이도: %s 최종점수(예측): %.2f'
        #                            '\n감정: %s 최종점수(예측): %.2f') \
        #                         % (total_played_time,
        #                            make_analysis_text(data['fun_stat_record'], total_played_time),
        #                            data['final_score_pred'][0][0][0],
        #                            make_analysis_text(data['immersion_stat_record'], total_played_time),
        #                            data['final_score_pred'][1][0][0],
        #                            make_analysis_text(data['difficulty_stat_record'], total_played_time),
        #                            data['final_score_pred'][2][0][0],
        #                            make_analysis_text(data['emotion_stat_record'], total_played_time),
        #                            data['final_score_pred'][3][0][0])
        text_display_analysis = (text_display_analysis
                                 + '\n------------------------------------------------------------\n'
                                   '게임 분석 종료\n'
                                   '플레이시간: %is\n'
                                   '재미: %s'
                                   '\n몰입감: %s'
                                   '\n난이도: %s'
                                   '\n감정: %s') \
                                % (total_played_time,
                                   make_analysis_text(data['fun_stat_record'], total_played_time),
                                   make_analysis_text(data['immersion_stat_record'], total_played_time),
                                   make_analysis_text(data['difficulty_stat_record'], total_played_time),
                                   make_analysis_text(data['emotion_stat_record'], total_played_time))
        text_analysis_final = ('최종 점수 예측 결과'
                               '\n재미:       %.2f   (재미없음 1 ~ 재미있음 9)'
                               '\n몰입감:   %.2f   (몰입 안 됨 1 ~ 몰입됨 9)'
                               '\n난이도:   %.2f   (쉬움 1 ~ 어려움 9)'
                               '\n감정:       %.2f   (짜증 1 ~ 3 일반 4 ~ 6 즐거움 7 ~ 9)'
                               % (data['final_score_pred'][0][0][0],
                                  data['final_score_pred'][1][0][0],
                                  data['final_score_pred'][2][0][0],
                                  data['final_score_pred'][3][0][0]))

    emotion_mean = float((2 - np.mean(data['emotion_status'], axis=0)) / 2)

    # print(np.mean(data['fun_status'], axis=0), np.mean(data['immersion_status'], axis=0),
    #       np.mean(data['difficulty_status'], axis=0), emotion_mean)

    data = {
        'eeg_mean': np.mean(data['eeg_realtime'], axis=0),
        'eeg_channels': data['eeg_realtime'].tolist(),
        'is_connected': data['is_connected'],
        'connection_status': data['connection_status'],
        'arousal_mean': float((np.mean(data['arousal_all'], axis=0) - 1) / 2) * 9,
        'valence_mean': float((np.mean(data['valence_all'], axis=0) - 1) / 2) * 9,
        'fun_mean': float(np.mean(data['fun_status'], axis=0)),
        'immersion_mean': float(np.mean(data['immersion_status'], axis=0)),
        'difficulty_mean': float(np.mean(data['difficulty_status'], axis=0)),
        'emotion_mean': float(np.mean(data['emotion_status'], axis=0)),
        'analysis': text_display_analysis,
        'analysis_final': text_analysis_final
    }

    return data


# Listening Parts
@socketio.on('connect_headset')
def connect_headset(message: dict):
    """ Receives the connection status command from UI

    :param message:
    :return:
    """
    # print('request in!!')
    # print(message)
    if stat_controller.headset_status != 2:
        stat_controller.headset_status += 1
    else:
        stat_controller.headset_status = 0
        stat_controller.analyze_status = 0
    # print(stat_controller.headset_status)


@socketio.on('control_analysis')
def start_analysis(message: dict):
    """ Receives the analysis status command from UI

    :param message:
    :return:
    """
    # print(message)

    if stat_controller.analyze_status != 2:
        stat_controller.analyze_status += 1
    else:
        stat_controller.analyze_status += 1
        tr.trial_name = message['data']

    print('Analyze Status: ', stat_controller.analyze_status)
    print(tr.trial_name)


@socketio.on('final_scores')
def final_scores(message: dict):
    """ Receives the final scores(labels) from UI

    :param message:
    :return:
    """
    tr.survey_labels = message['data']


def set_status_controller(status_controller: StatusController,
                          subject: Subject, trial: Trial):
    """ DAO objects for sharing in this python file and realtime_emotion.py

    :param status_controller:
    :param subject:
    :param trial:
    :return:
    """
    global stat_controller, subj, tr
    stat_controller = status_controller
    subj = subject
    tr = trial


def make_analysis_text(data: dict, duration: int=0):
    """ Make analysis details with percentage information and its duration for each component

    :param data:
    :param duration:
    :return:
    """
    txt = ''

    total_count = 0
    for k, v in data.items():
        total_count += v

    for k, v in data.items():
        if total_count == 0:
            percentage = '0'
            final_duration = '0'
        else:
            percentage = str(int(v * 100 / total_count))
            final_duration = str(int(duration * v / total_count))
        if len(txt) == 0:
            txt = txt + str(k) + ' (' + percentage + '%, ' + final_duration + 's)'
        else:
            txt = txt + ' ' + str(k) + ' (' + percentage + '%, ' + final_duration + 's)'

    return txt
