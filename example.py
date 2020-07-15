from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.behaviors import ButtonBehavior

from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.properties import (
    NumericProperty, ReferenceListProperty, ObjectProperty, StringProperty, BooleanProperty
)
from kivy.config import Config
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
from kivy.uix.textinput import TextInput

import cv2
import numpy as np
import datetime
import os
import time

frameRate = 8.0

class ImageButton(ButtonBehavior, Image):
    pass

class Video(Widget):
    # To be used for the first camera
    capture1 = ObjectProperty(None)

    recording = BooleanProperty(False)
    recorder = ObjectProperty(None)
    # To be used for the second camera
    # capture2 = ObjectProperty(None)

    brightness = NumericProperty(0)
    contrast = NumericProperty(1.0)
    zoom = NumericProperty(1)

    # filter states
    #####################
    noiseState = BooleanProperty(False)
    borderState = BooleanProperty(False)
    clusterState = BooleanProperty(False)
    thresholdState = BooleanProperty(False)
    invertState = BooleanProperty(False)
    #####################

    # Used in kMeans clustering
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    nmbrClusters = 6

    # full screen video state (on_release is fullscreenStream, needs implementation)
    fullscreenState = BooleanProperty(False)
    # power buttons states (on_release is power, needs implementation)
    powerState = BooleanProperty(False)

    picSaveFolder = os.path.join(os.path.dirname(os.path.realpath(__file__)),"capturedImages")
    videoSaveFolder = os.path.join(os.path.dirname(os.path.realpath(__file__)),"recordedVideos")
    lastImageDir = os.path.join(picSaveFolder, "cover.jpg")

    def __init__(self, *args, **kwargs):
        super(Video, self).__init__(*args, **kwargs)
        brightnessSlider = self.ids['brightnessSlider']
        brightnessSlider.fbind('value', self.onBrightnessChange)
        contrastSlider = self.ids['contrastSlider']
        contrastSlider.fbind('value', self.onContrastChange)
        contrastSlider = self.ids['zoomSlider']
        contrastSlider.fbind('value', self.onZoomChange)


    def update(self, dt):
        img1 = self.ids['videoFrame']

        # print(time.time())
        # display image from cam in opencv window
        _, frame = self.capture1.read()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        frame[:,:,2] = np.clip(np.rint(self.contrast * frame[:,:,2] + self.brightness), 0, 255)
        frame = cv2.cvtColor(frame, cv2.COLOR_HSV2BGR)

        # print(frame.shape[0], frame.shape[1])
        frame = self.applyFilters(frame)
        if(self.recording == True):
            self.recorder.write(frame)

        if(self.zoom > 1):
            frame = self.zoomFrame(frame)
            
        buf1 = cv2.flip(frame, 0)
        buf = buf1.tobytes()
        texture1 = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
        texture1.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')

        # display image from the texture
        img1.texture = texture1

    def applyFilters(self, frame):

        if self.noiseState == True:
            # good for salt and pepper noise, Panos suggested this made the most sense
            frame = cv2.medianBlur(frame, 7)

        if self.borderState == True:
            frameBW = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frameBW = cv2.adaptiveThreshold(frameBW,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,\
            cv2.THRESH_BINARY,11,2)
            frameBW = cv2.cvtColor(frameBW, cv2.COLOR_GRAY2BGR)
            frame = cv2.addWeighted(frameBW,0.5,frame,0.5,0)

        if self.clusterState == True:
            z = frame.reshape((-1,3))
            z = np.float32(z)
            ret, label, center = cv2.kmeans(z,self.nmbrClusters,None,self.criteria,
            10,cv2.KMEANS_RANDOM_CENTERS)

            center = np.uint8(center)
            res = center[label.flatten()]
            frame = res.reshape((frame.shape))

        if self.thresholdState == True:
            frameBW = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frame = cv2.adaptiveThreshold(frameBW,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,\
            cv2.THRESH_BINARY,11,2)
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            
        if self.invertState == True:
             frame = cv2.bitwise_not(frame)

        return frame

    def zoomFrame(self, frame):
        shape = frame.shape
        height = shape[0]
        width = shape[1]
        minX = int((self.zoom - 1)/(2*self.zoom) * width)
        maxX = width - minX
        minY = int((self.zoom - 1)/(2*self.zoom) * height)
        maxY = height - minY
        cropped = frame[minY:maxY, minX: maxX]
        return cv2.resize(cropped, (width, height))

    def captureImage(self):
        lastImage = self.ids['lastCapturedImage']
        ret, frame = self.capture1.read()

        buf1 = cv2.flip(frame, 0)
        buf = buf1.tobytes()
        texture1 = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
        texture1.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')

        # display image from the texture
        lastImage.texture = texture1

        # Save the captured image
        date = datetime.datetime.now().strftime("%d-%b-%Y-%H-%M-%S-%f")
        patientName = "-" + self.ids['nameTextBox'].text.strip().replace(" ", "-")
        if patientName == "-": patientName = ""

        # need to get current pathfrom OS to avoid issues with imwrite (note directory is found relative to scripts directory)
        dir = os.path.join(self.picSaveFolder, date + patientName + ".jpg")

        # cv2.imwrite fails silently if path is incorrect
        if not cv2.imwrite(dir, frame):
            raise Exception("Could not write image")

        self.lastImageDir = dir

    def displayLastImage(self):
        image = cv2.imread(self.lastImageDir)
        cv2.imshow('Last Captured Image', image)

    def onBrightnessChange(self, instance, value):
        self.brightness = value - 50

    def onContrastChange(self, instance, value):
        self.contrast = value/50.0 if value > 0 else 0.05

    def onZoomChange(self, instance, value):
        self.zoom = value

