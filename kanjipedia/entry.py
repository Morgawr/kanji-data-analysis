"""Module to handle individual kanjipedia entry data."""
import enum
import re
import requests
import sys

from bs4 import BeautifulSoup, NavigableString, Tag

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


# This gets rid of the pesky images with relative links
def _GetRealIMGPath(text):
    return text.replace('src="/', 'src="' + _KANJIPEDIA_URL + '/')


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

    @staticmethod
    def StrFromEnum(value):
        namemap = {
            KanjiType.SHIJI: "指事",
            KanjiType.SHOUKEI: "象形",
            KanjiType.KAII: "会意",
            KanjiType.KEISEI: "形声",
            KanjiType.TENCHUU: "転注",
            KanjiType.KASHA: "仮借",
        }
        return namemap[value]

# TODO(morg): add support for grade order, JLPT (if any??), jouyou vs non-jouyou
# TODO(morg): add support for searching/stripping kunyomi readings from kanji
#             okurigana separator
class Entry:

    def __init__(self):
        self.origin_url = None
        self.kanji = None
        self.old_form = set() # Some kanji can have multiple old forms? wtf
        self.radical = None
        self.semantic_comp = set()
        self.phonetic_comp = None
        self.types = set()
        self.related_kanji = set()
        self.onyomi = set()
        self.kunyomi = set()
        # The following fields are not supported/are ignored in kanjipedia scraping
        # entries.
        self.onyomi_ext = set()
        self.kunyomi_ext = set()
        self.onyomi_all = set()
        self.kunyomi_all = set()
        self.meaning = None
        self.naritachi = None

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
        # TODO(morg): support meaning and naritachi import from database
        entry = Entry()
        entry.origin_url = data["origin_url"]
        entry.kanji = data["kanji"]
        entry.old_form = set(data["old_form"])
        entry.radical = data["radical"]
        entry.semantic_comp = set(data["semantic_comp"])
        entry.phonetic_comp = data["phonetic_comp"]
        entry.types = set([KanjiType(s) for s in data["types"]])
        entry.related_kanji = set(data["related_kanji"])
        entry.onyomi = set(data["onyomi"])
        entry.onyomi_ext = set(data.get("onyomi_ext", []))
        entry.kunyomi = set(data["kunyomi"])
        entry.kunyomi_ext = set(data.get("kunyomi_ext", []))
        entry.onyomi_all = set(data.get("onyomi_all", []))
        entry.kunyomi_all = set(data.get("kunyomi_all", []))
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
        in_ext_mode = False
        def _get_on_reading(element):
            for on in re.sub(r"・", " ", str(element).strip()).split(" "):
                if not in_ext_mode:
                    self.onyomi.add(str(on).strip())
                else:
                    self.onyomi_ext.add(str(on).strip())
        # Loop through each onyomi element
        for child in list_tag[0]:
            if isinstance(child, NavigableString):
                _get_on_reading(child)
            elif isinstance(child, Tag):
                if child.name == "span":
                    for child2 in child:
                        if isinstance(child2, NavigableString):
                            _get_on_reading(child2)
                        elif isinstance(child, Tag):
                            if child2.name == "img" and "外" in str(child2):
                                in_ext_mode = True
                elif child.name == "img" and "外" in str(child):
                    in_ext_mode = True

        # Let's work on kunyomi now
        in_ext_mode = False
        kun_builder = ""
        for child in list_tag[1]:
            if isinstance(child, NavigableString):
                kun_builder += str(child).strip()
            elif isinstance(child, Tag):
                if child.name == "span":
                    if child.get("class") and child.get(
                            "class")[0] == "txtNormal":
                        for child2 in child:
                            if child2.name != "img":
                                if "・" in str(child2):
                                    kuns = str(child2).split("・")
                                    for k in kuns[:-1]:
                                        if kun_builder.strip():
                                            kun_builder += "."
                                        self.kunyomi.add(
                                                str(kun_builder +
                                                    str(k).strip()).strip())
                                        kun_builder = ""
                                    kun_builder = kuns[-1].strip()
                                else:
                                    if "・" in kun_builder:
                                        kuns = kun_builder.split("・")
                                        for k in kuns[:-1]:
                                            if k.strip():
                                                self.kunyomi.add(k.strip())
                                        kun_builder = kuns[-1]
                                    self.kunyomi.add(
                                            str(kun_builder + "." +
                                                str(child2)).replace(
                                                    "・", "").strip())
                                    kun_builder = ""
                    elif child.get("style") == "color:#000000":
                        if kun_builder:
                            for kun in kun_builder.split("・"):
                                if kun.strip():
                                    self.kunyomi.add(kun.strip())
                        kun_builder = ""
                        in_ext_mode = True
                        # We are in 外 territory now
                        for child2 in child:
                            if isinstance(child2, NavigableString):
                                kun_builder += str(child2).strip()
                            elif isinstance(child2, Tag):
                                if child2.name != "img":
                                    for child3 in child2:
                                        if "・" in str(child3):
                                            kuns = str(child3).split("・")
                                            for k in kuns[:-1]:
                                                if kun_builder.strip():
                                                    kun_builder += "."
                                                self.kunyomi_ext.add(
                                                        str(kun_builder +
                                                            str(k).strip(
                                                                )).strip())
                                                kun_builder = ""
                                            kun_builder = kuns[-1]
                                        else:
                                            if "・" in kun_builder:
                                                kuns = kun_builder.split("・")
                                                for k in kuns[:-1]:
                                                    if k.strip():
                                                        self.kunyomi_ext.add(
                                                                k.strip())
                                                kun_builder = kuns[-1]
                                            self.kunyomi_ext.add(
                                                    str(kun_builder + "." +
                                                        str(child3)).replace(
                                                            "・", "").strip())
                                            kun_builder = ""
        if kun_builder:
            if in_ext_mode:
                if "・" in kun_builder:
                    kuns = kun_builder.split("・")
                    for k in kuns:
                        if k.strip():
                            self.kunyomi_ext.add(k.strip())
                else:
                    self.kunyomi_ext.add(kun_builder.strip())
            else:
                if "・" in kun_builder:
                    kuns = kun_builder.split("・")
                    for k in kuns:
                        if k.strip():
                            self.kunyomi.add(k.strip())
                else:
                    self.kunyomi.add(kun_builder.strip())

    def _handle_special_readings(self):
        # Some kanji are wrong, so we manually fix them :/
        if self.kanji == "擬":
            self.onyomi.add("ギ")
            self.kunyomi_ext.add("なぞら.える")
            self.kunyomi_ext.add("はか.る")
            self.kunyomi_ext.add("まがい")
            self.kunyomi_ext.add("まどき")
            self.kunyomi_ext.add("まど.く")
        elif self.kanji == "絡":
            self.onyomi.add("ラク")
            self.kunyomi.add("から.む")
            self.kunyomi.add("から.まる")
            self.kunyomi.add("から.める")
            self.kunyomi_ext.add("まと.う")
            self.kunyomi_ext.add("から.げる")
            self.kunyomi_ext.add("つな.がる")
        elif self.kanji == "果":
            self.onyomi.add("カ")
            self.kunyomi.add("は.たす")
            self.kunyomi.add("は.てる")
            self.kunyomi.add("は.て")
            self.kunyomi_ext.add("くだもの")
            self.kunyomi_ext.add("は.たして")
            self.kunyomi_ext.add("おお.せる")
            self.kunyomi_ext.add("はか")
        else:
            return False
        return True


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
        if not self._handle_special_readings():
            self._parse_readings(list_tag)
        self.onyomi_all = self.onyomi.union(self.onyomi_ext)
        self.kunyomi_all = self.kunyomi.union(self.kunyomi_ext)

        bushu_list = soup.find(
                "ul", {"id": _KP_SAME_BUSHU})
        self._parse_related_kanji(bushu_list)

    def GetDataDict(self):
        """Returns a built data dictionary of the entry for storage."""
        # TODO(morg): support meaning and naritachi
        kanji_dict = {
            "kanji": self.kanji,
            "origin_url": self.origin_url,
            "old_form": list(self.old_form),
            "radical": self.radical,
            "semantic_comp": list(self.semantic_comp),
            "phonetic_comp": self.phonetic_comp,
            "types": list(self.types),
            "related_kanji": list(self.related_kanji),
            "onyomi": list(self.onyomi),
            "onyomi_ext": list(self.onyomi_ext),
            "kunyomi": list(self.kunyomi),
            "kunyomi_ext": list(self.kunyomi_ext),
            "onyomi_all": list(self.onyomi_all),
            "kunyomi_all": list(self.kunyomi_all),
        }
        return kanji_dict

    def Display(self):
        print("Kanji: " + self.kanji)
        print(" Onyomi: " + str(self.onyomi))
        if self.meaning:
            print(" Meaning: " + str(self.meaning))
        if self.naritachi:
            print(" 成り立ち: " + str(self.naritachi))
        if self.onyomi_ext:
            print(" Onyomi Ext: " + str(self.onyomi_ext))
        print(" Kunyomi: " + str(self.kunyomi))
        if self.kunyomi_ext:
            print(" Kunymomi Ext: " + str(self.kunyomi_ext))
        if self.old_form:
            print(" Kanji old forms: " + str(self.old_form))
        print(" Type: " + str(self.types))
        print(" Radical: " + self.radical)
        if self.phonetic_comp:
            print(" Phonetic component: " + str(self.phonetic_comp))
        if self.semantic_comp:
            print(" Semantic component: " + str(self.semantic_comp))
        print(" Related kanji: " + str(self.related_kanji))

    def GenerateHTML(self):
        """Generates a small HTML <div> snippet of the kanji entry."""
        # TODO(morg): support meaning and naritachi fields in web view
        output = '<div id="kanji_block">'
        output += '<div id="oyaji">'
        output += '<a href="' + self.origin_url + '">' + self.kanji + '</a>'
        if self.old_form:
            output += ' ('
            for k in self.old_form:
                output += _GetRealIMGPath(k) + ' '
            output += ')'
        output += '</div>'
        output += '<div id="readings">'
        output += '<p id="onyomi"> Onyomi: '
        for on in self.onyomi:
            output += on + '、 '
        if self.onyomi_ext:
            output += " (外) "
        for on in self.onyomi_ext:
            output += on + '、 '
        output += '</p>'
        output += '<p id="kunyomi"> Kunyomi: '
        for kun in self.kunyomi:
            output += kun + '、 '
        if self.kunyomi_ext:
            output += " (外) "
        for kun in self.kunyomi_ext:
            output += kun + '、 '
        output += '</p>'
        output += '</div>' # /readings
        output += '<div id="types">'
        output += '<p id="type"> Type: '
        for t in self.types:
            output += KanjiType.StrFromEnum(t) + ' '
        output += '</p>'
        output += '<table>'
        output += '<tr><th>部首</th><th>意符</th><th>音符</th></tr>'
        output += '<tr>'
        output += '<td>' + _GetRealIMGPath(self.radical) + '</td>'
        output += '<td>'
        if self.semantic_comp:
            for i in self.semantic_comp:
                output += _GetRealIMGPath(i) + ' '
        else:
            output += 'N/A'
        output += '</td>'
        output += '<td>'
        if self.phonetic_comp:
            output += _GetRealIMGPath(self.phonetic_comp)
        else:
            output += 'N/A'
        output += '</td>'
        output += '</tr>'
        output += '</table>'
        output += '</div>' # /types
        if self.related_kanji:
            output += '<div id="related"> Related Kanji: '
            for k in self.related_kanji:
                output += _GetRealIMGPath(k) + ' '
            output += '</div>'
        output += '</div>' # /kanji block
        return BeautifulSoup(output, "html.parser").prettify()

