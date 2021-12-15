import argparse
import os
from typing import *

from diff import f1, get_children, _lea_children, read_markup_dict


EPS = 1e-7


def get_relative_paths(path: str) -> Iterator[str]:
    return map(lambda entry: os.path.relpath(entry.path, path),
               filter(lambda entry: entry.name.endswith(".json"),
                      recursive_scandir(path)))


def recursive_scandir(path: str) -> Iterator[os.DirEntry]:
    for entry in os.scandir(path):
        if entry.is_dir():
            yield from recursive_scandir(entry.path)
        else:
            yield entry


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("a", help="Directory with one set of markups")
    argparser.add_argument("b", help="Directory with another set of markups")
    args = argparser.parse_args()

    a_files = set(get_relative_paths(args.a))
    b_files = set(get_relative_paths(args.b))
    common_files = a_files & b_files

    for file in a_files - common_files:
        print(f"Skipping {os.path.join(args.a, file)}")
    for file in b_files - common_files:
        print(f"Skipping {os.path.join(args.b, file)}")

    print()
    total_recall, total_r_weight = .0, .0
    total_precision, total_p_weight = .0, .0
    for file in sorted(common_files):
        a = read_markup_dict(os.path.join(args.a, file))
        b = read_markup_dict(os.path.join(args.b, file))
        assert a["text"] == b["text"]

        a_clusters = [(spans, get_children(a, i))
                      for i, spans in enumerate(a["entities"])]
        b_clusters = [(spans, get_children(b, i))
                      for i, spans in enumerate(b["entities"])]

        recall, r_weight = _lea_children(a_clusters, b_clusters)
        precision, p_weight = _lea_children(b_clusters, a_clusters)

        doc_recall = recall / (r_weight + EPS)
        doc_precision = precision / (p_weight + EPS)
        print(f"{f1(doc_recall, doc_precision):.3f} {file}")

        total_recall += recall
        total_r_weight += r_weight
        total_precision += precision
        total_p_weight += p_weight

    recall = total_recall / (total_r_weight + EPS)
    precision = total_precision / (total_p_weight + EPS)
    print(f"\n{f1(recall, precision):.3f} Total")
