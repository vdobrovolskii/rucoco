from functools import partial
from itertools import chain, cycle
import tkinter as tk
from tkinter import ttk
from typing import *

from coref_markup.const import *
from coref_markup.markup import *
from coref_markup.markup_text import *
from coref_markup.markup_label import *
from coref_markup import utils


# TODO: hover to show multientity as well
# TODO: merge entities: merge multientities with multientities and add entities to multientities
# TODO: scroll entities
# TODO: open files
# TODO: save files
# TODO: delete entity (select and press delete; should there be a Button?)
# TODO: delete spans (how?)
# TODO: config (annotator name, what else?)
# TODO: span and entity texts in error messages (custom Exception class to pass data)
# TODO: reorganize code
# TODO: remove magic values
# TODO: docstrings
# TODO: mypy and pylint


class Application(ttk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.master = master
        self.pack()

        #######################################################################
        self.__config = {"name": "annotator"}
        self.__text = "Привет, это Вася! Я давно хотел тебе написать, Иван. Как у тебя дела? У меня норм все вот. Мы." #* 100
        self.markup = Markup()
        self.markup.new_entity(("1.12", "1.16"))
        self.markup.add_span_to_entity(("1.18", "1.19"), 0)
        self.markup.new_entity(("1.32", "1.36"))
        self.markup.new_entity(("1.47", "1.51"))
        self.markup.merge(1, 2)

        # self.__markup.merge((12, 16), (18, 19))
        # self.__markup.merge((32, 36), (47, 51))
        i = self.markup.new_entity(("1.91", "1.93"), True)
        self.markup.add_entity_to_mentity(0, i)
        self.markup.add_entity_to_mentity(1, i)
        #######################################################################

        self.entity2label: Dict[int, MarkupLabel] = {}
        self.selected_entity: Optional[int] = None
        self.popup_menu_entity: Optional[int] = None

        self.self_in_self_spans: Dict[Span, int] = {}  # span -> overlapping level

        self.highlights: Set[str] = set()

        self.build_colors()
        self.build_widgets()

        self.render_entities()

    def add_span_to_entity(self, span: Span, entity_idx: int):
        try:
            self.markup.add_span_to_entity(span, entity_idx)
            self.render_entities()
        except RuntimeError as e:
            self.set_status(e.args[0])

    def build_colors(self):
        self.all_colors = cycle(utils.get_colors())
        self.entity2color: Dict[int, str] = {}
        self.color_stack: List[str] = []

    def build_widgets(self):
        """
        Only making the following visible as instance attributes:
            self.entity_panel
            self.multi_entity_panel
            self.status_bar
            self.text_box
            self.label_menu
        """
        menubar = tk.Menu(self)
        menubar.add_command(label="Open")
        menubar.add_command(label="Save")
        self.master.configure(menu=menubar)

        main_frame = ttk.Frame(self)
        main_frame.pack(side="top", fill="both")

        status_bar = ttk.Label(self)
        status_bar.pack(side="bottom", fill="x")

        text_box = MarkupText(main_frame, wrap="word")
        text_box.set_text(self.__text) ########################################
        text_box.bind("<ButtonRelease>", self.mouse_handler_text)

        text_box.pack(side="left")

        panel = ttk.Frame(main_frame)
        panel.pack(side="right", fill="y")

        text_box_scroller = ttk.Scrollbar(main_frame, command=text_box.yview)
        text_box_scroller.pack(side="left", after=text_box, before=panel, fill="y")
        text_box["yscrollcommand"] = text_box_scroller.set

        separator = ttk.Separator(main_frame, orient="vertical")
        separator.pack(side="left", after=text_box_scroller, before=panel, fill="y")

        entity_panel = ttk.Frame(panel)
        entity_panel.bind("<ButtonRelease>", self.mouse_handler_panel)
        entity_panel.pack(side="left", fill="y")

        separator = ttk.Separator(panel, orient="vertical")
        separator.pack(side="left", after=entity_panel, fill="y")

        multi_entity_panel = ttk.Frame(panel)
        multi_entity_panel.bind("<ButtonRelease>", self.mouse_handler_panel)
        multi_entity_panel.pack(side="right", fill="y")

        entity_panel_label = ttk.Label(entity_panel, text="Entities")
        entity_panel_label.pack(side="top")

        mentity_panel_label = ttk.Label(multi_entity_panel, text="mEntities")
        mentity_panel_label.pack(side="top")

        new_entity_button = ttk.Button(entity_panel, text="New Entity", command=self.new_entity)
        new_entity_button.pack(side="bottom")

        new_mentity_button = ttk.Button(multi_entity_panel, text="New mEntity",
                                        command=partial(self.new_entity, multi=True))
        new_mentity_button.pack(side="bottom")

        label_menu = tk.Menu(self, tearoff=0)
        label_menu.add_command(label="Merge", command=self.merge)
        label_menu.add_command(label="Set as parent", command=self.set_parent)
        label_menu.add_command(label="Unset parent", command=self.unset_parent)

        # Registering attributes
        self.entity_panel = entity_panel
        self.multi_entity_panel = multi_entity_panel
        self.status_bar = status_bar
        self.text_box = text_box
        self.label_menu = label_menu

    def get_entity_color(self, entity_idx: int) -> str:
        if entity_idx not in self.entity2color:
            self.entity2color[entity_idx] = self.color_stack.pop() if self.color_stack else next(self.all_colors)
        return self.entity2color[entity_idx]

    def get_highlighting_bitmap(self, span: Span) -> str:
        bitmaps = ["gray50", "gray25", "gray12"]
        overlapping_level = self.self_in_self_spans.get(span, 0)
        if overlapping_level > 2:
            self.set_status(f"warning: '{self.text_box.get(*span)}' has overlapping level of {overlapping_level}")
            overlapping_level = 2
        return bitmaps[overlapping_level]

    def merge(self):
        removed_entity = self.markup.merge(self.selected_entity, self.popup_menu_entity)
        if removed_entity is not None:
            self.color_stack.append(self.entity2color.pop(removed_entity))
        self.render_entities()

    def mouse_handler_label(self, event: tk.Event, entity_idx: int):
        if event.num == LEFT_MOUSECLICK:
            if self.text_box.selection_exists():
                self.add_span_to_entity(self.text_box.get_selection_indices(), entity_idx)
                self.text_box.clear_selection()
            elif self.selected_entity == entity_idx:
                self.entity2label[self.selected_entity].unselect()
                self.selected_entity = None
            else:
                if self.selected_entity is not None:
                    self.entity2label[self.selected_entity].unselect()
                self.selected_entity = entity_idx
                self.entity2label[self.selected_entity].select()

    def mouse_handler_panel(self, event: tk.Event):
        if event.num == LEFT_MOUSECLICK and self.selected_entity is not None:
            self.entity2label[self.selected_entity].unselect()
            self.selected_entity = None

    def mouse_handler_text(self, event: tk.Event):
        if event.num == LEFT_MOUSECLICK and self.selected_entity is not None and self.text_box.selection_exists():
            self.add_span_to_entity(self.text_box.get_selection_indices(), self.selected_entity)
            self.text_box.clear_selection()

    def mouse_hover_handler(self, event: tk.Event, entity_idx: int, underline: bool = True):
        if event.type is tk.EventType.Enter:
            for span in sorted(self.markup.get_spans(entity_idx), key=self.span_length, reverse=True):
                self.highlights.add(f"h{span}")
                self.text_box.tag_add(f"h{span}", *span)
                self.text_box.tag_configure(f"h{span}",
                                            bgstipple=self.get_highlighting_bitmap(span),
                                            underline=underline)
            self.entity2label[entity_idx].enter()
        else:
            while self.highlights:
                self.text_box.tag_delete(self.highlights.pop())
            self.entity2label[entity_idx].leave()

        if self.markup.is_multi_entity(entity_idx):
                for inner_entity_idx in self.markup.get_inner_entities(entity_idx):
                    self.mouse_hover_handler(event, inner_entity_idx, underline=False)

    def new_entity(self, multi: bool = False):
        try:
            start, end = self.text_box.get_selection_indices()
            self.text_box.clear_selection()
            self.markup.new_entity((start, end), multi=multi)
            self.render_entities()
        except RuntimeError as e:
            self.set_status(e.args[0])

    def popup_menu(self, event: tk.Event, entity_idx: int):
        if self.selected_entity is None or self.selected_entity == entity_idx:
            return
        try:
            self.popup_menu_entity = entity_idx

            # Only allowing merges of the same type (single + single or multi + multi)
            if self.markup.is_multi_entity(self.selected_entity) == self.markup.is_multi_entity(self.popup_menu_entity):
                self.label_menu.entryconfigure("Merge", state="active")
            else:
                self.label_menu.entryconfigure("Merge", state="disabled")

            # Only MultiEntity can be set as parent
            if self.markup.is_multi_entity(self.popup_menu_entity):
                if self.markup.is_part_of(self.selected_entity, self.popup_menu_entity):
                    self.label_menu.entryconfigure("Set as parent", state="disabled")
                    self.label_menu.entryconfigure("Unset parent", state="active")
                else:
                    self.label_menu.entryconfigure("Set as parent", state="active")
                    self.label_menu.entryconfigure("Unset parent", state="disabled")
            else:
                self.label_menu.entryconfigure("Set as parent", state="disabled")
                self.label_menu.entryconfigure("Unset parent", state="disabled")

            w, h = self.label_menu.winfo_reqwidth(), self.label_menu.winfo_reqheight()
            self.label_menu.tk_popup(event.x_root + w // 2, event.y_root + h // 2, 0)
        finally:
            self.label_menu.grab_release()

    def render_entities(self):
        for child in chain(self.entity_panel.winfo_children(), self.multi_entity_panel.winfo_children()):
            if isinstance(child, MarkupLabel):
                child.destroy()
        self.text_box.clear_tags()
        self.self_in_self_spans = {}
        tag2entity = {}

        all_spans: List[Tuple[Span, int]] = []
        for entity_idx in self.markup.get_entities():
            color = self.get_entity_color(entity_idx)

            # Highlight spans in the text
            spans = sorted(self.markup.get_spans(entity_idx))
            for span in spans:
                tag_idx = len(all_spans)
                tag2entity[f"e{tag_idx}"] = entity_idx
                all_spans.append((span, entity_idx))
                self.text_box.tag_add(f"e{tag_idx}", *span)
                self.text_box.tag_configure(f"e{tag_idx}", background=color)

            # Add labels to the right panel
            label_text = self.text_box.get(*spans[0])[:32]
            if isinstance(self.markup._entities[entity_idx], MultiEntity):
                placement = self.multi_entity_panel
            else:
                placement = self.entity_panel
            label = MarkupLabel(placement, text=label_text, background=color, borderwidth=0, relief="solid")
            label.pack(side="top")
            label.bind("<Enter>", partial(self.mouse_hover_handler, entity_idx=entity_idx))
            label.bind("<Leave>", partial(self.mouse_hover_handler, entity_idx=entity_idx))
            label.bind("<ButtonRelease>", partial(self.mouse_handler_label, entity_idx=entity_idx))
            label.bind("<Button-3>", partial(self.popup_menu, entity_idx=entity_idx))
            self.entity2label[entity_idx] = label

        # Because tkinter doesn't support several layers of tags, manually
        # set the color again for overlapping regions
        all_spans.sort(key=lambda x: self.span_length(x[0]), reverse=True)  # longest spans first
        for span, entity_idx in all_spans:
            tags = [tag for tag in self.text_box.tag_names(span[0]) if tag.startswith("e")]
            if len(tags) > 1:
                self_in_self = sum(1 for tag in tags if tag2entity[tag] == entity_idx) - 1
                if self_in_self:
                    self.self_in_self_spans[span] = self_in_self
                self.text_box.tag_add(f"+e{entity_idx}{span}", *span)
                self.text_box.tag_configure(f"+e{entity_idx}{span}",
                                            background=utils.get_shade(self.get_entity_color(entity_idx),
                                                                       1 - 0.15 * self_in_self))

        if self.selected_entity is not None:
            self.entity2label[self.selected_entity].select()

    def set_parent(self):
        self.markup.add_entity_to_mentity(self.selected_entity, self.popup_menu_entity)

    def set_status(self, message: str, duration: int = 5000):
        self.status_bar.configure(text=message)
        self.after(duration, lambda: self.status_bar.configure(text=""))

    def span_length(self, span: Span) -> int:
        return self.text_box.count(*span, "chars")

    def unset_parent(self):
        self.markup.remove_entity_from_mentity(self.selected_entity, self.popup_menu_entity)
