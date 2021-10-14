from functools import partial
from itertools import chain, cycle
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from typing import *

from coref_markup.const import *
from coref_markup.markup import *
from coref_markup.markup_text import *
from coref_markup.markup_label import *
from coref_markup import utils


# BUG: underline disappeared on hover
# TODO: if x>y>z, then highlight z when hovering x
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
# TODO: click in text to bring out names of spans in this area


class Application(ttk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.master = master
        self.pack()

        self.markup = Markup()

        self.entity2label: Dict[int, MarkupLabel] = {}
        self.selected_entity: Optional[int] = None
        self.popup_menu_entity: Optional[int] = None

        self.self_in_self_spans: Dict[Span, int] = {}  # span -> overlapping level

        self.highlights: Set[str] = set()

        self.build_colors()
        self.build_widgets()

        self.render_entities()

        self.open_file("test.txt")

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
        menubar = tk.Menu()
        file_menu = tk.Menu(menubar)
        file_menu.add_command(label="Open", command=self.open_file_handler)
        file_menu.add_command(label="Save")
        menubar.add_cascade(label="File", menu=file_menu)
        self.master.configure(menu=menubar)

        main_frame = ttk.Frame(self)
        main_frame.pack(side="top", fill="both")

        status_bar = ttk.Label(self)
        status_bar.pack(side="bottom", fill="x")

        text_box = MarkupText(main_frame, wrap="word")
        # text_box.set_text(self.__text) ########################################
        text_box.bind(f"<ButtonRelease-{LEFT_MOUSECLICK}>", self.mouse_handler_text)

        text_box.pack(side="left")

        panel = ttk.Frame(main_frame)
        panel.pack(side="right", fill="y")

        text_box_scroller = ttk.Scrollbar(main_frame, command=text_box.yview)
        text_box_scroller.pack(side="left", after=text_box, before=panel, fill="y")
        text_box["yscrollcommand"] = text_box_scroller.set

        separator = ttk.Separator(main_frame, orient="vertical")
        separator.pack(side="left", after=text_box_scroller, before=panel, fill="y")

        entity_panel = ttk.Frame(panel)
        entity_panel.bind(f"<ButtonRelease-{LEFT_MOUSECLICK}>", self.mouse_handler_panel)
        entity_panel.pack(side="left", fill="y")

        separator = ttk.Separator(panel, orient="vertical")
        separator.pack(side="left", after=entity_panel, fill="y")

        multi_entity_panel = ttk.Frame(panel)
        multi_entity_panel.bind(f"<ButtonRelease-{LEFT_MOUSECLICK}>", self.mouse_handler_panel)
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
        label_menu.add_command(label="Delete", command=self.delete_entity)

        # Registering attributes
        self.entity_panel = entity_panel
        self.multi_entity_panel = multi_entity_panel
        self.status_bar = status_bar
        self.text_box = text_box
        self.label_menu = label_menu

    def delete_entity(self) -> str:
        self.markup.delete_entity(self.popup_menu_entity)
        if self.selected_entity == self.popup_menu_entity:
            self.selected_entity = None
        self.color_stack.append(self.entity2color.pop(self.popup_menu_entity))
        self.render_entities()

    def get_entity_color(self, entity_idx: int) -> str:
        if entity_idx not in self.entity2color:
            self.entity2color[entity_idx] = self.color_stack.pop() if self.color_stack else next(self.all_colors)
        return self.entity2color[entity_idx]

    def merge(self):
        removed_entity = self.markup.merge(self.selected_entity, self.popup_menu_entity)
        if removed_entity is not None:
            self.color_stack.append(self.entity2color.pop(removed_entity))
        self.render_entities()

    def mouse_handler_label(self, event: tk.Event, entity_idx: int):
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
        if self.selected_entity is not None:
            self.entity2label[self.selected_entity].unselect()
            self.selected_entity = None

    def mouse_handler_text(self, event: tk.Event):
        if self.selected_entity is not None and self.text_box.selection_exists():
            self.add_span_to_entity(self.text_box.get_selection_indices(), self.selected_entity)
            self.text_box.clear_selection()

    def mouse_hover_handler(self, event: tk.Event, entity_idx: int, underline: bool = True, recursive: bool = True):
        if event.type is tk.EventType.Enter:
            for span in self.markup.get_spans(entity_idx):
                self.text_box.add_extra_highlight(span, underline=underline)
            self.entity2label[entity_idx].enter()
        else:
            for span in self.markup.get_spans(entity_idx):
                self.text_box.remove_extra_highlight(span)
            self.entity2label[entity_idx].leave()

        if recursive:
            if self.markup.is_multi_entity(entity_idx):
                for inner_entity_idx in self.markup.get_inner_entities(entity_idx):
                    self.mouse_hover_handler(event, inner_entity_idx, underline=False, recursive=False)

            for outer_entity_idx in self.markup.get_outer_entities(entity_idx):
                self.mouse_hover_handler(event, outer_entity_idx, underline=False, recursive=False)

    def new_entity(self, multi: bool = False):
        try:
            start, end = self.text_box.get_selection_indices()
            self.text_box.clear_selection()
            self.markup.new_entity((start, end), multi=multi)
            self.render_entities()
        except RuntimeError as e:
            self.set_status(e.args[0])

    def open_file_handler(self):
        # TODO: first close the current file to avoid losing any data
        self.open_file(filedialog.askopenfilename())

    def open_file(self, path: str):
        if path:
            self.markup = Markup()
            with open(path, encoding="utf8") as f:
                self.text_box.set_text(f.read())
            self.render_entities()

    def popup_menu(self, event: tk.Event, entity_idx: int):
        states = {
            "Merge": "disabled",
            "Set as parent": "disabled",
            "Unset parent": "disabled",
            "Delete": "active"
        }
        self.popup_menu_entity = entity_idx

        if self.selected_entity is not None and self.selected_entity != self.popup_menu_entity:

            if self.markup.is_multi_entity(self.selected_entity) == self.markup.is_multi_entity(self.popup_menu_entity):
                states["Merge"] = "active"

            if self.markup.is_multi_entity(self.popup_menu_entity):
                if self.markup.is_part_of(self.selected_entity, self.popup_menu_entity):
                    states["Unset parent"] = "active"
                else:
                    states["Set as parent"] = "active"

        for key, value in states.items():
            self.label_menu.entryconfigure(key, state=value)

        try:
            w, h = self.label_menu.winfo_reqwidth(), self.label_menu.winfo_reqheight()
            h //= self.label_menu.index("end") + 1
            self.label_menu.tk_popup(event.x_root + w // 2 * int(NOT_MAC), event.y_root + h // 2 * int(NOT_MAC), 0)
        finally:
            self.label_menu.grab_release()

    def render_entities(self):
        for child in chain(self.entity_panel.winfo_children(), self.multi_entity_panel.winfo_children()):
            if isinstance(child, MarkupLabel):
                child.destroy()
        self.text_box.clear_tags()

        for entity_idx in self.markup.get_entities():
            color = self.get_entity_color(entity_idx)
            for span in self.markup.get_spans(entity_idx):
                self.text_box.add_highlight(span, entity_idx, color)
            label_text = self.text_box.get_entity_label(entity_idx)

            if isinstance(self.markup._entities[entity_idx], MultiEntity):
                placement = self.multi_entity_panel
            else:
                placement = self.entity_panel
            label = MarkupLabel(placement, text=label_text, background=color, borderwidth=0, relief="solid")
            label.pack(side="top")
            label.bind("<Enter>", partial(self.mouse_hover_handler, entity_idx=entity_idx))
            label.bind("<Leave>", partial(self.mouse_hover_handler, entity_idx=entity_idx))
            label.bind(f"<ButtonRelease-{LEFT_MOUSECLICK}>", partial(self.mouse_handler_label, entity_idx=entity_idx))
            label.bind(f"<Button-{RIGHT_MOUSECLICK}>", partial(self.popup_menu, entity_idx=entity_idx))
            self.entity2label[entity_idx] = label

        self.text_box.fix_overlapping_highlights()

        if self.selected_entity is not None:
            self.entity2label[self.selected_entity].select()

    def set_parent(self):
        self.markup.add_entity_to_mentity(self.selected_entity, self.popup_menu_entity)

    def set_status(self, message: str, duration: int = 5000):
        self.status_bar.configure(text=message)
        self.after(duration, lambda: self.status_bar.configure(text=""))



    def unset_parent(self):
        self.markup.remove_entity_from_mentity(self.selected_entity, self.popup_menu_entity)
