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
