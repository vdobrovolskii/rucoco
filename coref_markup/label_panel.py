import tkinter as tk
from tkinter import ttk
from typing import *

from coref_markup.markup_label import MarkupLabel


class LabelPanel:
    def __init__(self, master: tk.Widget, *, label_width: int, row: int, rowspan: int, columns: Tuple[int, int]):

        self.canvas = tk.Canvas(master)
        self.canvas.grid(row=row, rowspan=rowspan, column=columns[0], sticky=(tk.N+tk.W+tk.E+tk.S))

        self.scrollbar = ttk.Scrollbar(master, orient="vertical", command=self.canvas.yview)
        self.scrollbar.grid(row=row, rowspan=rowspan, column=columns[1], sticky=(tk.N+tk.S))

        self.frame = ttk.Frame(self.canvas)

        self.frame.bind("<MouseWheel>", self.mouse_wheel_handler)
        self.frame.bind_class("Label", "<MouseWheel>", self.mouse_wheel_handler)
        self.canvas.bind("<MouseWheel>", self.mouse_wheel_handler)
        self.frame.bind(
            "<Configure>",
            lambda _: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.create_window((0, 0), window=self.frame, anchor="nw")

        entity_panel_label = tk.Label(self.frame, text="Entities", width=label_width)
        entity_panel_label.grid(row=0, sticky=tk.N)

    def bind(self, *args, **kwargs):
        self.canvas.bind(*args, **kwargs)
        self.frame.bind(*args, **kwargs)

    def get_labels(self, start_row: int = 0, only_markup_labels: bool = False) -> Iterator[tk.Label]:
        cls = tk.Label if not only_markup_labels else MarkupLabel
        for row in range(start_row, self.frame.grid_size()[1]):
            for child in self.frame.grid_slaves(row=row):
                if isinstance(child, cls):
                    yield child

    def mouse_wheel_handler(self, event: tk.Event):
        """ Only scrolling if the scrollbar is not disabled (state() returns an empty tuple """
        if not self.scrollbar.state():
            self.canvas.yview_scroll(-1 * event.delta, "units")
