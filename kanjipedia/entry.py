"""Module to handle individual kanjipedia entry data."""
import enum
import re
import requests
import sys

from bs4 import BeautifulSoup

_KANJIPEDIA_URL = "https://www.kanjipedia.jp"

_KP_OYAJI = "kanjiOyaji"
_KP_EXP_AREA = "kanjiExplanationArea"
_KP_ONKUN_YOMI = "onkunYomi"
_KP_RIGHT_SECTION = "kanjiRightSection"
_KP_BUSHU = "kanjiBushu"
_KP_NARITACHI = "naritachi"
_KP_KYUUJI = "旧字"
_KP_SUB_KANJI = "subKanji"
_KP_SAME_BUSHU = "sameBushuList"


class KanjiType(str, enum.Enum):
    SHIJI = enum.auto()
    SHOUKEI = enum.auto()
    KAII = enum.auto()
    KEISEI = enum.auto()
    TENCHUU = enum.auto()
    KASHA = enum.auto()

    @staticmethod
    def GetKanjiTypes(text):
        "Parses a given snippet of text and returns all types that get a hit."
        types = set()
        namemap = {
            KanjiType.SHIJI: "指事",
            KanjiType.SHOUKEI: "象形",
            KanjiType.KAII: "会意",
            KanjiType.KEISEI: "形声",
            KanjiType.TENCHUU: "転注",
            KanjiType.KASHA: "仮借",
        }
        for k,v in namemap.items():
            if v in text:
                types.add(k)
        return types


