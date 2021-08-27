"""Python script to generates various json data for graph web visualizers."""

import argparse
import enum
import json
import sys

from kanjipedia.entry import Entry as KanjiEntry
from kanjipedia.kanji_db import KanjiDB


class GraphType(enum.Enum):
    KUNMAP = 'kunmap'

    def __str__(self):
        return self.value


def build_kunmap(db, output_dir):
    kun_map = [
            {"kun": kun, "kanji": kanji}
            for kun, kanji in db.GetAllKunyomi().items()]
    with open(output_dir + "/kun_map.json", "w") as outfile:
        json.dump(kun_map, outfile, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(
            description="Generates a given json data for graph visualization.")
    parser.add_argument("database", type=str, metavar="database",
                        help="Database file where kanji data is stored")
    parser.add_argument("output_dir", type=str, metavar="output_dir",
                        help="Directory path where to save build artifacts.")
    parser.add_argument("graph_type", type=GraphType, choices=list(GraphType),

                        help="Type of graph data you want to generate.")
    args = parser.parse_args()

    db = KanjiDB(args.database)
    if(args.graph_type == GraphType.KUNMAP):
        build_kunmap(db, args.output_dir)


if __name__ == "__main__":
    main()
