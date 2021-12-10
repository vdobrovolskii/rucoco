import tkinter as tk
from tkinter import ttk
from typing import *


class FindBar(tk.Frame):
    def __init__(self,
                 master: tk.Widget,
                 *,
                 entry_width: int,
                 padx: int,
                 cancel_command: Callable[[], None],
                 find_command: Callable[[], None],
                ):
        super().__init__(master)

        self.entry = ttk.Entry(self, width=entry_width)
        self.entry.grid(row=0, column=0, padx=padx)
        self.entry.bind("<Return>", self.on_return)

        self.find_button = ttk.Button(self, text="Find Next", command=find_command)
        self.find_button.grid(row=0, column=1, padx=padx)

        self.cancel_button = ttk.Button(self, text="Cancel", command=cancel_command)
        self.cancel_button.grid(row=0, column=2, padx=padx)

        self.bind("<Map>", lambda _: self.entry.focus_set())
        self.bind("<Unmap>", lambda _: self.entry.delete(0, tk.END))

        self.find_command = find_command

    def get_query(self) -> str:
        return self.entry.get()

    def on_return(self, event: tk.Event):
        if self.winfo_ismapped():
            self.find_command()
