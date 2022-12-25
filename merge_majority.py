import argparse
from dataclasses import asdict
import json
import logging
import sys
from typing import List, Set, Tuple

import merge


def merge_majority(versions: List[merge.Markup]) -> merge.Markup:
    assert len(versions) > 2
    text = versions[0].text
    threshold = len(versions) / 2

    spans_by_version = [merge.get_spans(version) for version in versions]
    unique_spans = set()
    for spans in spans_by_version:
        unique_spans.update(spans)
    result_spans: Set[merge.Span] = set()
    for span in unique_spans:
        occurences = sum(span in spans for spans in spans_by_version)
        if occurences >= threshold:
            result_spans.add(span)
    logging.info(f"MERGE_MAJORITY: kept {len(result_spans)}/{len(unique_spans)} spans")

    links_by_version = [merge.get_links(version) for version in versions]
    unique_links = set()
    for links in links_by_version:
        unique_links.update(links)
    result_links: Set[Tuple[merge.Span, merge.Span]] = set()
    for link in unique_links:
        source, target = link
        if source in result_spans and target in result_spans:
            occurences = sum(link in links for links in links_by_version)
            if occurences >= threshold:
                result_links.add(link)
    logging.info(f"MERGE_MAJORITY: kept {len(result_links)}/{len(unique_links)} links")

    parent_links_by_version = [merge.get_parent_links(version) for version in versions]
    unique_parent_links = set()
    for parent_links in parent_links_by_version:
        unique_parent_links.update(parent_links)
    result_parent_links: Set[Tuple[merge.Span, merge.Span]] = set()
    for parent_link in unique_parent_links:
        source, target = parent_link
        if source in result_spans and target in result_spans:
            occurences = sum(parent_link in parent_links for parent_links in parent_links_by_version)
            if occurences >= threshold:
                result_parent_links.add(parent_link)
    logging.info(f"MERGE_MAJORITY: kept {len(result_parent_links)}/{len(unique_parent_links)} parent links")

    singletons = {span for plink in result_parent_links for span in plink}
    for span in {span for link in result_links for span in link}:
        singletons.discard(span)

    entities = merge.build_entities(result_links, singletons)
    includes = merge.build_includes(entities, result_parent_links)
    return merge.Markup(
        entities=entities,
        includes=includes,
        text=text
    )


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("paths", nargs=3, help="Paths to markup versions")
    argparser.add_argument("--out", "-o", required=True,
                           help="Output file name/path.")
    argparser.add_argument("--debug", action="store_true",
                           help="Log debug messages.")
    args = argparser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, format="%(message)s")

    versions: List[merge.Markup] = []
    for path in args.paths:
        versions.append(merge.read_markup(path))

    if any(version.text != versions[0].text for version in versions[1:]):
        print("Texts are not the same!")
        sys.exit(1)

    for version, path in zip(versions, args.paths):
        logging.info(f"Cleaning {path}")
        merge.clean(version)

    logging.info("Merging")
    merged = merge_majority(versions)
    merge.clean(merged)

    out = asdict(merged)

    with open(args.out, mode="w", encoding="utf8") as f:
        json.dump(out, f, ensure_ascii=False)
