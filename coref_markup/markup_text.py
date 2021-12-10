from collections import defaultdict
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from typing import *

from coref_markup import utils
from coref_markup.const import *
from coref_markup.markup import Span
from coref_markup.settings import Settings


FONT_TYPE = "TkFixedFont"


class Tag:
    def __init__(self, text_box: tk.Text, span: Span, color: str):
        self.text_box = text_box

        self.span = span
        self.tag_idx = f"e{span}"

        self._dimmed = False
        self._emphasized = False

        self._update_colors(color)
        self._add_to_text_widget()

    def dim(self):
        if not self._dimmed:
            self._dimmed = True
            self._update()

    def deemphasize(self):
        if self._emphasized:
            self._emphasized = False
            self._appearance["emphasized"]["underline"] = None
            self._update()

    def emphasize(self, underline=True):
        if not self._emphasized:
            self._emphasized = True
            if underline:
                self._appearance["emphasized"]["underline"] = True
            self._update()

    def fix_overlapping(self, self_in_self: int):
        self.text_box.tag_raise(self.tag_idx)
        if self_in_self:
            current_color = self._appearance["normal"]["background"]
            new_color = utils.multiply_color(current_color, max(0, 1 - 0.15 * self_in_self))
            self._update_colors(new_color)
            self._update()

    def restore(self):
        if self._dimmed:
            self._dimmed = False
            self._update()

    def _add_to_text_widget(self):
        self.text_box.tag_add(self.tag_idx, *self.span)
        self._update()

    def _update(self):
        if self._emphasized:
            mode = "emphasized"
        elif self._dimmed:
            mode = "dimmed"
        else:
            mode = "normal"
        appearance = self._appearance[mode]
        self.text_box.tag_configure(self.tag_idx, **appearance)

    def _update_colors(self, normal_color: str):
        self._appearance = {
            "normal": {
                "background": normal_color,
                "underline": ""
            },
            "dimmed": {
                "background": utils.desaturate_color(normal_color, 1.0),
                "underline": ""
            },
            "emphasized": {
                "background": utils.multiply_color(normal_color, 1.2),
                "underline": None
            }
        }


class MarkupText(ScrolledText):
    def __init__(self, *, settings: Settings, **kwargs):
        super().__init__(**kwargs, font=(FONT_TYPE, settings.text_box_font_size))
        self.configure(state="disabled", inactiveselectbackground=self.cget("selectbackground"))
        self.tag_configure("sel", underline=True)
        self.clear_tags()

        self.settings = settings

        if MAC:
            self.tag_configure("search_result",
                               background=self.tag_cget("sel", "background"),
                               underline=self.tag_cget("sel", "underline"))
            self.bind("<FocusIn>", self.on_focus_in)
            self.bind("<FocusOut>", self.on_focus_out)

    def add_highlight(self, span: Span, entity_idx: int, color: str):
        tag = Tag(self, span, color)

        self.highlights[span] = tag
        self.entity2spans[entity_idx].append(span)
        self.tag2entity[tag.tag_idx] = entity_idx

    def clear_selection(self):
        self.tag_remove("sel", "1.0", tk.END)

    def clear_tags(self):
        for tag in self.tag_names():
            if tag != "search_result":
                self.tag_delete(tag)
        self.entity2spans: Dict[int, List[Span]] = defaultdict(list)
        self.highlights: Dict[Span, Tag] = {}
        self.tag2entity: Dict[str, int] = {}

    def convert_char_to_tk(self, span: Tuple[int, int]) -> Span:
        """ Converts char offset notation to tkinter internal notation. """
        return tuple(self.index(f"1.0+{i}c") for i in span)

    def convert_tk_to_char(self, tk_span: Span) -> Tuple[int, int]:
        """ Converts tkinter internal notation to tuple of ints. """
        return tuple(self.convert_to_int_index(i) for i in tk_span)

    def convert_to_int_index(self, index: str) -> int:
        """ Converts tkinter string index to int """
        if index == "1.0":
            return 0
        return self.count("1.0", index, "chars")[0]

    def deemphasize_highlight(self, span: Span):
        self.highlights[span].deemphasize()

    def dim_highlight(self, span: Span):
        self.highlights[span].dim()

    def emphasize_highlight(self, span: Span, underline: bool = True):
        self.highlights[span].emphasize(underline=underline)

    def font_decrease(self):
        if self.settings.text_box_font_size > 8:
            self.settings.text_box_font_size -= 1
            self.configure(font=(FONT_TYPE, self.settings.text_box_font_size))

    def font_increase(self):
        self.settings.text_box_font_size += 1
        self.configure(font=(FONT_TYPE, self.settings.text_box_font_size))

    def get_entity_label(self, entity_idx: int, max_width: int) -> str:
        first_span = min(self.entity2spans[entity_idx], key=self.convert_tk_to_char)
        return self.get(*first_span)[:max_width]

    def get_selection_indices(self) -> Span:
        try:
            return self.index(tk.SEL_FIRST), self.index(tk.SEL_LAST)
        except tk.TclError:
            raise RuntimeError("error: no text selected")

    def get_spans_at_index(self, index: str) -> Iterable[Span]:
        for tag in self.tag_names(index):
            if tag.startswith("e"):
                yield self.index(f"{tag}.first"), self.index(f"{tag}.last")

    def fix_overlapping_highlights(self):
        # Longer spans first
        all_spans = sorted(((span, entity_idx) for entity_idx, spans in self.entity2spans.items() for span in spans),
                           key=lambda x: self.span_length(x[0]), reverse=True)
        for span, entity_idx in all_spans:
            tags = [tag for tag in self.tag_names(span[0]) if tag.startswith("e")]
            if len(tags) > 1:
                sibling_tags = (tag for tag in tags if self.tag2entity[tag] == entity_idx)
                enclosing_tags = (tag for tag in sibling_tags if self.compare(span[1], "<=", self.tag_ranges(tag)[1]))
                self_in_self = sum(1 for _ in enclosing_tags) - 1
                self.highlights[span].fix_overlapping(self_in_self)
        self.tag_raise("sel")  # selection to be above any other tag

    def highlight_search_result(self, start: str, end: str):
        self.clear_selection()
        self.tag_add("sel", start, end)
        self.see(end)

        if MAC:
            self.tag_remove("search_result", "1.0", "end")
            self.tag_add("search_result", start, end)
            self.tag_raise("search_result")

    def on_focus_in(self, event: tk.Event):
        self.tag_remove("search_result", "1.0", "end")

    def on_focus_out(self, event: tk.Event):
        if self.selection_exists():
            self.tag_add("search_result", *self.get_selection_indices())
            self.tag_raise("search_result")

    def restore_all_highlights(self):
        for span in self.highlights:
            self.restore_highlight(span)

    def restore_highlight(self, span: Span):
        self.highlights[span].restore()

    def selection_exists(self) -> bool:
        return len(self.tag_ranges("sel")) > 0

    def set_text(self, text: str):
        self.configure(state="normal")
        self.delete("1.0", tk.END)
        self.insert("end", text)
        self.configure(state="disabled")

    def span_length(self, span: Span) -> int:
        return self.count(*span, "chars")
