from dataclasses import dataclass, fields
from typing import *


Span = Tuple[str, str]


@dataclass
class DiffInfo:
    comment: Optional[str]
    shared_comment: Optional[str]

    def __iter__(self):
        return iter(getattr(self, field.name) for field in fields(self))

    def is_empty(self):
        return all(value is None for value in self)


class Entity:
    def __init__(self, idx: int):
        self.idx = idx
        self.spans: Set[Span] = set()

        self.children: Set[Entity] = set()
        self.parents: Set[Entity] = set()

    def __new__(cls, idx: int):
        """ Makes sure .idx is available for deepcopy module """
        obj = super().__new__(cls)
        obj.idx = idx
        return obj

    def __getnewargs__(self):
        """ Makes sure .idx is available for deepcopy module """
        return (self.idx, )

    def __hash__(self) -> int:
        return self.idx

    def add_child(self, child: "Entity"):
        if child is not self:
            self.children.add(child)

    def add_parent(self, parent: "Entity"):
        if parent is not self:
            self.parents.add(parent)

    def update(self, another: "Entity"):
        """ Moves spans from another into self. """
        if self is another:
            raise RuntimeError(f"error: cannot merge into itself")
        self.spans.update(another.spans)
        another.spans = set()

        while another.children:
            child_entity = another.children.pop()
            child_entity.parents.remove(another)
            child_entity.add_parent(self)
            self.add_child(child_entity)

        while another.parents:
            parent_entity = another.parents.pop()
            parent_entity.children.remove(another)
            parent_entity.add_child(self)
            self.add_parent(parent_entity)


class Markup:
    def __init__(self):
        self._span2entity: Dict[Span, Entity] = {}
        self._entities: List[Optional[Entity]] = []

        self.diff_info: Dict[Span, DiffInfo] = {}

    def __bool__(self):
        return bool(self._span2entity)

    def add_child_entity(self, child_idx: int, parent_idx: int):
        child = self._entities[child_idx]
        parent = self._entities[parent_idx]
        parent.add_child(child)
        child.add_parent(parent)

    def add_span_to_entity(self, span: Span, entity_idx: int):
        if span in self._span2entity:
            raise RuntimeError(f"error: span already belongs to entity {self._span2entity[span].idx}")
        entity = self._entities[entity_idx]
        assert entity is not None
        entity.spans.add(span)
        self._span2entity[span] = entity

    def delete_entity(self, entity_idx: int):
        entity = self._entities[entity_idx]
        self._entities[entity_idx] = None
        for span in entity.spans:
            del self._span2entity[span]
        while entity.parents:
            parent = entity.parents.pop()
            parent.children.remove(entity)
        while entity.children:
            child = entity.children.pop()
            child.parents.remove(entity)

    def delete_span(self, span: Span) -> Optional[int]:
        """ Returns the index of deleted entity if span was the last span in it. """
        if span not in self._span2entity:
            raise RuntimeError(f"error: span does not exist")
        entity = self._span2entity[span]
        entity.spans.remove(span)
        del self._span2entity[span]
        if not entity.spans:
            self.delete_entity(entity.idx)
            return entity.idx

    def has_children(self, entity_idx: int) -> bool:
        return len(self._entities[entity_idx].children) > 0

    def get_child_entities(self, entity_idx: int) -> Iterable[int]:
        return (child.idx for child in self._entities[entity_idx].children)

    def get_entities(self) -> Iterable[int]:
        return (idx for idx, entity in enumerate(self._entities) if entity is not None)

    def get_entity(self, span: Span) -> int:
        return self._span2entity[span].idx

    def get_parent_entities(self, entity_idx: int) -> Iterable[int]:
        return (parent.idx for parent in self._entities[entity_idx].parents)

    def get_spans(self, entity_idx: int) -> Iterable[Span]:
        return iter(self._entities[entity_idx].spans)

    def is_child_of(self, child_idx: int, parent_idx: int) -> bool:
        return self._entities[child_idx] in self._entities[parent_idx].children

    def merge(self, a_idx: int, b_idx: int) -> int:
        """ Returns the id of the entity that is no more"""
        a = self._entities[a_idx]
        b = self._entities[b_idx]
        for span in b.spans:
            self._span2entity[span] = a
        a.update(b)
        assert not(b.spans) and not(b.children) and not(b.parents)
        self._entities[b.idx] = None
        return b_idx

    def new_entity(self, span: Span) -> int:
        """ Return the new entity's id """
        if span in self._span2entity:
            raise RuntimeError(f"error: span already belongs to entity {self._span2entity[span].idx}")
        entity = Entity(len(self._entities))
        entity.spans.add(span)
        self._span2entity[span] = entity
        self._entities.append(entity)
        return entity.idx

    def remove_child_entity(self, child_idx: int, parent_idx: int):
        child_entity = self._entities[child_idx]
        parent_entity = self._entities[parent_idx]
        parent_entity.children.remove(child_entity)
        child_entity.parents.remove(parent_entity)

    def span_exists(self, span: Span) -> bool:
        return span in self._span2entity
