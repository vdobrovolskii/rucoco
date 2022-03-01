import tkinter as tk
from typing import *


class Menubar(tk.Menu):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cascades: Dict[str, tk.Menu] = {}

    def add_cascade(self, *args, **kwargs):
        super().add_cascade(*args, **kwargs)
        self.cascades[kwargs["label"]] = kwargs["menu"]

    def get_cascade(self, label: str) -> tk.Menu:
        return self.cascades[label]
