import pytest

from pacs_check.normalize import has_contrast, is_localizer, regions


@pytest.mark.parametrize("text,expected", [
    ("CT hr+bř s k.l.", {"CHEST", "ABDOMEN"}),
    ("CT hrudníku, břicha a pánve s k.l.", {"CHEST", "ABDOMEN", "PELVIS"}),
    ("CT TAP", {"CHEST", "ABDOMEN", "PELVIS"}),
    ("PET/CT celotěl.", {"NECK", "CHEST", "ABDOMEN", "PELVIS"}),
    ("MR mozku s k.l.", {"HEAD"}),
    ("CT BRICHA NATIV", {"ABDOMEN"}),
    ("RTG kolene", set()),
])
def test_regions_from_czech_text(text, expected):
    assert regions(text) == expected


def test_body_part_only_as_fallback():
    assert regions("Venózní fáze 1.0 mm", "ABDOMEN") == {"ABDOMEN"}
    assert regions("CT hrudníku", "ABDOMEN") == {"CHEST"}


@pytest.mark.parametrize("text,expected", [
    ("CT břicha s k.l.", True), ("CT hr+KL", True), ("CT mozku nativ", False),
    ("Portální fáze", True), ("CT hrudníku", None),
])
def test_contrast(text, expected):
    assert has_contrast(text) is expected


def test_localizer():
    assert is_localizer("Topogram") and is_localizer("SCOUT 0.6") and not is_localizer("Venózní fáze")
