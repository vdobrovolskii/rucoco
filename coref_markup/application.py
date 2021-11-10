from collections import deque
from copy import deepcopy
from functools import partial
from itertools import cycle
import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import *

from coref_markup.const import *
from coref_markup.markup import Span, Markup
from coref_markup.markup_text import MarkupText
from coref_markup.markup_label import MarkupLabel
from coref_markup.settings import Settings
from coref_markup import utils


# TODO: scroll entities
# TODO: config (annotator name, what else?)
# TODO: span and entity texts in error messages (custom Exception class to pass data)
# TODO: remove magic values
# TODO: docstrings
# TODO: mypy and pylint


class Application(ttk.Frame):
    LABEL_WIDTH = 32
    UNDO_REDO_STACK_SIZE = 5

    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.master = master
        self.grid(row=0, column=0, sticky=(tk.N+tk.W+tk.E+tk.S))

        self.markup = Markup()
        self.settings = Settings()

        self.reset_state()
        self.build_widgets()

    # Initializers #####################################################################################################

    def build_widgets(self):
        """
        Only making the following visible as instance attributes:
            self.panel
            self.status_bar
            self.text_box
            self.label_menu
            self.text_menu
        """
        self.master.protocol("WM_DELETE_WINDOW", self.close_program_handler)
        self.grid(row=0, column=0, sticky=(tk.N + tk.W + tk.E + tk.S))

        status_bar = ttk.Label(self)
        status_bar.grid(row=1, column=0, columnspan=2, sticky=(tk.N, tk.W))

        text_box = MarkupText(settings=self.settings, master=self, highlightthickness=0, wrap="word")
        text_box.bind(f"<ButtonRelease-{LEFT_MOUSECLICK}>", self.mouse_handler_text)
        text_box.bind(f"<Button-{RIGHT_MOUSECLICK}>", self.popup_text_menu)
        text_box.grid(row=0, column=0, sticky=(tk.N+tk.W+tk.E+tk.S))

        text_menu = tk.Menu(self, tearoff=0)

        panel = ttk.Frame(self)
        panel.bind(f"<ButtonRelease-{LEFT_MOUSECLICK}>", self.mouse_handler_panel)
        panel.grid(row=0, column=1, sticky=(tk.N+tk.W+tk.E+tk.S))

        entity_panel_label = tk.Label(panel, text="Entities", width=self.LABEL_WIDTH)
        entity_panel_label.grid(row=0, sticky=tk.N)

        label_menu = tk.Menu(self, tearoff=0)
        label_menu.add_command(label="Merge", command=self.merge)
        label_menu.add_command(label="Set as parent", command=self.set_parent)
        label_menu.add_command(label="Unset parent", command=self.unset_parent)
        label_menu.add_command(label="Delete", command=self.delete_entity)

        # Menu
        menubar = tk.Menu()
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open...", command=self.open_file_handler)
        file_menu.add_command(label="Save", command=self.save_file_handler, accelerator="Ctrl+s")
        file_menu.add_command(label="Save As...", command=self.save_file_as_handler)
        menubar.add_cascade(label="File", menu=file_menu)
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo", command=self.undo, accelerator="Ctrl+z")
        edit_menu.add_command(label="Redo", command=self.redo, accelerator="Ctrl+y")
        menubar.add_cascade(label="Edit", menu=edit_menu)
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Font +", command=text_box.font_increase, accelerator="Ctrl++")
        view_menu.add_command(label="Font -", command=text_box.font_decrease, accelerator="Ctrl+-")
        menubar.add_cascade(label="View", menu=view_menu)
        self.master.configure(menu=menubar)

        # Shortcuts
        self.master.bind("<Control-equal>", lambda _: self.text_box.font_increase())
        self.master.bind("<Control-minus>", lambda _: self.text_box.font_decrease())
        self.master.bind("<Control-z>", lambda _: self.undo())
        self.master.bind("<Control-y>", lambda _: self.redo())
        self.master.bind("<Control-s>", lambda _: self.save_file_handler())

        # Managing resizing
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=3)

        # Registering attributes
        self.panel = panel
        self.status_bar = status_bar
        self.text_box = text_box
        self.label_menu = label_menu
        self.text_menu = text_menu

    def reset_state(self):
        self.all_colors = cycle(utils.get_colors())
        self.entity2color: Dict[int, str] = {}
        self.color_stack: List[str] = []

        self.entity2label: Dict[int, MarkupLabel] = {}
        self.selected_entity: Optional[int] = None
        self.popup_menu_entity: Optional[int] = None

        self.undo_stack = deque([], self.UNDO_REDO_STACK_SIZE)
        self.redo_stack = deque([], self.UNDO_REDO_STACK_SIZE)

        self.filename: Optional[str] = None
        self.modified = False

    def undoable(func: Callable[..., Any]):
        def wrapper(instance: "Application", *args, **kwargs):
            markup = deepcopy(instance.markup)
            result = func(instance, *args, **kwargs)
            instance.undo_stack.append(markup)
            instance.redo_stack.clear()
            instance.modified = True
            return result
        return wrapper

    # Event handlers ###################################################################################################

    def close_program_handler(self):
        if (not self.markup
                or not self.modified
                or messagebox.askokcancel("Quit", "Are you sure you want to quit? All unsaved progress will be lost.")):
            self.master.destroy()

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

    def mouse_hover_handler(self,
                            event: tk.Event,
                            entity_idx: int,
                            underline: bool = True,
                            recursive: bool = True,
                            relation: Optional[str] = None):
        if event.type is tk.EventType.Enter:
            for span in self.markup.get_spans(entity_idx):
                self.text_box.add_extra_highlight(span, underline=underline)
            self.entity2label[entity_idx].enter(relation=relation)
        else:
            for span in self.markup.get_spans(entity_idx):
                self.text_box.remove_extra_highlight(span)
            self.entity2label[entity_idx].leave()

        if recursive:
            for child_entity_idx in self.markup.get_child_entities(entity_idx):
                self.mouse_hover_handler(event, child_entity_idx, underline=False, recursive=False, relation="child")

            for parent_entity_idx in self.markup.get_parent_entities(entity_idx):
                self.mouse_hover_handler(event, parent_entity_idx, underline=False, recursive=False, relation="parent")

    def open_file_handler(self):
        if (self.markup
                and self.modified
                and not messagebox.askokcancel("Open", "Are you sure? All unsaved progress will be lost.")):
            return

        path = filedialog.askopenfilename(filetypes=[("All supported types", "*.txt *.json"),
                                                     ("Plain text", "*.txt"),
                                                     ("JSON Markup", "*.json")])
        if path:
            self.open_file(path)

    def popup_label_menu(self, event: tk.Event, entity_idx: int):
        states = {
            "Merge": "disabled",
            "Set as parent": "disabled",
            "Unset parent": "disabled",
            "Delete": "active"
        }
        self.popup_menu_entity = entity_idx

        if self.selected_entity is not None and self.selected_entity != self.popup_menu_entity:

            states["Merge"] = "active"

            if self.markup.is_child_of(self.selected_entity, self.popup_menu_entity):
                states["Unset parent"] = "active"
            else:
                states["Set as parent"] = "active"

        for key, value in states.items():
            self.label_menu.entryconfigure(key, state=value)

        try:
            self.render_menu(self.label_menu, event.x_root, event.y_root)
        finally:
            self.label_menu.grab_release()

    def popup_text_menu(self, event: tk.Event):
        index = self.text_box.index(f"@{event.x},{event.y}")
        spans = list(self.text_box.get_spans_at_index(index))
        if not self.text_box.selection_exists() and not spans:
            return

        self.text_menu.delete(0, "end")
        if self.text_box.selection_exists():
            span = self.text_box.get_selection_indices()
            if not self.markup.span_exists(span):
                span_text = self.text_box.get(*span)
                self.text_menu.add_command(label=f"Add \"{span_text}\"",
                                            command=partial(self.new_entity, span=span))
        for span in spans:
            span_text = self.text_box.get(*span)
            self.text_menu.add_command(label=f"Delete \"{span_text}\"",
                                       command=partial(self.delete_span, span=span))
        self.text_menu.update()

        try:
            self.render_menu(self.text_menu, event.x_root, event.y_root)
        finally:
            self.text_menu.grab_release()

    def save_file_handler(self):
        if self.filename is None or not self.filename.endswith(".json"):
            self.save_file_as_handler()
        else:
            self.export(self.filename)

    def save_file_as_handler(self):
        if self.filename is None:
            initialdir = None
            initialfile = None
        else:
            initialdir, initialfile = os.path.split(self.filename)
            if not initialfile.endswith(".json"):
                initialfile = os.path.splitext(initialfile)[0] + ".json"

        path = filedialog.asksaveasfilename(confirmoverwrite=True,
                                            defaultextension=".json",
                                            filetypes=[("JSON Markup", "*.json")],
                                            initialdir=initialdir,
                                            initialfile=initialfile)
        if path:
            self.export(path)

    # Logic handlers ###################################################################################################

    @undoable
    def add_span_to_entity(self, span: Span, entity_idx: int):
        try:
            self.markup.add_span_to_entity(span, entity_idx)
            self.render_entities()
        except RuntimeError as e:
            self.set_status(e.args[0])

    @undoable
    def delete_entity(self) -> str:
        self.markup.delete_entity(self.popup_menu_entity)
        if self.selected_entity == self.popup_menu_entity:
            self.selected_entity = None
        self.color_stack.append(self.entity2color.pop(self.popup_menu_entity))
        self.render_entities()

    @undoable
    def delete_span(self, span: Span):
        removed_entity = self.markup.delete_span(span)
        if removed_entity is not None:
            self.color_stack.append(self.entity2color.pop(removed_entity))
            if self.selected_entity == removed_entity:
                self.selected_entity = None
        self.render_entities()

    @undoable
    def merge(self):
        removed_entity = self.markup.merge(self.selected_entity, self.popup_menu_entity)
        if removed_entity is not None:
            self.color_stack.append(self.entity2color.pop(removed_entity))
        self.render_entities()

    @undoable
    def new_entity(self, span: Optional[Span] = None):
        try:
            if span is None:
                span = self.text_box.get_selection_indices()
            self.text_box.clear_selection()
            self.markup.new_entity(span)
            self.render_entities()
        except RuntimeError as e:
            self.set_status(e.args[0])

    def open_file(self, path: str):
        if path.endswith(".txt"):
            try:
                with open(path, encoding="utf8") as f:
                    text = f.read()
                self.text_box.set_text(text)
                self.markup = Markup()
                self.reset_state()
                self.render_entities()
                self.filename = os.path.abspath(path)
            except UnicodeDecodeError:
                self.set_status(f"error: couldn't read file at \"{path}\"")
        elif path.endswith(".json"):
            try:
                old_text = self.text_box.get("1.0", "end-1c")
                with open(path, encoding="utf8") as f:
                    data = json.load(f)
                self.text_box.set_text(data["text"])
                self.read_markup(data)
                self.reset_state()
                self.render_entities()
                self.filename = os.path.abspath(path)
            except:
                self.text_box.set_text(old_text)
                self.render_entities()
                self.set_status(f"error: couldn't read file at \"{path}\"")
                self.master.update_idletasks()
        else:
            self.set_status(f"error: invalid file type at \"{path}\"")

    def read_markup(self, data: dict) -> Markup:
        markup = Markup()
        for entity_idx, entity in enumerate(data["entities"]):
            markup.new_entity(self.text_box.convert_char_to_tk(entity[0]))
            for span in entity[1:]:
                markup.add_span_to_entity(self.text_box.convert_char_to_tk(span), entity_idx)
        for parent_entity_idx, child_entities in enumerate(data["includes"]):
            for child_entity_idx in child_entities:
                markup.add_child_entity(child_entity_idx, parent_entity_idx)
        self.markup = markup

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.markup)
            self.markup = self.redo_stack.pop()
            self.render_entities()

    @undoable
    def set_parent(self):
        self.markup.add_child_entity(self.selected_entity, self.popup_menu_entity)
        self.render_entities()

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.markup)
            self.markup = self.undo_stack.pop()
            self.render_entities()

    @undoable
    def unset_parent(self):
        self.markup.remove_child_entity(self.selected_entity, self.popup_menu_entity)
        self.render_entities()

    # Renderers ########################################################################################################

    def get_entity_color(self, entity_idx: int) -> str:
        if entity_idx not in self.entity2color:
            self.entity2color[entity_idx] = self.color_stack.pop() if self.color_stack else next(self.all_colors)
        return self.entity2color[entity_idx]

    def render_entities(self):
        for row in range(1, self.panel.grid_size()[1]):
            for child in self.panel.grid_slaves(row=row):
                child.destroy()
        self.text_box.clear_tags()

        entities = sorted(self.markup.get_entities(), key=lambda idx: (self.markup.has_children(idx), idx))
        n_multientities = sum(int(self.markup.has_children(idx)) for idx in entities)
        if n_multientities:
            label = tk.Label(self.panel, text="Parent Entities")
            label.grid(row=len(entities) - n_multientities + 1)

        for position, entity_idx in enumerate(entities):
            color = self.get_entity_color(entity_idx)
            for span in self.markup.get_spans(entity_idx):
                self.text_box.add_highlight(span, entity_idx, color)
            label_text = self.text_box.get_entity_label(entity_idx, self.LABEL_WIDTH)

            label = MarkupLabel(self.panel, text=label_text, background=color, borderwidth=0, relief="solid")
            label.grid(row=position + 1 + int(self.markup.has_children(entity_idx)), sticky=tk.W)
            label.bind("<Enter>", partial(self.mouse_hover_handler, entity_idx=entity_idx))
            label.bind("<Leave>", partial(self.mouse_hover_handler, entity_idx=entity_idx))
            label.bind(f"<ButtonRelease-{LEFT_MOUSECLICK}>", partial(self.mouse_handler_label, entity_idx=entity_idx))
            label.bind(f"<Button-{RIGHT_MOUSECLICK}>", partial(self.popup_label_menu, entity_idx=entity_idx))
            self.entity2label[entity_idx] = label

        self.text_box.fix_overlapping_highlights()

        if self.selected_entity is not None:
            self.entity2label[self.selected_entity].select()

    def render_menu(self, menu: tk.Menu, x: int, y: int):
        w, h = menu.winfo_reqwidth(), menu.winfo_reqheight()
        h //= menu.index("end") + 1
        menu.tk_popup(x + w // 2 * int(NOT_MAC), y + h // 2 * int(NOT_MAC), 0)

    def set_status(self, message: str, duration: int = 5000):
        self.status_bar.configure(text=message)
        self.after(duration, lambda: self.status_bar.configure(text=""))

    # Export ###########################################################################################################

    def export(self, path: str):
        old_entities = []
        for entity_idx in self.markup.get_entities():
            spans = sorted(self.text_box.convert_tk_to_char(span) for span in self.markup.get_spans(entity_idx))
            old_entities.append((spans, entity_idx))
        old_entities.sort()

        index_mapping = {}
        entities = []
        for spans, old_entity_idx in old_entities:
            index_mapping[old_entity_idx] = len(entities)
            entities.append(spans)

        includes = [None for _ in entities]
        for old_entity_idx, new_entity_idx in index_mapping.items():
            child_entities = sorted(index_mapping[i]
                                    for i in self.markup.get_child_entities(old_entity_idx))
            includes[new_entity_idx] = child_entities
        assert all(elem is not None for elem in includes)

        state = {
            "entities": entities,
            "includes": includes,
            "text": self.text_box.get("1.0", "end-1c")
        }

        with open(path, mode="w", encoding="utf8") as f:
            json.dump(state, f, ensure_ascii=False)
        self.filename = path
        self.modified = False
        self.set_status(f"Saved to {path}")
