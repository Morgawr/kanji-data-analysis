"""Python module that adds a given kanji to the given tinydb database."""

import argparse
import sys

from tinydb import TinyDB, Query

from kanjipedia.entry import Entry as KanjiEntry


def main():
    parser = argparse.ArgumentParser(description="Extract kanji data from kanjipedia.")
    parser.add_argument("database", type=str, metavar="database",
                        help="Database file where kanji data is stored")
    parser.add_argument("url", type=str, metavar="url",
                        help="The kanjipedia kanji url.")
    args = parser.parse_args()
    database = args.database
    entry = KanjiEntry.FromURL(args.url)
    print("Kanji: " + entry.kanji)
    print("Onyomi: " + str(entry.onyomi))
    print("Kunyomi: " + str(entry.kunyomi))
    print("Kanji old forms: " + str(entry.old_form))
    print("Type: " + str(entry.types))
    print("Radical: " + entry.radical)
    print("Phonetic component: " + str(entry.phonetic_comp))
    print("Semantic component: " + str(entry.semantic_comp))

if __name__ == "__main__":
    main()
