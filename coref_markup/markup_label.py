import tkinter as tk
from typing import *
from coref_markup import utils


class MarkupLabel(tk.Label):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.normal_color = self.cget("background")
        self.hover_color = utils.multiply_color(self.normal_color, 1.2)

    def enter(self):
        self.configure(background=self.hover_color)

    def leave(self):
        self.configure(background=self.normal_color)

    def select(self):
        self.configure(borderwidth=2)

    def unselect(self):
        self.configure(borderwidth=0)
