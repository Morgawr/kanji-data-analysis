"""Module to store and query kanji in a tinyDB database."""

from tinydb import TinyDB, Query, where

from .entry import Entry as KanjiEntry


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
