"""Vytěžení zmínek o předchozích (zejm. externích) vyšetřeních z textu žádanky.

Baseline = regulární výrazy. Na hackathonu je místo pro LLM extraktor se stejným
rozhraním (vrací list[PriorMention]) – viz docs/03_navrh_reseni.md.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date

from .normalize import fold, regions_from_text

_MODALITY = r"(?P<mod>ct|mr|mri|pet ?/ ?ct|pet|rtg|usg|uz)"
_PLACE = r"(?:z|ze|v|ve|na)\s+(?P<place>[a-z][a-z .-]{2,40}?)"
_DATE = r"(?P<date>\d{1,2}\.\s?\d{1,2}\.\s?\d{4}|\d{1,2}\s?/\s?\d{4}|\d{1,2}\.\s?\d{4})"
_MENTION = re.compile(rf"{_MODALITY}\b[^.;]{{0,40}}?{_PLACE}\s*(?:\(|,|\s)\s*(?:dne\s+)?{_DATE}")

# klíčová slova, že pacient má být sledován (kontrola, restaging…)
_FOLLOW_UP = re.compile(r"\bkontrol|\brestag|\bfollow|\bdispenz|\bpo (?:chemo|lecb|op|rt)|\bprogres|\brecist|\bstp\b")

_ONCOLOGY = re.compile(r"\bca\b|\bkarcinom|\bnador|\blymfom|\bmeta\b|\bmetast|\bonko|\brestag|\brecist|\bmelanom|\bsarkom")

# vyšetření podle textu NEPROBĚHLO. Jen jednoznačné výrazy: "odmítl", "zrušeno" se často týkají
# něčeho jiného ("odmítl kontrastní látku", "operace zrušena"). "Snímky nejsou k dispozici" negace
# není, to je přesně případ pro ePACS.
_NOT_DONE = re.compile(r"\bneproveden|\bnebyl[oa]? proveden|\bneprobehl|\bnerealizov")

INTERNAL_PLACES = ("motol", "fn motol", "nase", "naseho")


@dataclass
class PriorMention:
    modality: str
    place: str
    approx_date: date | None
    regions: set[str]
    text: str               # citace z původního textu žádanky (zdroj nálezu)
    place_text: str = ""    # místo, jak je napsané v žádance (pro zobrazení)
    negated: bool = False   # text říká, že vyšetření neproběhlo

    @property
    def internal(self) -> bool:
        return any(p in self.place for p in INTERNAL_PLACES)


def _parse_date(raw: str) -> date | None:
    nums = [int(n) for n in re.findall(r"\d+", raw)]
    try:
        if len(nums) == 3:
            return date(nums[2], nums[1], nums[0])
        if len(nums) == 2:
            return date(nums[1], nums[0], 1)
    except ValueError:
        return None
    return None


def _fold_same_length(text: str) -> str:
    """Jako normalize.fold, ale znak po znaku -> indexy sedí na původní text (kvůli citaci)."""
    out = []
    for c in text:
        base = "".join(x for x in unicodedata.normalize("NFKD", c) if not unicodedata.combining(x)).lower()
        out.append(" " if c in ",;_" else (base[:1] or " "))
    return "".join(out)


def _clause_after(text: str, end: int) -> str:
    """Klauzule hned za zmínkou: do ',' ';' nebo konce věty; začíná-li čárkou, ta následující."""
    parts = re.split(r"[,;]|\.\s|\.$", text[end:end + 80])
    first = parts[0].strip(" -–")
    return first if first or len(parts) < 2 else parts[1]


def extract_mentions(referral_text: str) -> list[PriorMention]:
    referral_text = referral_text or ""
    t = _fold_same_length(referral_text)
    out = []
    for m in _MENTION.finditer(t):
        mod = m.group("mod").replace(" ", "").upper()
        mod = {"MRI": "MR", "PET/CT": "PT", "PET": "PT", "UZ": "US", "USG": "US", "RTG": "CR"}.get(mod, mod)
        sentence = t[max(0, m.start() - 10): m.end() + 40]
        out.append(PriorMention(
            modality=mod,
            place=m.group("place").strip(),
            approx_date=_parse_date(m.group("date")),
            regions=regions_from_text(sentence),
            text=referral_text[m.start():m.end()],
            place_text=referral_text[m.start("place"):m.end("place")].strip(),
            negated=bool(_NOT_DONE.search(m.group(0) + " " + fold(_clause_after(referral_text, m.end())))),
        ))
    return out


def implies_follow_up(referral_text: str) -> bool:
    return bool(_FOLLOW_UP.search(fold(referral_text)))


def implies_oncology(referral_text: str) -> bool:
    return bool(_ONCOLOGY.search(fold(referral_text)))
