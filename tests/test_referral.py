from datetime import date

from pacs_check.referral import extract_mentions, implies_follow_up, implies_oncology


def test_external_ct_mention():
    [m] = extract_mentions("Ca pankreatu. CT břicha z Oblastní nemocnice Kladno 07/2026, prosím srovnat.")
    assert m.modality == "CT" and "kladno" in m.place and m.approx_date == date(2026, 7, 1)
    assert m.regions == {"ABDOMEN"} and not m.internal


def test_full_date_and_pet():
    [m] = extract_mentions("PET/CT ve FN Motol dne 3. 2. 2026 bez progrese.")
    assert m.modality == "PT" and m.approx_date == date(2026, 2, 3) and m.internal


def test_no_mention():
    assert extract_mentions("Bolesti hlavy, první vyšetření.") == []


def test_flags():
    assert implies_follow_up("Kontrola po léčbě") and not implies_follow_up("Bolesti břicha")
    assert implies_oncology("Ca prsu, dispenzarizace") and not implies_oncology("Kontrola po pneumonii")


def test_citation_keeps_original_text():
    [m] = extract_mentions("Ca + meta. CT břicha z Oblastní nemocnice Kladno 07/2026, prosím srovnat.")
    assert m.text == "CT břicha z Oblastní nemocnice Kladno 07/2026"


def test_negation_only_when_exam_did_not_happen():
    [m] = extract_mentions("CT břicha z Nemocnice Kladno 08/2026 neprovedeno, pacient se nedostavil.")
    assert m.negated
    [m] = extract_mentions("CT hrudníku z Nemocnice Kladno 08/2026, snímky nejsou k dispozici.")
    assert not m.negated   # snímky chybí = přesně případ pro ePACS
    [m] = extract_mentions("CT břicha z Nemocnice Kladno 08/2026, pacient odmítl kontrastní látku.")
    assert not m.negated   # CT proběhlo, odmítnutí se týká k.l.
    [m] = extract_mentions("CT břicha z Nemocnice Kladno 08/2026, neprovedeno.")
    assert m.negated


def test_place_keeps_diacritics_for_display():
    [m] = extract_mentions("CT břicha z Oblastní nemocnice Kladno 07/2026.")
    assert m.place_text == "Oblastní nemocnice Kladno"
