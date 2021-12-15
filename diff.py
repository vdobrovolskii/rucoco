import argparse
from collections import defaultdict
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


def diff(a: Markup, b: Markup, context_len: int = 32):
    if a.text != b.text:
        raise ValueError("Texts are not the same")
    a_spans = set(a.span2entity.keys())
    b_spans = set(b.span2entity.keys())

    a_not_b_spans = a_spans - b_spans
    if a_not_b_spans:
        print_separator("Spans in A but not in B")
        diff_spans(a, a_not_b_spans, context_len)

    b_not_a_spans = b_spans - a_spans
    if b_not_a_spans:
        print_separator("Spans in B but not in A")
        diff_spans(b, b_not_a_spans, context_len)

    common_spans = a_spans & b_spans
    entity_mapping = get_entity_mapping(a, b, common_spans)
    mixed_spans = set()
    for a_entity, b_entity in entity_mapping.items():
        mixed_spans.update((a_entity.spans & common_spans) - b_entity.spans)
    if mixed_spans:
        print_separator("Spans belonging to different entities")
        diff_entities(a, b, mixed_spans, a.text, context_len)

    missing_children_a = get_missing_children(
        a, b, common_spans, entity_mapping
    )
    if missing_children_a:
        print_separator("Children in A but not in B")
        diff_children(missing_children_a, a.text)

    missing_children_b = get_missing_children(
        b, a, common_spans, get_entity_mapping(b, a, common_spans)
    )
    if missing_children_b:
        print_separator("Children in B but not in A")
        diff_children(missing_children_b, a.text)


def diff_children(children_and_parents: Set[Tuple[Entity, Entity]],
                  text: str):
    for child, parent in sorted(children_and_parents,
                                key=lambda x: min(x[1].spans)):
        print(f"Parent: {entity_to_str(parent, text)}")
        print(f"Child:  {entity_to_str(child, text)}")
        print()


def diff_entities(a: Markup, b: Markup,
                  mixed_spans: Set[Span],
                  text: str,
                  context_len: int):
    for span in sorted(mixed_spans):
        a_entity = a.span2entity[span]
        b_entity = b.span2entity[span]

        print(f"Position:    {span}")
        print(f"Text:        {text[slice(*span)]}")
        print(f"Context:     {get_context(span, text, context_len)}")
        print(f"Entity in A: {entity_to_str(a_entity, text)}")
        print(f"Entity in B: {entity_to_str(b_entity, text)}")
        print()


def diff_spans(ref: Markup, spans: Set[Span], context_len: int):
    for span in sorted(spans):
        print(f"Entity:   {entity_to_str(ref.span2entity[span], ref.text)}")
        print(f"Position: {span}")
        print(f"Text:     {ref.text[slice(*span)]}")
        print(f"Context:  {get_context(span, ref.text, context_len)}")
        print()


def entity_to_str(entity: Entity, text, max_spans: int = 3) -> str:
    spans_by_length = sorted(entity.spans,
                             key=lambda x: x[1] - x[0], reverse=True)
    spans_by_position = sorted(spans_by_length[:max_spans])
    label = f"<<{'//'.join('{}' for _ in spans_by_position)}>>"
    return label.format(*(text[slice(*span)]
                            for span in spans_by_position))


def f1(precision: float, recall: float, eps: float = 1e-7) -> float:
    return (precision * recall) / (precision + recall + eps) * 2


def get_children(data: dict, idx: int) -> List[Span]:
    """ Returns a list of all the immediate AND most distant children """
    children = set()
    for child_idx in data["includes"][idx]:
        children.update(data["entities"][child_idx])

    visited = set()
    stack = list(data["includes"][idx])
    while stack:
        child_idx = stack.pop()
        visited.add(child_idx)
        if not data["includes"][child_idx]:
            children.update(data["entities"][child_idx])
        else:
            for grandchild_idx in data["includes"][child_idx]:
                if grandchild_idx not in visited:
                    stack.append(grandchild_idx)

    return sorted(children)


def get_context(span: Span, text: str, context_len: int) -> str:
    return repr(f"{text[span[0] - context_len:span[0]]}"
                f">>{text[slice(*span)]}<<"
                f"{text[span[1]:span[1] + context_len]}")


def get_entity_mapping(a: Markup,
                       b: Markup,
                       common_spans: Set[Span]) -> Dict[Entity, Entity]:
    mapping = {}
    for a_entity in a.entities:
        if any(span in common_spans for span in a_entity.spans):
            mapping[a_entity] = max(
                b.entities,
                key=lambda b_entity: len(a_entity.spans & b_entity.spans)
            )
    return mapping


