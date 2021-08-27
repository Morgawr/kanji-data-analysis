"""Python module that builds the kunyomi map to the given tinydb database."""

import argparse
import sys
import time
import traceback

from tinydb import TinyDB, Query

from kanjipedia.entry import Entry as KanjiEntry
from kanjipedia.kanji_db import KanjiDB


def _get_elapsed(start, end):
    return int((end - start) * 1000)

def main():
    parser = argparse.ArgumentParser(
            description=("Given an already populated kanji db, builds a"
                         "kunyomi relationship map."))
    parser.add_argument("database", type=str, metavar="database",
                        help="Database file where kanji data is stored")
    args = parser.parse_args()
    db = KanjiDB(args.database)
    first_start = time.time()

    print("Retrieving kunyomi data...")
    start = time.time()
    # Build total kunyomi set:
    kunyomi = set()
    for kanji in db.GetAllKanji():
        kunyomi.update(db.GetKanji(kanji).kunyomi_all)
    print(f"Done. (Elapsed:{_get_elapsed(start, time.time())}ms)")

    print("Retrieving kanji data for each kunyomi...")
    start = time.time()
    kun_kanji_map = {}
    for k in kunyomi:
        kun_kanji_map[k] = (set(), set()) # non-ext and ext kanji
        for entry in db.FindKunyomi(k):
            if k in entry.kunyomi_ext:
                kun_kanji_map[k][1].add(entry.kanji)
            elif k in entry.kunyomi:
                kun_kanji_map[k][0].add(entry.kanji)
            else:
                print(f"WARNING: inconsistent value for {k} on {entry.kanji}")
    print(f"Done. (Elapsed:{_get_elapsed(start, time.time())}ms)")

    print("Populating database with new kunyomi data...")
    start = time.time()
    for k, v in kun_kanji_map.items():
        db.AddOrUpdateKunEntry(k, list(v[0]), list(v[1]))
    print(f"Done. (Elapsed:{_get_elapsed(start, time.time())}ms)")
    print(f"All Done! Total time: {_get_elapsed(first_start, time.time())}ms")

if __name__ == "__main__":
    main()
