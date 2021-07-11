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
_KP_SAME_BUSHI = "sameBushiList"


class KanjiType(enum.Enum):
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
        self.origin_url = None
        self.kanji = None
        self.old_form = set() # Some kanji can have multiple old forms? wtf
        self.meaning = None
        self.radical = None
        self.semantic_comp = set()
        self.phonetic_comp = None
        self.types = set()
        self.raw_text = ""
        self.related_kanji = set()
        self.onyomi = set()
        self.kunyomi = set()

    @staticmethod
    def FromURL(url):
        url = url if _KANJIPEDIA_URL in url else _KANJIPEDIA_URL + url
        entry = Entry()
        entry.origin_url = url.strip()
        # Load HTML data into the entry
        entry.raw_text = requests.get(entry.origin_url).text
        entry._parse_HTML()
        return entry

    def _parse_components(self, naritachi_tag):
        # Remove text in parentheses cause it doesn't help and breaks our
        # parsing code
        naritachi = re.sub(r"(（[^()]*）|\([^()]*\))", "",
                           str(naritachi_tag).split("<br/>")[-1])
        self.types = KanjiType.GetKanjiTypes(naritachi)

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

    def _parse_HTML(self):
        soup = BeautifulSoup(self.raw_text, "html.parser")
        #print(self.origin_url, file=sys.stderr)
        #print(self.raw_text)
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

        naritachi_tag = soup.find(
                "li", {"class": _KP_NARITACHI}).contents[-2].contents[1]
        self._parse_components(naritachi_tag)

        list_tag = soup.find_all(
                "p", {"class": _KP_ONKUN_YOMI})
        self._parse_readings(list_tag)

        #print(soup.prettify())
