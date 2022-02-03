import argparse
from itertools import combinations, takewhile
import json
import logging
from typing import *
import sys


Span = Tuple[int, int]
Entity = List[Span]


def build_entities(links: Set[Tuple[Span, Span]]) -> List[Entity]:
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

    return sorted(sorted(entity) for entity in entities)


def get_links(markup: dict) -> Set[Tuple[Span, Span]]:
    links = set()
    for entity in markup["entities"]:
        spans = sorted(entity)
        links.update(combinations(spans, 2))
    return links


def get_spans(markup: dict) -> Set[Span]:
    return {span for entity in markup["entities"] for span in entity}


def merge(a: dict, b: dict) -> dict:
    text = a["text"]
    a_spans, b_spans = get_spans(a), get_spans(b)
    common_spans = a_spans & b_spans

    for span in a_spans:
        if span not in common_spans:
            logging.info(f"MERGE: «{text[slice(*span)]}» {span} missing from B")
    for span in b_spans:
        if span not in common_spans:
            logging.info(f"MERGE: «{text[slice(*span)]}» {span} missing from A")

    a_links, b_links = get_links(a), get_links(b)
    common_links = a_links & b_links

    for link in a_links:
        if link not in common_links:
            source, target = link
            if source in common_spans and target in common_spans:
                logging.info(f"MERGE: «{text[slice(*source)]}» + «{text[slice(*target)]}» missing from B")
    for link in b_links:
        if link not in common_links:
            source, target = link
            if source in common_spans and target in common_spans:
                logging.info(f"MERGE: «{text[slice(*source)]}» + «{text[slice(*target)]}» missing from A")

    merged_entities = build_entities(a_links | b_links)
    return {
        "entities": merged_entities,
        "includes": [[] for _ in merged_entities],
        "text": text
    }

# Cleaning functions ==========================================================


def clean(entities: Iterable[Entity], text: str) -> Iterator[Entity]:
    entities = remove_singletons(entities, text)
    entities = fix_overlapping_spans(entities, text)
    entities = fix_discontinuous_spans(entities, text)
    entities = strip_spans(entities, text)
    entities = remove_empty_spans(entities)
    entities = deduplicate(entities, text)
    entities = remove_singletons(entities, text)
    return entities


def deduplicate(entities: Iterable[Entity], text: str) -> Iterator[Entity]:
    seen_spans = set()
    for entity in entities:
        spans = []
        for span in entity:
            if span not in seen_spans:
                seen_spans.add(span)
                spans.append(span)
            else:
                logging.info(f"CLEAN: deleted duplicate span «{text[slice(*span)]}»")
        yield spans


def fix_discontinuous_spans(entities: Iterable[Entity], text: str) -> Iterator[Entity]:
    """ Assumes that all the spans of the same entity are non-overlapping.
    [Jo][hn] -> [John]
    """
    for entity in entities:
        affected_starts = set()
        end2start = {}

        for start, end in sorted(entity):
            if start in end2start:  # span's start is another span's end
                fixed_start = end2start.pop(start)
                end2start[end] = fixed_start
                affected_starts.add(fixed_start)
            else:
                end2start[end] = start

        fixed_spans = []
        for end, start in end2start.items():
            if start in affected_starts:
                logging.info(f"CLEAN: fixed discontinuous span «{text[start:end]}»")
            fixed_spans.append((start, end))

        yield sorted(fixed_spans)


def fix_overlapping_spans(entities: Iterable[Entity], text: str) -> Iterator[Entity]:
    for entity in entities:
        non_overlapping_spans = []
        spans = sorted(entity, key=lambda span: (span[0] - span[1], span))
        span_map = [False for _ in text]
        for span in spans:
            if not any(span_map[slice(*span)]):
                for i in range(*span):
                    span_map[i] = True
                non_overlapping_spans.append(span)
            else:
                logging.info(f"CLEAN: deleted overlapping span «{text[slice(*span)]}»")
        yield non_overlapping_spans


def remove_empty_spans(entities: Iterable[Entity]) -> Iterator[Entity]:
    for entity in entities:
        non_empty_spans = [(start, end) for start, end in entity if start < end]

        if len(non_empty_spans) != len(entity):
            logging.info(f"CLEAN: deleted {len(entity) - len(non_empty_spans)} empty spans")

        yield non_empty_spans


def remove_singletons(entities: Iterable[Entity], text: str) -> Iterator[Entity]:
    for entity in entities:
        if len(entity) > 1:
            yield entity
        elif entity:
            logging.info(f"CLEAN: deleted singleton «{text[slice(*entity[0])]}»")
        else:
            logging.info(f"CLEAN: deleted empty entity")


def strip_spans(entities: Iterable[Entity], text: str) -> Iterator[Entity]:
    """ Can produce empty and duplicate spans """
    for entity in entities:
        spans = []
        for start, end in entity:
            span_text = text[start:end]
            start_offset = countwhile(str.isspace, span_text)
            end_offset = countwhile(str.isspace, reversed(span_text))
            new_span = (start + start_offset, end - end_offset)
            spans.append(new_span)

            if (start, end) != new_span:
                logging.info(f"CLEAN: «{text[start:end]}» -> «{text[slice(*new_span)]}»")

        yield spans


# Utility functions ===========================================================


def countwhile(predicate: Callable[[Any], bool],
                iterable: Iterable[Any]
                ) -> int:
    """ Returns the number of times the predicate evaluates to True until
    it fails or the iterable is exhausted """
    return sum(takewhile(bool, map(predicate, iterable)))


def read_markup_dict(path: str) -> dict:
    with open(path, mode="r", encoding="utf8") as f:
        markup_dict = json.load(f)
    markup_dict["entities"] = [[tuple(span) for span in entity]
                               for entity in markup_dict["entities"]]
    return markup_dict


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    argparser = argparse.ArgumentParser()
    argparser.add_argument("a", help="Path to a markup file.")
    argparser.add_argument("b", help="Path to another markup file.")
    argparser.add_argument("--out", "-o", required=True,
                           help="Output file name/path.")
    args = argparser.parse_args()

    paths = (args.a, args.b)

    versions = []
    for path in paths:
        versions.append(read_markup_dict(path))

    if versions[0]["text"] != versions[1]["text"]:
        print("Texts are not the same!")
        sys.exit(1)

    for version, path in zip(versions, paths):
        logging.info(f"Cleaning {path}")
        version["entities"] = list(clean(version["entities"], version["text"])) # does not consider child/parent
                                                                                # relations yet. Can break child/parent
                                                                                # data while removing singletons
                                                                                # (which can be valid parents)
        logging.warning(f"Removing child/parent relations from {path}")
        version["includes"] = [[] for _ in version["entities"]]

    logging.info("Merging")
    merged = merge(*versions)
    merged["entities"] = list(clean(merged["entities"], merged["text"]))        # in case new overlapping spans were
                                                                                # introduced while merging
    with open(args.out, mode="w", encoding="utf8") as f:
        json.dump(merged, f, ensure_ascii=False)
