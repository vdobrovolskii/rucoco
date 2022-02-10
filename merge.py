import argparse
from collections import defaultdict
from dataclasses import asdict, dataclass
from itertools import combinations, takewhile
import json
import logging
from typing import *
import sys


Span = Tuple[int, int]
Entity = List[Span]


@dataclass
class Markup:
    entities: List[Entity]
    includes: List[List[int]]
    text: str


class SpanInfo:
    def __init__(self, span: Span):
        self.span = span
        self.parents: Set[SpanInfo] = set()
        self.children: Set[SpanInfo] = set()

    @staticmethod
    def have_parent_link(*, ancestor: "SpanInfo", descendant: "SpanInfo") -> bool:
        return (
            descendant in ancestor.children
            or any(SpanInfo.have_parent_link(ancestor=child, descendant=descendant)
                   for child in ancestor.children)
        )

    @staticmethod
    def link(*, parent: "SpanInfo", child: "SpanInfo"):
        parent.children.add(child)
        child.parents.add(parent)

    @staticmethod
    def unlink(*, parent: "SpanInfo", child: "SpanInfo"):
        parent.children.remove(child)
        child.parents.remove(parent)

    def has_parent_links(self) -> bool:
        """ True if has at least one parent or at least one child. """
        return bool(self.parents) or bool(self.children)

    def unlink_all_parents_and_children(self):
        for parent in list(self.parents):
            SpanInfo.unlink(parent=parent, child=self)
        for child in list(self.children):
            SpanInfo.unlink(parent=self, child=child)

    def unlink_redundant_children(self):
        """ Unlinks children that are also grand+children. """
        grandchilren: Set[SpanInfo] = set()
        for child in self.children:
            if any(SpanInfo.have_parent_link(ancestor=another_child, descendant=child)
                   for another_child in self.children - {child}):
                grandchilren.add(child)
        for grandchild in grandchilren:
            SpanInfo.unlink(parent=self, child=grandchild)

    def __lt__(self, other: "SpanInfo") -> bool:
        return self.span.__lt__(other.span)


EntityInfo = List[SpanInfo]


class DiffHandler():
    _instance: Optional["DiffHandler"] = None

    def __new__(cls, *args, **kwargs):
        if DiffHandler._instance is None:
            instance = super().__new__(cls, *args, **kwargs)
            instance.span2diff = defaultdict(set)
            DiffHandler._instance = instance
        return DiffHandler._instance

    def add(self, comment: str, *spans: Span, shared: bool = False):
        for span in spans:
            self.span2diff[span].add((comment, shared))

    def get_diff(self, markup: Markup) -> List[dict]:
        out = []
        spans = get_spans(markup)
        for span, comments in self.span2diff.items():
            if span in spans:
                regular_comments = sorted(comment for comment, shared in comments if not shared)
                shared_comments = sorted(comment for comment, shared in comments if shared)
                out.append({
                    "span": span,
                    "comments": regular_comments,
                    "shared_comments": shared_comments})
            else:
                logging.debug(f"DIFF: failed to write diff for «{markup.text[slice(*span)]}» {span}")
        return out


def build_entities(links: Set[Tuple[Span, Span]], singletons: Set[Span]) -> List[Entity]:
    span2entity = {}

    def get_entity(span: Span) -> Entity:
        if span not in span2entity:
            span2entity[span] = [span]
        return span2entity[span]

    for source, target in links:
        source_entity, target_entity = get_entity(source), get_entity(target)
        if source_entity is not target_entity:
            source_entity.extend(target_entity)
            for span in target_entity:
                span2entity[span] = source_entity

    ids = set()
    entities = []
    for entity in span2entity.values():
        if id(entity) not in ids:
            ids.add(id(entity))
            entities.append(entity)

    for span in singletons:
        if span not in span2entity:
            entities.append([span])

    return sorted(sorted(entity) for entity in entities)


