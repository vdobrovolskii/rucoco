import tkinter as tk
from typing import *
from coref_markup import utils


class MarkupLabel(tk.Label):
    icons = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configure(compound=tk.RIGHT)
        self.load_icons()
        self.normal_color = self.cget("background")
        self.hover_color = utils.multiply_color(self.normal_color, 1.2)
        self.inactive_color = utils.desaturate_color(self.normal_color, 1.0)

    def disable(self):
        self.configure(background=self.inactive_color, state=tk.DISABLED)

    def enable(self):
        self.configure(background=self.normal_color, state=tk.NORMAL)

    def enter(self, relation: Optional[str] = None):
        self.configure(background=self.hover_color, image=self.icons.get(relation, ""))

    def leave(self):
        self.configure(background=self.normal_color, image="")

    def load_icons(self):
        if MarkupLabel.icons is None:
            MarkupLabel.icons = {
                "child": tk.PhotoImage(file="resources/child.png"),
                "parent": tk.PhotoImage(file="resources/parent.png")
            }

    def select(self):
        self.configure(borderwidth=2)

    def unselect(self):
        self.configure(borderwidth=0)
