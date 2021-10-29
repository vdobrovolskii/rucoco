from functools import partial
from itertools import chain, cycle
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import *

from coref_markup.const import *
from coref_markup.markup import *
from coref_markup.markup_text import *
from coref_markup.markup_label import *
from coref_markup import utils


# TODO: scroll entities
# TODO: config (annotator name, what else?)
# TODO: span and entity texts in error messages (custom Exception class to pass data)
# TODO: remove magic values
# TODO: docstrings
# TODO: mypy and pylint


class Application(ttk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.master = master
        self.pack()

        self.markup = Markup()

        self.reset_state()
        self.build_widgets()

    # Initializers #####################################################################################################

    def build_widgets(self):
        """
        Only making the following visible as instance attributes:
            self.entity_panel
            self.multi_entity_panel
            self.status_bar
            self.text_box
            self.label_menu
            self.text_menu
        """
        self.master.protocol("WM_DELETE_WINDOW", self.close_program_handler)
        self.grid(row=0, column=0, sticky=(tk.N + tk.W + tk.E + tk.S))

        status_bar = ttk.Label(self)
        status_bar.grid(row=1, column=0, columnspan=2, sticky=(tk.N, tk.W))

        text_box = MarkupText(self, wrap="word")
        text_box.bind(f"<ButtonRelease-{LEFT_MOUSECLICK}>", self.mouse_handler_text)
        text_box.bind(f"<Button-{RIGHT_MOUSECLICK}>", self.popup_text_menu)
        text_box.grid(row=0, column=0, sticky=(tk.N+tk.W+tk.E+tk.S))

        text_menu = tk.Menu(self, tearoff=0)

        panel = ttk.Frame(self)
        panel.grid(row=0, column=1, sticky=(tk.N+tk.W+tk.E+tk.S))

        entity_panel = ttk.Frame(panel)
        entity_panel.bind(f"<ButtonRelease-{LEFT_MOUSECLICK}>", self.mouse_handler_panel)
        entity_panel.grid(row=0, column=0, sticky=(tk.N+tk.W+tk.E+tk.S))

        separator = ttk.Separator(panel, orient="vertical")
        separator.grid(row=0, column=1, sticky=(tk.N+tk.S))

        multi_entity_panel = ttk.Frame(panel)
        multi_entity_panel.bind(f"<ButtonRelease-{LEFT_MOUSECLICK}>", self.mouse_handler_panel)
        multi_entity_panel.grid(row=0, column=2, sticky=(tk.N+tk.W+tk.E+tk.S))

        entity_panel_label = ttk.Label(entity_panel, text="Entities")
        entity_panel_label.grid(row=0)

        mentity_panel_label = ttk.Label(multi_entity_panel, text="mEntities")
        mentity_panel_label.grid(row=0)

        new_entity_button = ttk.Button(entity_panel, text="New Entity", command=self.new_entity)
        new_entity_button.grid(row=1)

        new_mentity_button = ttk.Button(multi_entity_panel, text="New mEntity",
                                        command=partial(self.new_entity, multi=True))
        new_mentity_button.grid(row=1)

        label_menu = tk.Menu(self, tearoff=0)
        label_menu.add_command(label="Merge", command=self.merge)
        label_menu.add_command(label="Set as parent", command=self.set_parent)
        label_menu.add_command(label="Unset parent", command=self.unset_parent)
        label_menu.add_command(label="Delete", command=self.delete_entity)

        # Menu
        menubar = tk.Menu()
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open", command=self.open_file_handler)
        file_menu.add_command(label="Save", command=self.save_file_handler)
        menubar.add_cascade(label="File", menu=file_menu)
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Font +", command=text_box.font_increase)
        view_menu.add_command(label="Font -", command=text_box.font_decrease)
        menubar.add_cascade(label="View", menu=view_menu)
        self.master.configure(menu=menubar)

        # Shortcuts
        self.master.bind("<Control-=>", lambda _: self.text_box.font_increase())
        self.master.bind("<Control-minus>", lambda _: self.text_box.font_decrease())

        # Managing resizing
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=1)
        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(2, weight=1)

        # Registering attributes
        self.entity_panel = entity_panel
        self.multi_entity_panel = multi_entity_panel
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

    # Event handlers ###################################################################################################

    def close_program_handler(self):
        if (not self.markup
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
            for inner_entity_idx in self.markup.get_inner_entities(entity_idx):
                self.mouse_hover_handler(event, inner_entity_idx, underline=False, recursive=False)

            for outer_entity_idx in self.markup.get_outer_entities(entity_idx):
                self.mouse_hover_handler(event, outer_entity_idx, underline=False, recursive=False)

    def open_file_handler(self):
        if self.markup and not messagebox.askokcancel("Open", "Are you sure? All unsaved progress will be lost."):
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
        path = filedialog.asksaveasfilename(confirmoverwrite=True,
                                            defaultextension=".json",
                                            filetypes=[("JSON Markup", "*.json")])
        if path:
            with open(path, mode="w", encoding="utf8") as f:
                json.dump(self.export(), f, ensure_ascii=False)

    # Logic handlers ###################################################################################################

    def add_span_to_entity(self, span: Span, entity_idx: int):
        try:
            self.markup.add_span_to_entity(span, entity_idx)
            self.render_entities()
        except RuntimeError as e:
            self.set_status(e.args[0])

    def delete_entity(self) -> str:
        self.markup.delete_entity(self.popup_menu_entity)
        if self.selected_entity == self.popup_menu_entity:
            self.selected_entity = None
        self.color_stack.append(self.entity2color.pop(self.popup_menu_entity))
        self.render_entities()

    def delete_span(self, span: Span):
        removed_entity = self.markup.delete_span(span)
        if removed_entity is not None:
            self.color_stack.append(self.entity2color.pop(removed_entity))
            if self.selected_entity == removed_entity:
                self.selected_entity = None
        self.render_entities()

    def merge(self):
        removed_entity = self.markup.merge(self.selected_entity, self.popup_menu_entity)
        if removed_entity is not None:
            self.color_stack.append(self.entity2color.pop(removed_entity))
        self.render_entities()

    def new_entity(self, multi: bool = False, span: Optional[Span] = None):
        try:
            if span is None:
                span = self.text_box.get_selection_indices()
            self.text_box.clear_selection()
            self.markup.new_entity(span, multi=multi)
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
            except UnicodeDecodeError:
                self.set_status(f"error: couldn't read file at \"{path}\"")
        elif path.endswith(".json"):
            try:
                old_text = self.text_box.get("1.0", "end")
                with open(path, encoding="utf8") as f:
                    data = json.load(f)
                self.text_box.set_text(data["text"])
                self.read_markup(data)
                self.reset_state()
                self.render_entities()
            except:
                self.text_box.set_text(old_text)
                self.set_status(f"error: couldn't read file at \"{path}\"")
        else:
            self.set_status(f"error: invalid file type at \"{path}\"")

    def read_markup(self, data: dict) -> Markup:
        markup = Markup()
        is_multi = list(map(bool, data["includes"]))
        for entity_idx, entity in enumerate(data["entities"]):
            markup.new_entity(self.text_box.convert_char_to_tk(entity[0]), is_multi[entity_idx])
            for span in entity[1:]:
                markup.add_span_to_entity(self.text_box.convert_char_to_tk(span), entity_idx)
        for entity_idx, inner_entities in enumerate(data["includes"]):
            for inner_entity_idx in inner_entities:
                markup.add_entity_to_mentity(inner_entity_idx, entity_idx)
        self.markup = markup

    def set_parent(self):
        self.markup.add_entity_to_mentity(self.selected_entity, self.popup_menu_entity)

    def unset_parent(self):
        self.markup.remove_entity_from_mentity(self.selected_entity, self.popup_menu_entity)

    # Renderers ########################################################################################################

    def get_entity_color(self, entity_idx: int) -> str:
        if entity_idx not in self.entity2color:
            self.entity2color[entity_idx] = self.color_stack.pop() if self.color_stack else next(self.all_colors)
        return self.entity2color[entity_idx]

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
            label.grid(row=placement.grid_size()[1], sticky=tk.W)
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

    def export(self) -> dict:
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
            inner_entities = sorted(index_mapping[i]
                                    for i in self.markup.get_inner_entities(old_entity_idx, recursive=False))
            includes[new_entity_idx] = inner_entities
        assert all(elem is not None for elem in includes)

        return {
            "entities": entities,
            "includes": includes,
            "text": self.text_box.get("1.0", "end-1c")
        }
