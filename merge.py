import argparse
import copy
import itertools
import json
from typing import *


Span = Tuple[int, int]


class Entity:
    def __init__(self, spans: Iterable[Span]):
        self.spans: Set[Span] = set(spans)
        self._included_spans: Set[Span] = set()

    def add_included_spans(self, spans: Iterable[Span]):
        self._included_spans.update(spans)

    @property
    def included_spans(self) -> Set[Span]:
        return self._included_spans - self.spans


class Markup:
    def __init__(self,
                 entities: List[List[Span]],
                 includes: List[int],
                 text: str):
        self.entities = self._parse_entities(entities, includes)
        self.span2entity: Dict[Span, Entity] = {
            span: entity
            for entity in self.entities
            for span in entity.spans
        }
        self.text = text

    def add_entity(self, span: Span):
        assert span not in self.span2entity
        entity = Entity([span])
        self.entities.add(entity)
        self.span2entity[span] = entity

    def get_or_add_entity(self, span: Span) -> Entity:
        if span not in self.span2entity:
            self.add_entity(span)
        return self.span2entity[span]

    def merge_spans(self, a_span: Span, b_span: Span):
        a = self.get_or_add_entity(a_span)
        b = self.get_or_add_entity(b_span)
        if a is b:
            return
        self.entities.remove(a)
        self.entities.remove(b)

        new_entity = Entity(itertools.chain(a.spans, b.spans))
        new_entity.add_included_spans(itertools.chain(a.included_spans,
                                                      b.included_spans))

        self.entities.add(new_entity)
        for span in itertools.chain(a.spans, b.spans):
            self.span2entity[span] = new_entity

    def to_dict(self) -> dict:
        entities = sorted(self.entities, key=lambda x: min(x.spans))
        entity2idx = {entity: i for i, entity in enumerate(entities)}

        includes = []
        for entity in entities:
            included_entities = {self.span2entity[span]
                                 for span in entity.included_spans}
            includes.append(sorted(entity2idx[e] for e in included_entities))

        return {
            "entities": [sorted(entity.spans) for entity in entities],
            "includes": includes,
            "text": self.text
        }

    @staticmethod
    def _parse_entities(entities: List[List[Span]],
                        includes: List[int]) -> Set[Entity]:
        entities: List[Entity] = [Entity(spans) for spans in entities]
        for entity_idx, inner_entities in enumerate(includes):
            for inner_entity_idx in inner_entities:
                entities[entity_idx].add_included_spans(entities[inner_entity_idx].spans)
        return set(entities)


def merge(versions: List[Markup]) -> Markup:
    if not all(l.text == r.text for l, r in zip(versions, versions[1:])):
        raise ValueError("Texts are not the same")
    result = copy.deepcopy(versions[0])
    for version in versions[1:]:
        for version_entity in version.entities:
            spans = list(version_entity.spans)
            for l, r in zip(spans, spans[1:]):
                result.merge_spans(l, r)
    return result


def normalize(s: str) -> str:
    return s.replace("\r\n", "\n")


def read_markup(path: str) -> Markup:
    return Markup(**read_markup_dict)


def read_markup_dict(path: str) -> Markup:
    with open(path, mode="r", encoding="utf8") as f:
        markup_dict = json.load(f)
    markup_dict["entities"] = [[tuple(span) for span in entity]
                               for entity in markup_dict["entities"]]
    markup_dict["text"] = normalize(markup_dict["text"])
    return markup_dict


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("file", nargs="+",
                           help="Paths to markup files to merge.")
    argparser.add_argument("--out", "-o", required=True,
                           help="Output file name/path.")
    args = argparser.parse_args()

    if len(args.file) < 2:
        raise ValueError("At least two input files are required")

    versions = []
    for filename in args.file:
        versions.append(read_markup(filename))

    merged_markup = merge(versions)

    with open(args.out, mode="w", encoding="utf8") as f:
        json.dump(merged_markup.to_dict(), f, ensure_ascii=False)