# Updated button images when they're active

    def noiseReduction(self):
        if not self.noiseState:
            self.ids['noise'].source = "assets/images/noise-active.png"
            self.noiseState = True
        else:
            self.ids['noise'].source = "assets/images/noise.png"
            self.noiseState = False

    def borderHighlight(self):
        if not self.borderState:
            self.ids['border'].source = "assets/images/border-active.png"
            self.borderState = True
        else:
            self.ids['border'].source = "assets/images/border.png"
            self.borderState = False

    def cluster(self):
        if not self.clusterState:
            self.ids['cluster'].source = "assets/images/cluster-active.png"
            self.clusterState = True
        else:
            self.ids['cluster'].source = "assets/images/cluster.png"
            self.clusterState = False

    def threshold(self):
        if not self.thresholdState:
            self.ids['threshold'].source = "assets/images/gaussian-active.png"
            self.thresholdState = True
        else:
            self.ids['threshold'].source = "assets/images/gaussian.png"
            self.thresholdState = False

    def invert(self):
        if not self.invertState:
            self.ids['invert'].source = "assets/images/invert-active.png"
            self.invertState = True
        else:
            self.ids['invert'].source = "assets/images/invert.png"
            self.invertState = False

    def fullscreenStream(self):
        print('fullscreen')
        if not self.fullscreenState:
            self.ids['arrow'].source = "assets/images/smallscreen.png"
            self.fullscreenState = True
        else:
            self.ids['arrow'].source = "assets/images/fullscreen.png"
            self.fullscreenState = False

    def power(self):
        if not self.powerState:
            self.ids['power'].source = "assets/images/power-active.png"
            self.powerState = True
        else:
            self.ids['power'].source = "assets/images/power.png"
            self.powerState = False

    def record(self):
        if self.recording:
            self.recorder.release()
            self.ids['recordButton'].source = "assets/images/record.png"
            self.recording = False
        else:
            self.recording = True
            self.ids['recordButton'].source = "assets/images/stop.png"

            date = datetime.datetime.now().strftime("%d-%b-%Y-%H-%M-%S-%f")
            patientName = "-" + self.ids['nameTextBox'].text.strip().replace(" ", "-")
            if patientName == "-": patientName = ""
            dir = os.path.join(self.videoSaveFolder, date + patientName + ".mp4")

            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self.recorder = cv2.VideoWriter(dir, fourcc, frameRate, (1280,720))

###########################
# Needs implementation
###########################

    def overlay(self):
        print('overlay')

    def swapCamera(self):
        print('swap cameras')

class ExampleApp(App):

    # acts like a static variable, ideally would be an instance variable but that
    # causes errors with conda for some reason
    vid = None

    def build(self):
        vid = Video()
        vid.capture1 = cv2.VideoCapture(0)
        # vid.capture2 = cv2.VideoCapture(1)
        vid.capture1.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        vid.capture1.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        # time1 = time.time()
        Clock.schedule_interval(vid.update, 1.0/8.0)
        self.vid = vid
        return vid

    # end recording session when closing application
    def on_stop(self):
        if self.vid.recording:
            self.vid.recorder.release()
            self.vid.recording = False


if __name__ == '__main__':
    ExampleApp().run()
    cv2.destroyAllWindows()
