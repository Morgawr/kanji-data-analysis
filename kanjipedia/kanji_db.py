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
        self._db.table("kanji").upsert(data, self._kq.kanji == data["kanji"])

    def AddOrUpdateKunEntry(self, kun, kanji_list):
        """Given a kunyomi and list of kanji, adds them to the database."""
        self._db.table("kunyomi").upsert({
            "kun": kun,
            "kanji": kanji_list,
        }, self._kq.kun == kun)

    def Remove(self, entry):
        """Given a kanji entry, removes it from the database."""
        self._db.table("kanji").remove(where("kanji") == entry.kanji)

    def Search(self, table, query):
        results = []
        for data in self._db.table(table).search(query):
            if table == "kanji":
                results.append(KanjiEntry.FromJSON(data))
            else:
                results.append(data)
        return results

    def GetKanji(self, kanji):
        """Given a kanji name, finds the relevant entry (if any)."""
        return self.Search("kanji", self._kq.kanji == kanji)[0]

    def GetAllKanji(self):
        """Returns a list of all kanji (just the kanji, not entity)."""
        return [KanjiEntry.FromJSON(x).kanji
                for x in self._db.table("kanji").all()]

    def FindKunyomi(self, *readings):
        """Given a list of kunyomi, finds all kanji that match all (if any).

        Args:
            *readings: list of str, all readings to test and find.

        Returns:
            A list of kanji Entities (not individual moji).
        """
        return self.Search("kanji", self._kq.kunyomi.all(readings))

    def FindSingleKunyomi(self, reading, fast=True):
        """Given a single kunyomi reading, get list of kanji (if any).

        Args:
            reading: str, the kunyomi reading.
            fast: bool, if true, hits the cached pre-built database.

        Returns:
            List of individual moji (not Entries).
        """
        if fast:
            result = self.Search("kunyomi", self._kq.kun == reading)
            if result:
                return result[0]["kanji"]
            return []
        else:
            return [k.kanji for k in self.FindKunyomi(reading)]

    def GetAllKunyomi(self):
        """Returns entire kunyomi map from pre-built cache.

        Returns:
            A dictionary of kun readings (str key) + list of kanji (not Entries)
            that have the given reading.
        """
        result = self.Search("kunyomi", self._kq.kun != "")
        kun_map = {}
        for kun in result:
            kun_map[kun["kun"]] = kun["kanji"]
        return kun_map


    def FindKanjiWithSharedPhonetic(self, kanji):
        """Given an initial kanji, finds all kanji that share 音符 with it."""
        kanji = self.GetKanji(kanji)
        if not kanji.phonetic_comp:
            return []
        else:
            return self.Search("kanji",
                               self._kq.phonetic_comp == kanji.phonetic_comp)

    def FindKanjiWithSharedSemantic(self, kanji):
        """Given an initial kanji, finds all kanji that share 意符 with it."""
        kanji = self.GetKanji(kanji)
        if not kanji.semantic_comp:
            return []
        else:
            results = {}
            for sem in kanji.semantic_comp:
                results[sem] = self.Search("kanji",
                                           self._kq.semantic_comp.any(sem))
            return results

    def FindOnyomi(self, *readings):
        """Given a list of onyomi, finds all kanji that match all (if any)."""
        return self.Search("kanji", self._kq.onyomi.all(readings))

    def SearchTypes(self, *types):
        return self.Search("kanji", self._kq.types.any(types))

    def SearchExactTypes(self, *types):
        return self.Search("kanji", self._kq.types.all(types))

    def Stats(self):
        """Prints statistics."""
        total = len(self._db.table("kanji"))
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
