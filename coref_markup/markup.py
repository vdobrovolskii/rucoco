from typing import *


Span = Tuple[str, str]


class Entity:
    def __init__(self, idx: int):
        self.idx = idx
        self.spans: Set[Span] = set()
        
        self.children: Set[Entity] = set()
        self.parents: Set[Entity] = set()

    def __hash__(self) -> int:
        return self.idx

    def update(self, another: "Entity"):
        """ Moves spans from another into self. """
        if self is another:
            raise RuntimeError(f"error: cannot merge into itself")
        self.spans.update(another.spans)
        another.spans = set()

        while another.children:
            child_entity = another.children.pop()
            child_entity.parents.remove(another)
            child_entity.parents.add(self)
            self.children.add(child_entity)

        while another.parents:
            parent_entity = another.parents.pop()
            parent_entity.children.remove(another)
            parent_entity.children.add(self)
            self.parents.add(parent_entity)


class Markup:
    def __init__(self):
        self._span2entity: Dict[Span, Entity] = {}
        self._entities: List[Optional[Entity]] = []

    def __bool__(self):
        return bool(self._span2entity)

    def add_child_entity(self, child_idx: int, parent_idx: int):
        child = self._entities[child_idx]
        parent = self._entities[parent_idx]
        parent.children.add(child)
        child.parents.add(parent)

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

    def get_child_entities(self, entity_idx: int, recursive: bool = True) -> Iterable[int]:
        entity = self._entities[entity_idx]
        entities = set()
        for child_entity in entity.children:
            entities.add(child_entity.idx)
            if recursive:
                entities.update(self.get_child_entities(child_entity.idx))
        return entities

    def get_entities(self) -> Iterable[int]:
        return (idx for idx, entity in enumerate(self._entities) if entity is not None)

    def get_parent_entities(self, entity_idx: int) -> Iterable[int]:
        entities = set()
        for parent_entity in self._entities[entity_idx].parents:
            entities.add(parent_entity.idx)
            entities.update(self.get_parent_entities(parent_entity.idx))
        return entities

    def get_spans(self, entity_idx: int) -> Iterable[Span]:
        return iter(self._entities[entity_idx].spans)

    def is_child_of(self, child_idx: int, parent_idx: int) -> bool:
        return self._entities[child_idx] in self._entities[parent_idx].children

    def merge(self, a_idx: int, b_idx: int) -> Optional[int]:
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