def build_includes(entities: List[Entity], parent_links: Set[Tuple[Span, Span]]) -> List[List[int]]:
    span2entity_idx: Dict[Span, int] = {}
    for entity_idx, entity in enumerate(entities):
        for span in entity:
            span2entity_idx[span] = entity_idx
    includes: List[Set[int]] = [set() for _ in entities]
    for parent_span, child_span in parent_links:
        parent_entity_idx = span2entity_idx[parent_span]
        child_entity_idx = span2entity_idx[child_span]
        includes[parent_entity_idx].add(child_entity_idx)
    return [sorted(children) for children in includes]


def clean(markup: Markup):
    entities = [[SpanInfo(span) for span in entity] for entity in markup.entities]
    for parent_idx, children_list in enumerate(markup.includes):
        for child_idx in children_list:
            for parent_span in entities[parent_idx]:
                for child_span in entities[child_idx]:
                    SpanInfo.link(parent=parent_span, child=child_span)
    for entity in entities:
        for span in entity:
            span.unlink_redundant_children()

    entities = remove_singletons(entities, markup.text)
    entities = fix_overlapping_spans(entities, markup.text)
    entities = fix_discontinuous_spans(entities, markup.text)
    entities = strip_spans(entities, markup.text)
    entities = remove_empty_spans(entities)
    entities = deduplicate(entities, markup.text)
    entities = remove_singletons(entities, markup.text)
    entities = sorted(sorted(entity) for entity in entities)

    span2entity_idx: Dict[Span, int] = {}
    for entity_idx, entity in enumerate(entities):
        for span_info in entity:
            span2entity_idx[span_info.span] = entity_idx
    includes = []
    for entity in entities:
        children = set()
        for parent in entity:
            for child in parent.children:
                children.add(span2entity_idx[child.span])
        includes.append(sorted(children))

    markup.entities = [[span_info.span for span_info in entity] for entity in entities]
    markup.includes = includes


def countwhile(predicate: Callable[[Any], bool],
               iterable: Iterable[Any]
               ) -> int:
    """ Returns the number of times the predicate evaluates to True until
    it fails or the iterable is exhausted """
    return sum(takewhile(bool, map(predicate, iterable)))


def deduplicate(entities: Iterable[EntityInfo], text: str) -> Iterator[EntityInfo]:
    """ In case of conflict, keeps the spans from the entity with the most spans. """
    seen_spans = set()
    for entity in sorted(entities, key=lambda x: -len(x)):
        spans = []
        for span_info in entity:
            if span_info.span not in seen_spans:
                seen_spans.add(span_info.span)
                spans.append(span_info)
            else:
                logging.info(f"CLEAN: deleted duplicate span «{text[slice(*span_info.span)]}» {span_info.span}")
                DiffHandler().add("deleted duplicate span", span_info.span)
        yield spans


def fix_discontinuous_spans(entities: Iterable[EntityInfo], text: str) -> Iterator[EntityInfo]:
    """ Assumes that all the spans of the same entity are non-overlapping.
    [Jo][hn] -> [John]
    """
    for entity in entities:
        affected_starts: Dict[int, Set[SpanInfo]] = defaultdict(set)
        end2start: Dict[int, int] = {}
        end2info = {si.span[1]: si for si in entity}

        for span_info in sorted(entity, key=lambda x: x.span):
            start, end = span_info.span
            if start in end2start:  # span's start is another span's end
                fixed_start = end2start.pop(start)
                end2start[end] = fixed_start
                affected_starts[fixed_start].add(end2info[start])
                affected_starts[fixed_start].add(span_info)
            else:
                end2start[end] = start

        fixed_spans = []
        for end, start in end2start.items():
            if start in affected_starts:
                logging.info(f"CLEAN: fixed discontinuous span «{text[start:end]}» {(start, end)}")
                DiffHandler().add("fixed discontinuous span", (start, end))
                new_span = (start, end)
                parents = set()
                children = set()
                for span_info in affected_starts[start]:
                    parents.update(span_info.parents)
                    children.update(span_info.children)
                    span_info.unlink_all_parents_and_children()
                new_span_info = SpanInfo(new_span)
                for parent in parents:
                    SpanInfo.link(parent=parent, child=new_span_info)
                for child in children:
                    SpanInfo.link(parent=new_span_info, child=child)
                fixed_spans.append(new_span_info)
            else:
                fixed_spans.append(end2info[end])

        yield fixed_spans