class Entry:

    def __init__(self):
        # TODO(morg): maybe also add meaning field
        self.origin_url = None
        self.kanji = None
        self.old_form = set() # Some kanji can have multiple old forms? wtf
        self.radical = None
        self.semantic_comp = set()
        self.phonetic_comp = None
        self.types = set()
        #self.raw_text = ""
        self.related_kanji = set()
        self.onyomi = set()
        self.kunyomi = set()

    @staticmethod
    def FromURL(url):
        url = url if _KANJIPEDIA_URL in url else _KANJIPEDIA_URL + url
        entry = Entry()
        entry.origin_url = url.strip()
        # Load HTML data into the entry
        raw_text = requests.get(entry.origin_url).text
        entry._parse_HTML(raw_text)
        return entry

    @staticmethod
    def FromJSON(data):
        entry = Entry()
        entry.origin_url = data["origin_url"]
        entry.kanji = data["kanji"]
        entry.old_form = set(data["old_form"])
        entry.radical = data["radical"]
        entry.semantic_comp = set(data["semantic_comp"])
        entry.phonetic_comp = data["phonetic_comp"]
        entry.types = set([KanjiType(s) for s in data["types"]])
        #entry.raw_text = data["raw_text"]
        entry.related_kanji = set(data["related_kanji"])
        entry.onyomi = set(data["onyomi"])
        entry.kunyomi = set(data["kunyomi"])
        return entry

    def _parse_components(self, naritachi_tag):
        # Remove text in parentheses cause it doesn't help and breaks our
        # parsing code
        naritachi = re.sub(r"(（[^()]*）|\([^()]*\))", "",
                           str(naritachi_tag).split("<br/>")[-1])
        self.types = KanjiType.GetKanjiTypes(naritachi)

        # Some kanji just won't want to cooperate, so we hardcode them
        if self._handle_special_entries():
            return

        if KanjiType.KEISEI in self.types:
            naritachi_ifu = ""
            # Check if the semantic component is parsable
            if naritachi.find("意符") != -1:
                naritachi_ifu = naritachi[naritachi.find("意符") + 2]
            else:
                naritachi_ifu = naritachi[naritachi.find("と") - 1]
            parsable = True
            if naritachi_ifu != ">" and naritachi_ifu != "<":
                self.semantic_comp.add(naritachi_ifu)
            else:
                self.semantic_comp.add(str(naritachi_tag.contents[1]))
                parsable = False
            # Check if the phonetic component is parsable
            naritachi_onpu = naritachi[naritachi.find("音符") + 2]
            # Check if the kanji is 会意形声
            if KanjiType.KAII in self.types:
                # Skip 、 and go to the real 音符 that is also secondary 意符
                naritachi_onpu = naritachi[naritachi.find("と") + 2]
            if naritachi_onpu != "<":
                self.phonetic_comp = naritachi_onpu
                self.semantic_comp.add(naritachi_onpu)
            else:
                # If semantic component was an image, then we need to skip one
                # image ahead :/
                self.phonetic_comp = str(
                        naritachi_tag.contents[1 if parsable else 2])
                self.semantic_comp.add(str(
                    naritachi_tag.contents[1 if parsable else 2]))
        # If it's a 会意 but not a 会意形声
        elif KanjiType.KAII in self.types:
            naritachi_ifu = ""
            # Check if the semantic component is parsable
            naritachi_ifu = naritachi[naritachi.find("と") - 1]
            parsable = True
            if naritachi_ifu != ">" and naritachi_ifu != "<":
                self.semantic_comp.add(naritachi_ifu)
            else:
                self.semantic_comp.add(str(naritachi_tag.contents[1]))
                parsable = False
            naritachi_ifu = naritachi[naritachi.find("と") + 2]
            if naritachi_ifu != ">" and naritachi_ifu != "<":
                self.semantic_comp.add(naritachi_ifu)
            else:
                self.semantic_comp.add(str(
                    naritachi_tag.contents[1 if parsable else 2]))

    def _parse_readings(self, list_tag):
        for on in re.sub(r"・", " ", list_tag[0].text).split(" "):
            self.onyomi.add(str(on).strip())
        for kun in re.sub(r"・", " ", list_tag[1].text).split(" "):
            self.kunyomi.add(str(kun).strip())

    def _handle_special_entries(self):
        if self.kanji == "比":
            self.semantic_comp.add("人")
        elif self.kanji == "会":
            self.semantic_comp.add("曾")
            self.semantic_comp.add(
                "<img src=\"/common/images/naritachi/500064.png\">")
        elif self.kanji == "炎":
            self.semantic_comp.add("火")
        elif self.kanji == "並":
            self.semantic_comp.add("立")
        elif self.kanji == "歩":
            self.semantic_comp.add("止")
        elif self.kanji == "門":
            self.semantic_comp.add("戸")
        elif self.kanji == "林":
            self.semantic_comp.add("木")
        elif self.kanji == "乗":
            self.semantic_comp.add("木")
            self.semantic_comp.add("人")
        elif self.kanji == "侵":
            self.semantic_comp.add("人")
            self.semantic_comp.add("帚")
            self.semantic_comp.add("又")
        elif self.kanji == "品":
            self.semantic_comp.add("口")
        elif self.kanji == "保":
            self.semantic_comp.add("人")
            self.semantic_comp.add(
                "<img src=\"/common/images/naritachi/500065.png\">")
        elif self.kanji == "要":
            pass
        elif self.kanji == "森":
            self.semantic_comp.add("木")
        elif self.kanji == "慨":
            self.semantic_comp.add("心")
            self.phonetic_comp = \
                "<img src=\"/common/images/naritachi/2293.png\">"
        elif self.kanji == "継":
            self.semantic_comp.add("糸")
            self.phonetic_comp = \
                "<img src=\"/common/images/naritachi/2565.png\">"
        elif self.kanji == "憬":
            self.semantic_comp.add("心")
            self.phonetic_comp = "景"
        elif self.kanji == "錮":
            self.semantic_comp.add("金")
            self.phonetic_comp = "固"
        else:
            return False
        return True

    def _parse_related_kanji(self, bushu_list):
        for i in bushu_list.text.replace("\n", ""):
            if i == self.kanji:
                pass
            self.related_kanji.add(i)

    def _parse_HTML(self, raw_text):
        soup = BeautifulSoup(raw_text, "html.parser")
        # Save the kanji value
        self.kanji = soup.find("p", {"id": _KP_OYAJI}).text
        # And its old form (if any)
        try:
            for old_form in soup.find_all("p", {"class": _KP_SUB_KANJI}):
                if str(old_form.text) != self.kanji:
                    self.old_form.add(str(old_form.contents[0]))
        except AttributeError:
            pass
        # Get the radical, it will be an image link :(
        self.radical = str(
                soup.find("p", {"class": _KP_BUSHU}).next_element.next_element)

        # Some entries don't have naritachi data :(
        try:
            naritachi_tag = soup.find(
                    "li", {"class": _KP_NARITACHI}).contents[-2]
            # Hack for some pesky exceptions
            if naritachi_tag == "\n":
                naritachi_tag = soup.find(
                        "li", {"class": _KP_NARITACHI}).contents[-1]
            naritachi_tag = naritachi_tag.contents[1]
            self._parse_components(naritachi_tag)
        except AttributeError:
            pass

        list_tag = soup.find_all(
                "p", {"class": _KP_ONKUN_YOMI})
        self._parse_readings(list_tag)

        bushu_list = soup.find(
                "ul", {"id": _KP_SAME_BUSHU})
        self._parse_related_kanji(bushu_list)

    def GetDataDict(self):
        """Returns a built data dictionary of the entry for storage."""
        kanji_dict = {
            "kanji": self.kanji,
            "origin_url": self.origin_url,
            "old_form": list(self.old_form),
            "radical": self.radical,
            "semantic_comp": list(self.semantic_comp),
            "phonetic_comp": self.phonetic_comp,
            "types": list(self.types),
            #"raw_text": self.raw_text,
            "related_kanji": list(self.related_kanji),
            "onyomi": list(self.onyomi),
            "kunyomi": list(self.kunyomi),
        }
        return kanji_dict

    def Display(self):
        print("Kanji: " + self.kanji)
        print(" Onyomi: " + str(self.onyomi))
        print(" Kunyomi: " + str(self.kunyomi))
        print(" Kanji old forms: " + str(self.old_form))
        print(" Type: " + str(self.types))
        print(" Radical: " + self.radical)
        print(" Phonetic component: " + str(self.phonetic_comp))
        print(" Semantic component: " + str(self.semantic_comp))
        print(" Related kanji: " + str(self.related_kanji))

