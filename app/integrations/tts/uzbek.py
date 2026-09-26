import re

APOSTROPHES = "ʻʼ'‘’`"
LATIN_TO_CYRILLIC = (
    ("oʻ", "ў"),
    ("gʻ", "ғ"),
    ("sh", "ш"),
    ("ch", "ч"),
    ("yo", "ё"),
    ("yu", "ю"),
    ("ya", "я"),
    ("ye", "е"),
    ("a", "а"),
    ("b", "б"),
    ("d", "д"),
    ("e", "е"),
    ("f", "ф"),
    ("g", "г"),
    ("h", "ҳ"),
    ("i", "и"),
    ("j", "ж"),
    ("k", "к"),
    ("l", "л"),
    ("m", "м"),
    ("n", "н"),
    ("o", "о"),
    ("p", "п"),
    ("q", "қ"),
    ("r", "р"),
    ("s", "с"),
    ("t", "т"),
    ("u", "у"),
    ("v", "в"),
    ("x", "х"),
    ("y", "й"),
    ("z", "з"),
    ("ʼ", "ъ"),
)
WORD = re.compile(r"[a-zʻʼ]+")
CYRILLIC = re.compile(r"[а-яёА-ЯЁ]")


UZBEK_LETTERS = re.compile(r"[og][ʻ'‘’`]", re.IGNORECASE)
UZBEK_WORDS = frozenset(
    {
        "va",
        "bilan",
        "uchun",
        "bor",
        "yoʻq",
        "siz",
        "sizning",
        "men",
        "kuni",
        "soat",
        "bugun",
        "ertaga",
        "nima",
        "qanday",
    }
)
UZBEK_WORD_MIN = 2


def has_cyrillic(text: str) -> bool:
    return CYRILLIC.search(text) is not None


def looks_uzbek(text: str) -> bool:
    if UZBEK_LETTERS.search(text):
        return True
    words = re.findall(r"[a-zʻ']+", text.lower())
    return sum(word in UZBEK_WORDS for word in words) >= UZBEK_WORD_MIN


def _normalize_apostrophes(text: str) -> str:
    text = re.sub(rf"(?<=[og])[{APOSTROPHES}]", "ʻ", text)
    return re.sub(rf"(?<![og])[{APOSTROPHES}]", "ʼ", text)


def _word_to_cyrillic(match: re.Match[str]) -> str:
    word = match.group(0)
    if word.startswith("e"):
        word = "э" + word[1:]
    for latin, cyrillic in LATIN_TO_CYRILLIC:
        word = word.replace(latin, cyrillic)
    return word


def to_cyrillic(text: str) -> str:
    return WORD.sub(_word_to_cyrillic, _normalize_apostrophes(text.lower()))
