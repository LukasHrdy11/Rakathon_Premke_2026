"""Normalizace volného textu popisů vyšetření (česky, se zkratkami) na anatomické oblasti.

BodyPartExamined v DICOM bývá prázdné nebo chybné, proto se oblast odvozuje
hlavně z StudyDescription / SeriesDescription / textu žádanky.
"""

from __future__ import annotations

import re
import unicodedata

# oblast -> regexy nad textem bez diakritiky, malými písmeny
REGION_PATTERNS: dict[str, list[str]] = {
    "HEAD": [r"\bmozk", r"\bmozek", r"\bhlav", r"\blebk", r"\bbrain", r"\bhead\b", r"\bcranium"],
    "NECK": [r"\bkrk", r"\bkrcn", r"\bneck\b", r"\bstitn"],
    "CHEST": [r"\bhrud", r"\bhr\b", r"\bplic", r"\bthorax", r"\bchest\b", r"\bpulmo"],
    "ABDOMEN": [r"\bbric", r"\bbr\b", r"\babdom", r"\bjater", r"\bjatr", r"\bpankrea", r"\bledvin"],
    "PELVIS": [r"\bpanev", r"\bpanv", r"\bpelvi", r"\bprostat"],
    "SPINE": [r"\bpater", r"\bspine\b", r"\bbedern", r"\bhrudni pater"],
}

# kombinované / celotělové zkratky
COMPOSITE_PATTERNS: dict[str, set[str]] = {
    r"\bcelotel|\bwhole ?body|\bwb\b|\bpet": {"NECK", "CHEST", "ABDOMEN", "PELVIS"},
    r"\btap\b|\bcap\b": {"CHEST", "ABDOMEN", "PELVIS"},
    r"\bab?dom.{0,3}pel|\bbrich.{0,10}pan|\bap\b": {"ABDOMEN", "PELVIS"},
}

# DICOM BodyPartExamined -> oblast
BODY_PART_MAP: dict[str, set[str]] = {
    "HEAD": {"HEAD"}, "BRAIN": {"HEAD"}, "NECK": {"NECK"},
    "CHEST": {"CHEST"}, "THORAX": {"CHEST"}, "LUNG": {"CHEST"},
    "ABDOMEN": {"ABDOMEN"}, "LIVER": {"ABDOMEN"}, "PELVIS": {"PELVIS"},
    "ABDOMENPELVIS": {"ABDOMEN", "PELVIS"}, "CHESTABDOMEN": {"CHEST", "ABDOMEN"},
    "CHESTABDPELVIS": {"CHEST", "ABDOMEN", "PELVIS"}, "WHOLEBODY": {"NECK", "CHEST", "ABDOMEN", "PELVIS"},
    "SPINE": {"SPINE"}, "CSPINE": {"SPINE"}, "TSPINE": {"SPINE"}, "LSPINE": {"SPINE"},
}

_CONTRAST_YES = re.compile(r"\bs k\.? ?l\b|\bk\.l\.|\+ ?k\.?l|\+ ?c\b|\bkontrast|\bpost ?kl|\bcontrast\b|\bportal|\bvenoz|\barter")
_CONTRAST_NO = re.compile(r"\bnativ|\bbez k\.? ?l|\bnon.?contrast|\bsine\b")


def fold(text: str) -> str:
    """Malá písmena, bez diakritiky, '+' oddělené mezerami, ',;_' -> mezera."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return re.sub(r"[,;_]", " ", text.replace("+", " + "))


def regions_from_text(text: str) -> set[str]:
    t = fold(text)
    found: set[str] = set()
    for pattern, regions in COMPOSITE_PATTERNS.items():
        if re.search(pattern, t):
            found |= regions
    for region, patterns in REGION_PATTERNS.items():
        if any(re.search(p, t) for p in patterns):
            found.add(region)
    return found


def regions_from_body_part(body_part: str) -> set[str]:
    key = re.sub(r"[^A-Z]", "", (body_part or "").upper())
    return set(BODY_PART_MAP.get(key, set()))


def regions(description: str, body_part: str = "") -> set[str]:
    """Text má přednost; BodyPartExamined jen doplňuje, když text nic neřekne."""
    found = regions_from_text(description)
    return found or regions_from_body_part(body_part)


def has_contrast(text: str) -> bool | None:
    t = fold(text)
    if _CONTRAST_NO.search(t):
        return False
    if _CONTRAST_YES.search(t):
        return True
    return None


def is_localizer(description: str) -> bool:
    return bool(re.search(r"\btopogram|\bscout|\blocali[sz]er|\bsurview|\bdose ?report", fold(description)))