def get_missing_children(a: Markup,
                         b: Markup,
                         common_spans: Set[Span],
                         entity_mapping: Dict[Entity, Entity]
                         ) -> Set[Tuple[Entity, Entity]]:
    """
    Returns:
        missing_children: a set of pairs (child, parent), where each child
            is annotated in A but not in B
        accuracy: the percentage of children in A correctly identified in B
    """
    total_children, correct_children = 0, 0

    missing_children = set()
    for a_entity, b_entity in entity_mapping.items():
        a_children = {entity_mapping[a.span2entity[span]]
                      for span in (a_entity.included_spans & common_spans)}
        b_children = {b.span2entity[span]
                      for span in (b_entity.included_spans & common_spans)}
        a_children_missing = {(child, a_entity)
                              for child in (a_children - b_children)}
        missing_children.update(a_children_missing)

        total_children += len(a_children)
        correct_children += len(a_children) - len(a_children_missing)

    return missing_children


def lea(a: dict, b: dict, eps: float = 1e-7) -> float:
    a_clusters = a["entities"]
    b_clusters = b["entities"]

    recall, r_weight = _lea(a_clusters, b_clusters)
    precision, p_weight = _lea(b_clusters, a_clusters)

    doc_precision = precision / (p_weight + eps)
    doc_recall = recall / (r_weight + eps)
    return f1(doc_precision, doc_recall, eps=eps)


def _lea(key: List[List[Span]],
         response: List[List[Span]]) -> Tuple[float, float]:
        """ See aclweb.org/anthology/P16-1060.pdf. """
        response_clusters = [set(cluster) for cluster in response]
        response_map = {mention: cluster
                        for cluster in response_clusters
                        for mention in cluster}
        importances = []
        resolutions = []
        for entity in key:
            size = len(entity)
            if size == 1:  # entities of size 1 are not annotated
                continue
            importances.append(size)
            correct_links = 0
            for i in range(size):
                for j in range(i + 1, size):
                    correct_links += int(entity[i]
                                         in response_map.get(entity[j], {}))
            resolutions.append(correct_links / (size * (size - 1) / 2))
        res = sum(imp * res for imp, res in zip(importances, resolutions))
        weight = sum(importances)
        return res, weight


def lea_children(a: dict, b: dict, eps: float = 1e-7) -> float:
    a_clusters = [(spans, get_children(a, i))
                  for i, spans in enumerate(a["entities"])]
    b_clusters = [(spans, get_children(b, i))
                  for i, spans in enumerate(b["entities"])]

    recall, r_weight = _lea_children(a_clusters, b_clusters)
    precision, p_weight = _lea_children(b_clusters, a_clusters)

    doc_precision = precision / (p_weight + eps)
    doc_recall = recall / (r_weight + eps)
    return f1(doc_precision, doc_recall, eps=eps)


def _lea_children(key: List[Tuple[List[Span], List[Span]]],
                  response: List[Tuple[List[Span], List[Span]]]
                  ) -> Tuple[float, float]:
        response_clusters = [set(cluster) for cluster, _ in response]
        response_map = {mention: cluster
                        for cluster in response_clusters
                        for mention in cluster}
        response_children_map = defaultdict(set)
        for cluster, children in response:
            for mention in children:
                response_children_map[mention].update(cluster)

        importances = []
        resolutions = []
        for entity, children in key:
            size = len(entity)
            if size > 1:  # entities of size 1 are not annotated
                importances.append(size)
                correct_links = 0
                for i in range(size):
                    for j in range(i + 1, size):
                        correct_links += int(entity[i]
                                            in response_map.get(entity[j], {}))
                resolutions.append(correct_links / (size * (size - 1) / 2))

            if not children:
                continue
            importances.append(len(children))
            correct_links = 0
            for mention in entity:
                for child in children:
                    correct_links += int(mention in response_children_map.get(child, {}))
            resolutions.append(correct_links / (size * len(children)))

        res = sum(imp * res for imp, res in zip(importances, resolutions))
        weight = sum(importances)
        return res, weight


def metrics(a: dict, b: dict):
    print_separator("Metrics")

    print(f"LEA (w/o child spans): {lea(a, b):.3f}")
    print(f"LEA (w/  child spans): {lea_children(a, b):.3f}")


def print_separator(message: str, width: int = 120):
    line_width = max(0, width - len(message) - 1)
    print(f"\n{message} {'=' * line_width}\n")


def read_markup(path: str) -> Markup:
    return Markup(**read_markup_dict(path))


def read_markup_dict(path: str) -> dict:
    with open(path, mode="r", encoding="utf8") as f:
        markup_dict = json.load(f)
    markup_dict["entities"] = [[tuple(span) for span in entity]
                               for entity in markup_dict["entities"]]
    return markup_dict


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("file", nargs=2,
                           help="Paths to markup files to compare")
    args = argparser.parse_args()

    markup_dicts = [read_markup_dict(filename) for filename in args.file]
    versions = [Markup(**markup_dict) for markup_dict in markup_dicts]

    diff(*versions)
    metrics(*markup_dicts)
