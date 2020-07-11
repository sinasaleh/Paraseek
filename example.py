__author__ = 'bunkus'
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.behaviors import ButtonBehavior

from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.properties import (
    NumericProperty, ReferenceListProperty, ObjectProperty, StringProperty
)
from kivy.config import Config
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

import cv2
import numpy as np
import datetime
import os


class ImageButton(ButtonBehavior, Image):
    pass

class Video(Widget):
    # To be used for the first camera
    capture1 = ObjectProperty(None)

    # To be used for the second camera
    # capture2 = ObjectProperty(None)

    brightness = NumericProperty(0)
    contrast = NumericProperty(1.0)
    frameRate =  NumericProperty(30)

    saveFolder = os.path.join(os.path.dirname(os.path.realpath(__file__)),"capturedImages")
    lastImageDir = os.path.join(saveFolder, "cover.jpg")

    def __init__(self, *args, **kwargs):
        super(Video, self).__init__(*args, **kwargs)
        brightnessSlider = self.ids['brightnessSlider']
        brightnessSlider.fbind('value', self.onBrightnessChange)
        contrastSlider = self.ids['contrastSlider']
        contrastSlider.fbind('value', self.onContrastChange)

    def update(self, dt):
        img1 = self.ids['videoFrame']

        # display image from cam in opencv window
        ret, frame = self.capture1.read()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        frame[:,:,2] = np.clip(np.rint(self.contrast * frame[:,:,2] + self.brightness), 0, 255)
        frame = cv2.cvtColor(frame, cv2.COLOR_HSV2BGR)
        buf1 = cv2.flip(frame, 0)
        buf = buf1.tobytes()
        texture1 = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
        texture1.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        
        # display image from the texture
        img1.texture = texture1

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

        # need to get current pathfrom OS to avoid issues with imwrite (note directory is found relative to scripts directory)
        dir = os.path.join(self.saveFolder, date + ".jpg")

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

class ExampleApp(App):
    def build(self):
        vid = Video()
        vid.capture1 = cv2.VideoCapture(0)
        # vid.capture2 = cv2.VideoCapture(1)
        vid.capture1.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        vid.capture1.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        Clock.schedule_interval(vid.update, 1.0/30.0)
        return vid

if __name__ == '__main__':
    ExampleApp().run()
    cv2.destroyAllWindows()
