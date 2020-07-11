__author__ = 'bunkus'
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.properties import (
    NumericProperty, ReferenceListProperty, ObjectProperty
)
from kivy.config import Config
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

import cv2
import datetime
class Video(Widget):
    # To be used for the first camera
    capture1 = ObjectProperty(None)
    # To be used for the second camera
    capture2 = ObjectProperty(None)

    brightness = NumericProperty(0)
    contrast = NumericProperty(1)
    frameRate =  NumericProperty(20)
    def update(self, dt):
        img1 = self.ids['videoFrame']
        # display image from cam in opencv window
        ret, frame = self.capture1.read()
        # cv2.imshow("CV2 Image", frame)
        # convert it to texture
        # contrast = 1
        # brightness = 0
        # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # frame[:,:,2] = np.clip(contrast * frame[:,:,2] + brightness, 0, 255)
        # frame = cv2.cvtColor(frame, cv2.COLOR_HSV2BGR)
        buf1 = cv2.flip(frame, 0)
        buf = buf1.tostring()
        texture1 = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
        texture1.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        # display image from the texture
        img1.texture = texture1

    def captureImage(self):
        print("HERE")
        lastImage = self.ids['lastCapturedImage']
        ret, frame = self.capture1.read()
        buf1 = cv2.flip(frame, 0)
        buf = buf1.tostring()
        texture1 = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
        texture1.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        # display image from the texture
        lastImage.texture = texture1

        # Save the captured image
        date = datetime.datetime.now().strftime("%d-%b-%Y-%H-%M-%S-%f")
        print(date)
        cv2.imwrite("capturedImages/" + date + ".jpg", frame)

class ExampleApp(App):
    def build(self):
        vid = Video()
        vid.capture1 = cv2.VideoCapture(0)
        vid.capture2 = cv2.VideoCapture(1)
        Clock.schedule_interval(vid.update, 1.0/20.0)
        return vid

if __name__ == '__main__':
    ExampleApp().run()
    cv2.destroyAllWindows()
