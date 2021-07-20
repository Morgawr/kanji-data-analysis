"""Python script to generate a kanji map webpage."""

import argparse
import sys

from bs4 import BeautifulSoup

from kanjipedia.entry import Entry as KanjiEntry
from kanjipedia.kanji_db import KanjiDB


def main():
    parser = argparse.ArgumentParser(
            description="Generates a kanji map webpage.")
    parser.add_argument("database", type=str, metavar="database",
                        help="Database file where kanji data is stored")
    parser.add_argument("output_dir", type=str, metavar="output_dir",
                        help="Directory path where to save build artifacts.")
    args = parser.parse_args()
    db = KanjiDB(args.database)

    output = "<html>"
    output += "<head>"
    output += "<title>Morg's POGGERS kanji list</title>"
    output += "<style> table, th, td { padding: 10px; border: 1px solid black; border-collapse: collapse; } </style>"
    output += "<meta charset='utf-8'/>"
    output += "</head>"
    # TODO(morg): Add proper CSS lmao
    output += "<body>"
    for k in db.GetAllKanji():
        output += db.GetKanji(k).GenerateHTML()
        output += '<hr />'
    output += "</body>"
    output += "</html>"
    soup = BeautifulSoup(output, "html.parser")
    # TODO(morg): use os.path :/
    with open(args.output_dir + "/index.html", "w") as f:
        f.write(soup.prettify())

if __name__ == "__main__":
    main()
