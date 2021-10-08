import tkinter as tk
from typing import *


class MarkupText(tk.Text):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configure(state="disabled")
        self.tag_configure("sel", underline=True)

    def clear_selection(self):
        self.tag_remove("sel", "1.0", tk.END)

    def clear_tags(self):
        for tag in self.tag_names():
            self.tag_delete(tag)

    # def convert_char_to_tk(self, span: Span) -> Tuple[str, str]:
    #     """ Converts char offset notation to tkinter internal notation. """
    #     return tuple(self.text_box.index(f"1.0+{i}c") for i in span)

    # def convert_tk_to_char(self, tk_span: Tuple[str, str]) -> Span:
    #     """ Converts tkinter internal notation to tuple of ints. """
    #     return tuple(self.text_box.count("1.0", i, "chars")[0] for i in tk_span)

    def get_selection_indices(self) -> Tuple[str, str]:
        try:
            return self.index(tk.SEL_FIRST), self.index(tk.SEL_LAST)
        except tk.TclError:
            raise RuntimeError("error: no text selected")

    def selection_exists(self) -> bool:
        return len(self.tag_ranges("sel")) > 0

    def set_text(self, text: str):
        self.configure(state="normal")
        self.delete("1.0", tk.END)
        self.insert("end", text)
        self.configure(state="disabled")
