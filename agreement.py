import argparse
from collections import defaultdict
import os
import sys
from typing import *

from diff import f1, get_children, _lea_children, read_markup_dict


EPS = 1e-7


class DocumentPair(NamedTuple):
    filename: str
    dir_a: str
    dir_b: str


def agreement(pairs: Iterable[DocumentPair]):
    total_recall, total_r_weight = .0, .0
    total_precision, total_p_weight = .0, .0
    for pair in sorted(pairs):
        a = read_markup_dict(os.path.join(pair.dir_a, pair.filename))
        b = read_markup_dict(os.path.join(pair.dir_b, pair.filename))
        assert a["text"] == b["text"]

        a_clusters = [(spans, get_children(a, i))
                      for i, spans in enumerate(a["entities"])]
        b_clusters = [(spans, get_children(b, i))
                      for i, spans in enumerate(b["entities"])]

        recall, r_weight = _lea_children(a_clusters, b_clusters)
        precision, p_weight = _lea_children(b_clusters, a_clusters)

        doc_recall = recall / (r_weight + EPS)
        doc_precision = precision / (p_weight + EPS)
        print(f"{f1(doc_recall, doc_precision):.3f} {pair.filename}")

        total_recall += recall
        total_r_weight += r_weight
        total_precision += precision
        total_p_weight += p_weight

    recall = total_recall / (total_r_weight + EPS)
    precision = total_precision / (total_p_weight + EPS)
    print(f"\n{f1(recall, precision):.3f} Total")


def get_pairs_from_dir(path: str) -> List[DocumentPair]:
    entries = filter(lambda entry: entry.name.endswith(".json"),
                     recursive_scandir(path))
    name2paths = defaultdict(list)
    for entry in entries:
        name2paths[entry.name].append(entry.path)

    pairs = []
    for name, paths in name2paths.items():
        if len(paths) == 1:
            print(f"No matching document for {paths[0]}")
        elif len(paths) > 2:
            print(f"Too many matching documents: {', '.join(paths)}")
        else:
            pairs.append(
                DocumentPair(name, *(os.path.dirname(path) for path in paths))
            )
    print()
    return pairs


def get_pairs_from_two_dirs(a: str,
                            b: str) -> List[DocumentPair]:
    a_files = set(get_relative_paths(a))
    b_files = set(get_relative_paths(b))
    common_files = a_files & b_files

    for file in a_files - common_files:
        print(f"No matching document for {os.path.join(a, file)}")
    for file in b_files - common_files:
        print(f"No matching document for {os.path.join(b, file)}")

    print()
    return [DocumentPair(filename, a, b) for filename in common_files]


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
    argparser.add_argument("src", nargs="+",
                           help="Directory or directories (max 2)"
                                " with documents to compare.")
    args = argparser.parse_args()

    if len(args.src) == 1:
        pairs = get_pairs_from_dir(*args.src)
    elif len(args.src) == 2:
        pairs = get_pairs_from_two_dirs(*args.src)
    else:
        print("The number of command-line arguments cannot exceed two.",
              file=sys.stderr)
        sys.exit(1)
    agreement(pairs)
