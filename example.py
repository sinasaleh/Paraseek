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

import cv2

class Video(Widget):
    capture1 = ObjectProperty(None)
    capture2 = ObjectProperty(None)

class ExampleApp(App):
    def build(self):
        vid = Video()
        return vid

if __name__ == '__main__':
    ExampleApp().run()
    cv2.destroyAllWindows()