def fix_overlapping_spans(entities: Iterable[EntityInfo], text: str) -> Iterator[EntityInfo]:
    for entity in entities:
        non_overlapping_spans: List[SpanInfo] = []
        spans = sorted(entity, key=lambda x: (x.span[0] - x.span[1], x.span))
        span_map = [False for _ in text]
        for span_info in spans:
            span = span_info.span
            if not any(span_map[slice(*span)]):
                for i in range(*span):
                    span_map[i] = True
                non_overlapping_spans.append(span_info)
            else:
                span_info.unlink_all_parents_and_children()
                logging.info(f"CLEAN: deleted overlapping span «{text[slice(*span)]}» {span}")
                preserved_span = next(si.span for si in non_overlapping_spans if si.span[0] <= span[0] < si.span[1])
                DiffHandler().add(f"deleted overlapping «{text[slice(*span)]}»", preserved_span)
        yield non_overlapping_spans


def get_entity_name(span: Span, markup: Markup, max_spans: int = 3) -> str:
    entity = next(entity for entity in markup.entities if span in entity)
    text_spans = []
    for span in entity:
        text_span = markup.text[slice(*span)]
        if text_span not in text_spans:
            text_spans.append(text_span)
            if len(text_spans) == max_spans:
                break
    return "//".join(["«{}»"] * len(text_spans)).format(*text_spans)


def get_links(markup: Markup) -> Set[Tuple[Span, Span]]:
    links: Set[Tuple[Span, Span]] = set()
    for entity in markup.entities:
        spans = sorted(entity)
        links.update(combinations(spans, 2))
    return links


def get_parent_links(markup: Markup) -> Set[Tuple[Span, Span]]:
    links = set()
    for parent_idx, children_list in enumerate(markup.includes):
        for child_idx in children_list:
            for parent_span in markup.entities[parent_idx]:
                for child_span in markup.entities[child_idx]:
                    links.add((parent_span, child_span))
    return links


def get_singletons(markup: Markup) -> Set[Span]:
    return {entity[0] for entity in markup.entities if len(entity) == 1}


def get_spans(markup: Markup) -> Set[Span]:
    return {span for entity in markup.entities for span in entity}


def merge(a: Markup, b: Markup) -> Markup:
    text = a.text
    a_spans, b_spans = get_spans(a), get_spans(b)
    common_spans = a_spans & b_spans

    for span in a_spans:
        if span not in common_spans:
            logging.info(f"MERGE: «{text[slice(*span)]}» {span} missing from B")
            DiffHandler().add("added span", span)
    for span in b_spans:
        if span not in common_spans:
            logging.info(f"MERGE: «{text[slice(*span)]}» {span} missing from A")
            DiffHandler().add("added span", span)

    a_links, b_links = get_links(a), get_links(b)
    common_links = a_links & b_links

    for link in a_links:
        if link not in common_links:
            source, target = link
            if source in common_spans and target in common_spans:
                logging.info(f"MERGE: «{text[slice(*source)]}» {source} + «{text[slice(*target)]}» {target} missing from B")
                DiffHandler().add(f"added link to {get_entity_name(target, a)}", source)
                DiffHandler().add(f"added link to {get_entity_name(source, a)}", target)
    for link in b_links:
        if link not in common_links:
            source, target = link
            if source in common_spans and target in common_spans:
                logging.info(f"MERGE: «{text[slice(*source)]}» {source} + «{text[slice(*target)]}» {target} missing from A")
                DiffHandler().add(f"added link to {get_entity_name(target, b)}", source)
                DiffHandler().add(f"added link to {get_entity_name(source, b)}", target)

    a_parent_links, b_parent_links = get_parent_links(a), get_parent_links(b)
    common_parent_links = a_parent_links & b_parent_links

    for link in a_parent_links:
        if link not in common_parent_links:
            source, target = link
            if source in common_spans and target in common_spans:
                logging.info(f"MERGE: «{text[slice(*source)]}» {source} > «{text[slice(*target)]}» {target} missing from B")
                DiffHandler().add(f"added child: {get_entity_name(target, a)}", source, shared=True)
                DiffHandler().add(f"added parent: {get_entity_name(source, a)}", target, shared=True)
    for link in b_parent_links:
        if link not in common_parent_links:
            source, target = link
            if source in common_spans and target in common_spans:
                logging.info(f"MERGE: «{text[slice(*source)]}» {source} > «{text[slice(*target)]}» {target} missing from A")
                DiffHandler().add(f"added child: {get_entity_name(target, b)}", source, shared=True)
                DiffHandler().add(f"added parent: {get_entity_name(source, b)}", target, shared=True)

    # These are spans that only have parent links, but not normal links
    a_singletons, b_singletons = get_singletons(a), get_singletons(b)

    merged_entities = build_entities(a_links | b_links, a_singletons | b_singletons)
    merged_includes = build_includes(merged_entities, a_parent_links | b_parent_links)
    return Markup(
        entities=merged_entities,
        includes=merged_includes,
        text=text
    )


