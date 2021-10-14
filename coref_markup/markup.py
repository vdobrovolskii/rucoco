from typing import *


Span = Tuple[str, str]


class Entity:
    def __init__(self, idx: int):
        self.idx = idx
        self.spans: Set[Span] = set()
        self.part_of: Set[MultiEntity] = set()

    def __hash__(self) -> int:
        return self.idx

    def update(self, another: "Entity"):
        """ Moves spans from another into self. """
        if self is another:
            raise RuntimeError(f"error: cannot merge into itself")
        if isinstance(another, MultiEntity) != isinstance(self, MultiEntity):
            raise RuntimeError(f"error: cannot merge entities of different types")
        self.spans.update(another.spans)
        another.spans = set()

        while another.part_of:
            entity = another.part_of.pop()
            entity.entities.remove(another)
            self.part_of.add(entity)
            entity.entities.add(self)


class MultiEntity(Entity):
    def __init__(self, idx: int):
        super().__init__(idx)
        self.entities: Set[Entity] = set()

    def update(self, another: "MultiEntity"):
        """ Moves spans and entitites from another into self. """
        super().update(another)
        while another.entities:
            entity = another.entities.pop()
            entity.part_of.remove(entity)
            entity.part_of.add(self)
            self.entities.add(entity)

class Markup:
    def __init__(self):
        self._span2entity: Dict[Span, Entity] = {}
        self._entities: List[Optional[Entity]] = []

    def add_entity_to_mentity(self, e_idx: int, m_idx: int):
        entity = self._entities[e_idx]
        mentity = self._entities[m_idx]
        assert isinstance(mentity, MultiEntity)
        mentity.entities.add(entity)
        entity.part_of.add(mentity)

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
        while entity.part_of:
            parent = entity.part_of.pop()
            parent.entities.remove(entity)
        if isinstance(entity, MultiEntity):
            while entity.entities:
                child = entity.entities.pop()
                child.part_of.remove(entity)

    def delete_span(self, span: Span):
        if span not in self._span2entity:
            raise RuntimeError(f"error: span does not exist")
        entity = self._span2entity[span]
        entity.spans.remove(span)
        if not entity.spans:
            self._entities[entity.idx] = None
        del self._span2entity[span]

    def get_entities(self) -> Iterable[int]:
        return (idx for idx, entity in enumerate(self._entities) if entity is not None)

    def get_inner_entities(self, entity_idx: int) -> Iterable[int]:
        return (entity.idx for entity in self._entities[entity_idx].entities)

    def get_outer_entities(self, entity_idx: int) -> Iterable[int]:
        return (entity.idx for entity in self._entities[entity_idx].part_of)

    def get_spans(self, entity_idx: int) -> Iterable[Span]:
        return iter(self._entities[entity_idx].spans)

    def is_multi_entity(self, entity_idx: int) -> bool:
        return isinstance(self._entities[entity_idx], MultiEntity)

    def is_part_of(self, e_idx: int, m_idx: int) -> bool:
        return self.is_multi_entity(m_idx) and self._entities[e_idx] in self._entities[m_idx].entities

    def merge(self, a_idx: int, b_idx: int) -> Optional[int]:
        """ Returns the id of the entity that is no more"""
        a = self._entities[a_idx]
        b = self._entities[b_idx]
        a.update(b)
        for span in b.spans:
            self._span2entity[span] = a
        for mentity in b.part_of:
            mentity.entities.remove(b)
        self._entities[b.idx] = None
        return b_idx

    def new_entity(self, span: Span, multi: bool = False) -> int:
        """ Return the new entity's id """
        if span in self._span2entity:
            raise RuntimeError(f"error: span already belongs to entity {self._span2entity[span].idx}")
        cls = Entity if not multi else MultiEntity
        entity = cls(len(self._entities))
        entity.spans.add(span)
        self._span2entity[span] = entity
        self._entities.append(entity)
        return entity.idx

    def remove_entity_from_mentity(self, e_idx: int, m_idx: int):
        entity = self._entities[e_idx]
        mentity = self._entities[m_idx]
        assert isinstance(mentity, MultiEntity)
        mentity.entities.remove(entity)
        entity.part_of.remove(mentity)
