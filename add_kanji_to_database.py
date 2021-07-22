"""Python module that adds a given kanji to the given tinydb database."""

import argparse
import sys
import time
import traceback

from kanjipedia.entry import Entry as KanjiEntry
from kanjipedia.kanji_db import KanjiDB


def main():
    parser = argparse.ArgumentParser(
            description="Extract kanji data from kanjipedia.")
    parser.add_argument("database", type=str, metavar="database",
                        help="Database file where kanji data is stored")
    parser.add_argument("url_file", type=str, metavar="url_file",
                        help=("File containing a list of kanjipedia URLs for "
                              "each kanji + the relevant kanji on each line"))
    args = parser.parse_args()
    db = KanjiDB(args.database)
    first_start = time.time()

    with open(args.url_file) as f:
        kanji_list = f.read().splitlines()
    print(f"Getting ready to load {len(kanji_list)} kanji.")
    current = 0
    for kanji in kanji_list:
        try:
            url, k = kanji.split(" ")
            print(f"Loading kanji {k} from {url}")
            start = time.time()
            entry = KanjiEntry.FromURL(url)
            db.AddOrUpdate(entry)
            current += 1
            end = time.time()
            elapsed = int((end - start) * 1000)
            elapsed_all = int((end - first_start) * 1000)
            print(f"Done! Time: f{elapsed}ms (Total: f{elapsed_all}ms)")
            print(f"Loaded {current} out of {len(kanji_list)} kanji...")
        except KeyboardInterrupt:
            sys.exit(1)
        except:
            print(f"Error at line: {current + 1} - {kanji}", file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)


if __name__ == "__main__":
    main()