def read_markup(path: str) -> Markup:
    with open(path, mode="r", encoding="utf8") as f:
        markup_dict = json.load(f)
    markup_dict["entities"] = [[tuple(span) for span in entity]
                               for entity in markup_dict["entities"]]
    return Markup(**markup_dict)


def remove_empty_spans(entities: Iterable[EntityInfo]) -> Iterator[EntityInfo]:
    for entity in entities:
        non_empty_spans = []
        for span_info in entity:
            start, end = span_info.span
            if start < end:
                non_empty_spans.append(span_info)
            else:
                span_info.unlink_all_parents_and_children()

        if len(non_empty_spans) != len(entity):
            logging.info(f"CLEAN: deleted {len(entity) - len(non_empty_spans)} empty spans")

        yield non_empty_spans


def remove_singletons(entities: List[EntityInfo], text: str) -> Iterator[EntityInfo]:
    for entity in entities:
        if len(entity) > 1 or any(span.has_parent_links() for span in entity):
            yield entity
        elif entity:
            logging.info(f"CLEAN: deleted singleton «{text[slice(*entity[0].span)]}» {entity[0].span}")
        else:
            logging.info("CLEAN: deleted empty entity")


def strip_spans(entities: Iterable[EntityInfo], text: str) -> Iterator[EntityInfo]:
    """ Can produce empty and duplicate spans """
    for entity in entities:
        for span_info in entity:
            start, end = span_info.span
            span_text = text[start:end]
            start_offset = countwhile(str.isspace, span_text)
            end_offset = countwhile(str.isspace, reversed(span_text))
            new_span = (start + start_offset, end - end_offset)
            span_info.span = new_span

            if (start, end) != new_span:
                logging.info(f"CLEAN: «{text[start:end]}» {(start, end)} -> «{text[slice(*new_span)]}» {new_span}")
                DiffHandler().add(f"stripped from «{text[start:end]}»", new_span)

        yield entity


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("a", help="Path to a markup file.")
    argparser.add_argument("b", help="Path to another markup file.")
    argparser.add_argument("--out", "-o", required=True,
                           help="Output file name/path.")
    argparser.add_argument("--debug", action="store_true",
                           help="Log debug messages.")
    args = argparser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, format="%(message)s")

    paths = (args.a, args.b)

    versions: List[Markup] = []
    for path in paths:
        versions.append(read_markup(path))

    if versions[0].text != versions[1].text:
        print("Texts are not the same!")
        sys.exit(1)

    for version, path in zip(versions, paths):
        logging.info(f"Cleaning {path}")
        clean(version)

    logging.info("Merging")
    merged = merge(*versions)
    clean(merged)

    out = asdict(merged)
    diff = DiffHandler().get_diff(merged)
    if diff:
        out["diff"] = diff

    with open(args.out, mode="w", encoding="utf8") as f:
        json.dump(out, f, ensure_ascii=False)
