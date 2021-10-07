from typing import *


Span = Tuple[str, str]


class Entity:
    def __init__(self, idx: int):
        self.idx = idx
        self.spans: Set[Span] = set()

    def __hash__(self) -> int:
        return self.idx

    def update(self, another: "Entity"):
        """ Adds spans from another into self. """
        if self is another:
            raise RuntimeError(f"error: cannot merge into itself")
        if isinstance(another, MultiEntity) != isinstance(self, MultiEntity):
            raise RuntimeError(f"error: cannot merge entities of different types")
        self.spans.update(another.spans)


class MultiEntity(Entity):
    def __init__(self, idx: int):
        super().__init__(idx)
        self.entities: Set[Entity] = set()

    def update(self, another: "MultiEntity"):
        """ Adds spans and entitites from another into self. """
        super().update(another)
        self.entities.update(another.entities)


class Markup:
    def __init__(self):
        self._span2entity: Dict[Span, Entity] = {}
        self._entities: List[Optional[Entity]] = []

    def add_span_to_entity(self, span: Span, entity_idx: int):
        if span in self._span2entity:
            raise RuntimeError(f"error: span already belongs to entity {self._span2entity[span].idx}")
        entity = self._entities[entity_idx]
        assert entity is not None
        entity.spans.add(span)
        self._span2entity[span] = entity

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

    def get_spans(self, entity_idx: int) -> Iterable[Span]:
        return iter(self._entities[entity_idx].spans)

    def is_multi_entity(self, entity_idx: int) -> bool:
        return isinstance(self._entities[entity_idx], MultiEntity)

    def merge(self, a: Entity, b: Entity):
        if isinstance(a, MultiEntity) == isinstance(b, MultiEntity):
            a.update(b)
            for span in b.spans:
                self._span2entity[span] = a
            self._entities[b.idx] = None
        else:
            multi, single = (a, b) if isinstance(a, MultiEntity) else (b, a)
            multi.entities.add(single)

    def new_entity(self, span: Span, multi: bool = False) -> int:
        if span in self._span2entity:
            raise RuntimeError(f"error: span already belongs to entity {self._span2entity[span].idx}")
        cls = Entity if not multi else MultiEntity
        entity = cls(len(self._entities))
        entity.spans.add(span)
        self._span2entity[span] = entity
        self._entities.append(entity)
        return entity.idx


        # if span in self._span2entity:
        #     raise RuntimeError(f"error: cannot add to entity {entity_id}; current entities: {self._span2entity[span]}")






# Span = Tuple[int, int]
# Entity = Set[Span]


# class Markup:
#     def __init__(self):
#         self._span2entity: Dict[Span, Entity] = {}

#     @property
#     def entities(self) -> List[List[Span]]:
#         """ Returns a sorted list of entities that contain more than 1 element. """
#         ids = set()
#         unique_entities = []
#         for entity in self._span2entity.values():
#             if id(entity) not in ids:
#                 ids.add(id(entity))
#                 if len(entity) > 1:
#                     unique_entities.append(sorted(entity))
#         return sorted(unique_entities)

#     def merge(self, a_span: Span, b_span: Span):
#         a_entity = self._get_entity(a_span)
#         b_entity = self._get_entity(b_span)
#         assert a_entity is not b_entity, "Entities are already merged"
#         a_entity.update(b_entity)
#         for span in b_entity:
#             self._span2entity[span] = a_entity

#     def _get_entity(self, span: Span) -> Entity:
#         if span not in self._span2entity:
#             self._span2entity[span] = {span}
#         return self._span2entity[span]
