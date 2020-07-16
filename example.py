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

###################################
# For Hovering
from kivy.core.window import Window
# For Hovering
###################################

import cv2
import numpy as np
import datetime
import os
import time
import math

frameRate = 8.0

###################################
# For Hovering
# Just need to add hover specific image of the ImageButton to the assets/hover folder.
# NOTE  images must have same name in the assets/hover and assets/images folders
class ImageButton(ButtonBehavior, Image):
    hovered = BooleanProperty(False)
    border_point= ObjectProperty(None)

    def __init__(self, **kwargs):
        self.register_event_type('on_enter')
        self.register_event_type('on_leave')
        Window.bind(mouse_pos=self.on_mouse_pos)
        super(ImageButton, self).__init__(**kwargs)

    def on_mouse_pos(self, *args):
        if not self.get_root_window():
            return # do proceed if I'm not displayed <=> If have no parent
        pos = args[1]
        # Next line to_widget allow to compensate for relative layout
        inside = self.collide_point(*self.to_widget(*pos))
        if self.hovered == inside:
            # We have already done what was needed
            return
        self.border_point = pos
        self.hovered = inside
        if inside:
            self.dispatch('on_enter')
        else:
            self.dispatch('on_leave')

    def on_enter(self):
        if "capturedImages" in self.source:
            with self.canvas:
                self.opacity = 0.7
        elif "hover" not in self.source:
            self.source = self.source.replace("images", "hover")


    def on_leave(self):
        if "capturedImages" in self.source:
            with self.canvas:
                self.opacity = 1.0
        elif "hover" in self.source:
            self.source = self.source.replace("hover", "images")


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
    nmbrClusters = 5
    # by what factor is the center rectangle that is clustered smaller from the image in size 
    cntrRecSzFac = math.sqrt(9.0)

    # full screen video state (on_release is fullscreenStream, needs implementation)
    fullscreenState = BooleanProperty(False)
    # power buttons states (on_release is power, needs implementation)
    powerState = BooleanProperty(False)

    picSaveFolder = os.path.join(os.path.dirname(os.path.realpath(__file__)),"capturedImages")
    videoSaveFolder = os.path.join(os.path.dirname(os.path.realpath(__file__)),"recordedVideos")
    saveFileDir = os.path.join(os.path.dirname(os.path.realpath(__file__)),"bin", "lastImage.txt")
    lastImageDir = None

    def __init__(self, *args, **kwargs):
        super(Video, self).__init__(*args, **kwargs)

        brightnessSlider = self.ids['brightnessSlider']
        brightnessSlider.fbind('value', self.onBrightnessChange)

        contrastSlider = self.ids['contrastSlider']
        contrastSlider.fbind('value', self.onContrastChange)

        zoomSlider = self.ids['zoomSlider']
        zoomSlider.fbind('value', self.onZoomChange)
        
        # read directory of last save image, if image no longer exists cover image in assets folder
        raw = open(self.saveFileDir, "r")
        self.lastImageDir = raw.read().split("\n")[0]
        raw.close()
        if not os.path.exists(self.lastImageDir):
            self.lastImageDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets", "images", "cover.jpg")
        self.ids['lastCapturedImage'].source = self.lastImageDir


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
            height,width,_ = frame.shape
            recSize = (math.ceil(width/self.cntrRecSzFac), math.ceil(height/self.cntrRecSzFac))
            startPoint = (math.ceil((width - recSize[0])/2.0), math.ceil((height - recSize[1])/2.0))
            endPoint = (startPoint[0] + recSize[0], startPoint[1] + recSize[1])
            centerRec = np.zeros(recSize, np.uint8)
            centerRec = frame[startPoint[1]:endPoint[1],startPoint[0]:endPoint[0]]

            z = centerRec.reshape((-1,3))
            z = np.float32(z)
            ret, label, center = cv2.kmeans(z,self.nmbrClusters,None,self.criteria,
            10,cv2.KMEANS_RANDOM_CENTERS)

            center = np.uint8(center)
            res = center[label.flatten()]
            centerRec = res.reshape((centerRec.shape))

            frame[startPoint[1]:endPoint[1],startPoint[0]:endPoint[0]] = centerRec

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

        # apply filters to this captured frame
        frame = self.applyFilters(frame)

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
        if not self.fullscreenState:
            # somehow change canvas to that of a full screen stream (should this be done inside ExampleApp?)
            self.fullscreenState = True
        else:
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
        
        saveTextFile = open(self.vid.saveFileDir, "r+")
        saveTextFile.read()
        saveTextFile.seek(0)
        saveTextFile.truncate()
        saveTextFile.write(self.vid.lastImageDir)
        saveTextFile.close()


if __name__ == '__main__':
    ExampleApp().run()
    cv2.destroyAllWindows()
