# copied from: https://stackoverflow.com/questions/11874767/how-do-i-plot-in-real-time-in-a-while-loop-using-matplotlib

###################################################################
#                                                                 #
#                     PLOTTING A LIVE GRAPH                       #
#                  ----------------------------                   #
#            EMBED A MATPLOTLIB ANIMATION INSIDE YOUR             #
#            OWN GUI!                                             #
#                                                                 #
###################################################################


import sys
import os
from PyQt5 import QtGui, QtWidgets
from PyQt5 import QtCore
import functools
import numpy as np
import random as rd
import matplotlib
matplotlib.use("Qt4Agg")
from matplotlib.figure import Figure
from matplotlib.animation import TimedAnimation
from matplotlib.lines import Line2D
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
import time
import threading
from os.path import join, dirname
image_path = join(join(dirname(__file__), '..'), 'webapp', 'public', 'img')



def setCustomSize(x, width, height):
    sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
    sizePolicy.setHorizontalStretch(0)
    sizePolicy.setVerticalStretch(0)
    sizePolicy.setHeightForWidth(x.sizePolicy().hasHeightForWidth())
    x.setSizePolicy(sizePolicy)
    x.setMinimumSize(QtCore.QSize(width, height))
    x.setMaximumSize(QtCore.QSize(width, height))

''''''


class CustomMainWindow(QtWidgets.QMainWindow):

    def __init__(self):

        super(CustomMainWindow, self).__init__()

        # Define the geometry of the main window
        self.setGeometry(300, 300, 800, 400)
        self.setWindowTitle("Realtime EEG Analysis")

        # Create FRAME_A
        self.FRAME_A = QtWidgets.QFrame(self)
        self.FRAME_A.setStyleSheet("QWidget { background-color: %s }" % QtGui.QColor(210, 210, 235, 255).name())
        self.LAYOUT_A = QtWidgets.QGridLayout()
        self.FRAME_A.setLayout(self.LAYOUT_A)
        self.setCentralWidget(self.FRAME_A)

        # Place the zoom button
        # self.zoomBtn = QtWidgets.QPushButton(text = 'zoom')
        # setCustomSize(self.zoomBtn, 100, 50)
        # self.zoomBtn.clicked.connect(self.zoomBtnAction)
        # self.LAYOUT_A.addWidget(self.zoomBtn, *(1,0))

        # Quit button
        self.quit_button = QtWidgets.QPushButton(text='Quit')
        setCustomSize(self.quit_button, 100, 50)
        self.quit_button.clicked.connect(self.quit_button_action)
        self.LAYOUT_A.addWidget(self.quit_button, *(2, 0))

        # # record/record finish button
        self.record_button = QtWidgets.QPushButton(text='Start Record')
        setCustomSize(self.record_button, 100, 50)
        self.record_button.clicked.connect(self.record_button_action)
        self.LAYOUT_A.addWidget(self.record_button, *(2, 1))

        # sys.exit()

        # Add Text emotion
        self.emotion_picture = QtWidgets.QLabel()
        setCustomSize(self.emotion_picture, 200, 200)
        self.LAYOUT_A.addWidget(self.emotion_picture, *(0, 0))

        # self.emotion_label = QtWidgets.QLabel()
        # setCustomSize(self.emotion_label, 200, 200)
        # self.LAYOUT_A.addWidget(self.emotion_label, *(1, 0))



        # Place the matplotlib figure
        self.myFig = CustomFigCanvas('Arousal')
        self.LAYOUT_A.addWidget(self.myFig, *(0, 1))

        self.myFig2 = CustomFigCanvas('Valence')
        self.LAYOUT_A.addWidget(self.myFig2, *(1, 1))

        self.emotion_dict = {
            1: "fear - nervous - stress - tense - upset",
            2: "happy - alert - excited - elated",
            3: "relax - calm - serene - contented",
            4: "sad - depressed - lethargic - fatigue",
            5: "neutral"
        }

        self.record = False


        # Add the callbackfunc to ..
        # myDataLoop = threading.Thread(name='myDataLoop', target=run_process, daemon=True, args=(self.addData_callbackFunc,))
        # myDataLoop.start()
        # im = Image.open('Penguins.jpg')
        # im = im.convert("RGBA")
        # data = im.tobytes("raw", "RGBA")
        # qim = QtGui.QImage(data, im.size[0], im.size[1], QtGui.QImage.Format_ARGB32)
        # pix = QtGui.QPixmap.fromImage(qim)

        self.show()

    ''''''


    def zoomBtnAction(self):
        print("zoom in")
        self.myFig.zoomIn(5)

    def quit_button_action(self):
        sys.exit()

    def record_button_action(self):
        # print('record')
        self.record = not self.record
        if self.record:
            self.record_button.setText('Stop Recording')
        else:
            self.record_button.setText('Start Record')

    ''''''

    def addData_callbackFunc(self, value):
        # print("Add data: " + str(value))

        final_emotion = self.emotion_dict[value[-1]]

        self.myFig.addData(value[0])
        self.myFig2.addData(value[1])
        # self.myFig3.addData(value[2])
        # self.emotion_label.setText(str(final_emotion))
        pixmap = QtGui.QPixmap(join(image_path, str(int(value[-1])) + '.png'))
        pixmap = pixmap.scaledToWidth(200)
        pixmap = pixmap.scaledToHeight(200)
        # pixmap.scaled(200, 200, QtCore.Qt.KeepAspectRatio)
        self.emotion_picture.setPixmap(pixmap)

    def get_record_status(self):
        return self.record




