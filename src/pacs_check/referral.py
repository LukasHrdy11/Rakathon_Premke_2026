"""Vytěžení zmínek o předchozích (zejm. externích) vyšetřeních z textu žádanky.

Baseline = regulární výrazy. Na hackathonu je místo pro LLM extraktor se stejným
rozhraním (vrací list[PriorMention]) – viz docs/03_navrh_reseni.md.
"""

from __future__ import annotations

import re
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

INTERNAL_PLACES = ("motol", "fn motol", "nase", "naseho")


@dataclass
class PriorMention:
    modality: str
    place: str
    approx_date: date | None
    regions: set[str]
    text: str

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


def extract_mentions(referral_text: str) -> list[PriorMention]:
    t = fold(referral_text)
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
            text=m.group(0),
        ))
    return out


def implies_follow_up(referral_text: str) -> bool:
    return bool(_FOLLOW_UP.search(fold(referral_text)))


def implies_oncology(referral_text: str) -> bool:
    return bool(_ONCOLOGY.search(fold(referral_text)))
