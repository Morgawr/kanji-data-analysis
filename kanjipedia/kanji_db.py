"""Module to store and query kanji in a tinyDB database."""

from tinydb import TinyDB, Query, where

from .entry import Entry as KanjiEntry
from .entry import KanjiType


class KanjiDB:

    def __init__(self, database):
        self._db = TinyDB(database)
        self._kq = Query()

    def AddOrUpdate(self, entry):
        """Given a kanji entry, adds or updates it in the database."""
        data = entry.GetDataDict()
        self._db.upsert(data, self._kq.kanji == data["kanji"])

    def Remove(self, entry):
        """Given a kanji entry, removes it from the database."""
        self._db.remove(where("kanji") == entry.kanji)

    def Search(self, query):
        results = []
        for kanji in self._db.search(query):
            results.append(KanjiEntry.FromJSON(kanji))
        return results

    def SearchTypes(self, *types):
        return self.Search(self._kq.types.any(types))

    def SearchExactTypes(self, *types):
        return self.Search(self._kq.types.all(types))

    def Stats(self):
        """Prints statistics."""
        total = len(self._db)
        print(f"Number of entries: {total}")
        shoukei = len(self.SearchTypes(KanjiType.SHOUKEI))
        shiji = len(self.SearchTypes(KanjiType.SHIJI))
        kaii = len(self.SearchTypes(KanjiType.KAII))
        keisei = len(self.SearchTypes(KanjiType.KEISEI))
        kaiikeisei = len(self.SearchExactTypes(KanjiType.KEISEI,
                                               KanjiType.KAII))
        def _percent(num1, num2):
            return float(int(100 * (100 * float(num1) / float(num2)))) / 100.0
        print(f"    象形: {shoukei} ({_percent(shoukei, total)}%)")
        print(f"    指事: {shiji} ({_percent(shiji, total)}%)")
        print(f"    会意: {kaii} ({_percent(kaii, total)}%)")
        print(f"    形声: {keisei} ({_percent(keisei, total)}%)")
        print(f"    会意形声: {kaiikeisei} ({_percent(kaiikeisei, total)}%)")