''' End Class '''


class CustomFigCanvas(FigureCanvas, TimedAnimation):

    def __init__(self, title):

        self.addedData = []
        print(matplotlib.__version__)

        # The data
        self.xlim = 200
        self.n = np.linspace(0, self.xlim - 1, self.xlim)
        a = []
        b = []
        a.append(2.0)
        a.append(4.0)
        a.append(2.0)
        b.append(4.0)
        b.append(3.0)
        b.append(4.0)
        self.y = (self.n * 0.0) + 50

        # The window
        self.fig = Figure(figsize=(5,5), dpi=100)
        self.ax1 = self.fig.add_subplot(111)
        self.ax1.set_title(title)


        # self.ax1 settings
        self.ax1.set_xlabel('time')
        self.ax1.set_ylabel('raw data')
        self.line1 = Line2D([], [], color='blue')
        self.line1_tail = Line2D([], [], color='red', linewidth=2)
        self.line1_head = Line2D([], [], color='red', marker='o', markeredgecolor='r')
        self.ax1.add_line(self.line1)
        self.ax1.add_line(self.line1_tail)
        self.ax1.add_line(self.line1_head)
        self.ax1.set_xlim(0, self.xlim - 1)
        self.ax1.set_ylim(3800, 4400)

        # self.title = title


        FigureCanvas.__init__(self, self.fig)
        TimedAnimation.__init__(self, self.fig, interval = 50, blit = True)

    def new_frame_seq(self):
        return iter(range(self.n.size))

    def _init_draw(self):
        lines = [self.line1, self.line1_tail, self.line1_head]
        for l in lines:
            l.set_data([], [])

    def addData(self, value):
        self.addedData.append(value)

    def zoomIn(self, value):
        bottom = self.ax1.get_ylim()[0]
        top = self.ax1.get_ylim()[1]
        bottom += value
        top -= value
        self.ax1.set_ylim(bottom,top)
        self.draw()


    def _step(self, *args):
        # Extends the _step() method for the TimedAnimation class.
        try:
            TimedAnimation._step(self, *args)
        except Exception as e:
            self.abc += 1
            print(str(self.abc))
            TimedAnimation._stop(self)
            pass

    def _draw_frame(self, framedata):
        margin = 2
        while(len(self.addedData) > 0):
            self.y = np.roll(self.y, -1)
            self.y[-1] = self.addedData[0]
            del(self.addedData[0])


        self.line1.set_data(self.n[ 0 : self.n.size - margin ], self.y[ 0 : self.n.size - margin ])
        self.line1_tail.set_data(np.append(self.n[-10:-1 - margin], self.n[-1 - margin]), np.append(self.y[-10:-1 - margin], self.y[-1 - margin]))
        self.line1_head.set_data(self.n[-1 - margin], self.y[-1 - margin])
        self._drawn_artists = [self.line1, self.line1_tail, self.line1_head]



''' End Class '''


# You need to setup a signal slot mechanism, to
# send data to your GUI in a thread-safe way.
# Believe me, if you don't do this right, things
# go very very wrong..
class Communicate(QtCore.QObject):
    # data_signal = QtCore.pyqtSignal(float)
    data_signal = QtCore.pyqtSignal(np.ndarray)

''' End Class '''



def dataSendLoop(addData_callbackFunc):
    # Setup the signal-slot mechanism.
    mySrc = Communicate()
    mySrc.data_signal.connect(addData_callbackFunc)

    # Simulate some data
    n = np.linspace(0, 499, 500)
    y = 50 + 25*(np.sin(n / 8.3)) + 10*(np.sin(n / 7.5)) - 5*(np.sin(n / 1.5))
    i = 0

    while(True):
        if(i > 499):
            i = 0
        time.sleep(0.001)
        mySrc.data_signal.emit(y[i]) # <- Here you emit a signal!
        i += 1
    ###
###


def draw_graph(run_process=dataSendLoop):
    app = QtWidgets.QApplication(sys.argv)
    QtWidgets.QApplication.setStyle(QtWidgets.QStyleFactory.create('Plastique'))
    # myGUI = CustomMainWindow(run_process)
    myGUI = CustomMainWindow()
    myDataLoop = threading.Thread(name='myDataLoop', target=run_process, daemon=True, args=(myGUI.addData_callbackFunc,))
    myDataLoop.start()

    sys.exit(app.exec_())
    # return myGUI



if __name__== '__main__':
    # app = QtWidgets.QApplication(sys.argv)
    # QtWidgets.QApplication.setStyle(QtWidgets.QStyleFactory.create('Plastique'))
    # myGUI = CustomMainWindow()
    #
    #
    # sys.exit(app.exec_())

    draw_graph()

''''''