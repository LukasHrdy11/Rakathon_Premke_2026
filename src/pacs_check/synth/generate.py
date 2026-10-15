"""Generátor syntetických scénářů. Žádná reálná data – všichni pacienti jsou smyšlení.

Výstup (data/generated/):
  worklist.json      plánovaná CT (náhrada RIS/MWL)
  ris.json           historie vyšetření podle RIS
  pacs.json          index PACS (pro běh bez Dockeru)
  dicom/*.dcm        hlavičky DICOM bez pixelů (nahrát do Orthancu)
  worklists/*.wl     Modality Worklist soubory pro Orthanc
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

from ..adapters.json_files import dump
from ..models import Availability, PlannedExam, RisRecord, Series, Study

CT_IMAGE_STORAGE = "1.2.840.10008.5.1.4.1.1.2"
UID_ROOT = "1.2.826.0.1.3680043.10.1499."  # pydicom-generated prefix pro testovací UID


@dataclass
class Scenario:
    planned: PlannedExam
    priors: list[Study] = field(default_factory=list)
    ris: list[RisRecord] = field(default_factory=list)
    expected: str = ""


def _ser(desc: str, thick: float | None = 1.0, contrast: str = "", avail=Availability.ONLINE,
         body_part: str = "", modality: str = "CT") -> Series:
    return Series(generate_uid(UID_ROOT), modality, desc, body_part, thick, contrast, 1, avail)


def _std(pid: str, d: date, desc: str, series: list[Series], acc: str, inst: str = "FN Motol",
         mods: list[str] | None = None) -> Study:
    return Study(generate_uid(UID_ROOT), pid, d, mods or ["CT"], desc, acc, inst, series)


def _ct_full(avail=Availability.ONLINE) -> list[Series]:
    return [_ser("Topogram", None, avail=avail),
            _ser("Venózní fáze 1.0 mm", 1.0, "Iomeron 350", avail),
            _ser("Venózní fáze 5.0 mm", 5.0, "Iomeron 350", avail)]


def build_scenarios(today: date) -> list[Scenario]:
    T = lambda days: today + timedelta(days=days)  # noqa: E731
    sc: list[Scenario] = []

    def planned(n, days, desc, referral, onco=False, priority="ROUTINE"):
        return PlannedExam(f"PLAN{n:03d}", f"SYN{n:03d}", f"TEST^PACIENT{n:02d}", T(days), "CT", desc, referral, onco,
                           priority)

    # 1) Vše v pořádku: onkologie, poslední kontrola + baseline online
    p = planned(1, 1, "CT hr+bř s k.l.", "Ca plic, restaging po 3. cyklu chemoterapie.", True)
    sc.append(Scenario(p, [
        _std("SYN001", T(-400), "CT hrudníku a břicha s k.l.", _ct_full(), "A1001"),
        _std("SYN001", T(-90), "CT hr+bř s k.l.", _ct_full(), "A1002"),
    ], expected="OK"))

    # 2) Baseline je v offline archivu -> prefetch
    p = planned(2, 1, "CT hrudníku, břicha a pánve s k.l.", "Lymfom, kontrola po léčbě, srovnat s výchozím stavem.", True)
    sc.append(Scenario(p, [
        _std("SYN002", T(-900), "CT TAP s k.l.", _ct_full(Availability.OFFLINE), "A2001"),
        _std("SYN002", T(-100), "CT TAP s k.l.", _ct_full(), "A2002"),
    ], expected="ARCHIVED_PREFETCH"))

    # 3) Předchozí CT má jen topogram a tlusté řezy
    p = planned(3, 2, "CT břicha s k.l.", "Kontrola ložiska v játrech.")
    sc.append(Scenario(p, [
        _std("SYN003", T(-60), "CT břicha s k.l.", [_ser("Topogram", None), _ser("Portální fáze 8 mm", 8.0, "Iomeron 350")], "A3001"),
    ], expected="INCOMPLETE_SERIES"))

    # 4) Externí CT zmíněné v žádance, v PACS není. CT za 2 dny, ePACS potřebuje 3 -> eskalace
    ext = T(-75)
    p = planned(4, 2, "CT břicha s k.l.",
                f"Ca pankreatu. CT břicha z Oblastní nemocnice Kladno {ext.month:02d}/{ext.year}, prosím srovnat.", True)
    sc.append(Scenario(p, [], expected="EXTERNAL_REQUEST_EPACS"))

    # 5) RIS hlásí provedené CT, PACS ho nemá (nedoputovalo z modality)
    p = planned(5, 3, "CT hrudníku s k.l.", "Kontrola plicního uzlu dle Fleischnera.")
    sc.append(Scenario(p, [
        _std("SYN005", T(-200), "CT hrudníku s k.l.", _ct_full(), "A5001"),
    ], ris=[
        RisRecord("A5001", "SYN005", T(-200), "CT", "CT hrudníku s k.l."),
        RisRecord("A5002", "SYN005", T(-40), "CT", "CT hrudníku nativ"),
    ], expected="MISSING_IN_PACS"))

    # 6) Onkologický pacient, poslední kontrola před >1 rokem -> podezřelá mezera
    p = planned(6, 3, "CT hr+bř s k.l.", "Ca prsu, dispenzarizace, restaging.", True)
    sc.append(Scenario(p, [
        _std("SYN006", T(-420), "CT hrudníku a břicha s k.l.", _ct_full(), "A6001"),
    ], expected="NEEDS_HUMAN"))

    # 7) První vyšetření hlavy, předchozí jen nerelevantní (břicho, RTG)
    p = planned(7, 4, "CT mozku nativ", "Bolesti hlavy, první vyšetření.")
    sc.append(Scenario(p, [
        _std("SYN007", T(-300), "CT břicha s k.l.", _ct_full(), "A7001"),
        _std("SYN007", T(-30), "RTG kolene", [_ser("AP+bok", None, modality="CR")], "A7002", mods=["CR"]),
    ], expected="NO_PRIOR_EXPECTED"))

    # 8) Externí MR z Homolky už je naimportované v PACS -> OK
    mr = T(-50)
    p = planned(8, 4, "CT mozku s k.l.", f"Meta do mozku? MR mozku z Nemocnice Na Homolce {mr.month:02d}/{mr.year}.", True)
    sc.append(Scenario(p, [
        _std("SYN008", mr, "MR mozku s k.l.", [_ser("T1 MPRAGE post k.l.", 1.0, "Gadovist", modality="MR"),
                                               _ser("FLAIR", 3.0, modality="MR")],
             "H8001", "Nemocnice Na Homolce", ["MR"]),
    ], expected="OK"))

    # 9) Prázdný BodyPartExamined, oblast jen ze zkratky "TAP"
    p = planned(9, 5, "CT hrudníku s k.l.", "Kontrola po pneumonii.")
    sc.append(Scenario(p, [
        _std("SYN009", T(-120), "CT TAP", _ct_full(), "A9001"),
    ], expected="OK"))

    # 10) Předchozí jen nativně, plánováno s k.l. -> OK s poznámkou
    p = planned(10, 5, "CT břicha s k.l.", "Bolesti břicha, kontrola.")
    sc.append(Scenario(p, [
        _std("SYN010", T(-150), "CT břicha nativ", [_ser("Topogram", None), _ser("Nativ 1.0 mm", 1.0, body_part="ABDOMEN")], "A10001"),
    ], expected="OK"))

    # 11) Negace: externí CT podle žádanky NEPROBĚHLO -> nic nevyžadovat, zmínku ale ukázat se zdrojem
    p = planned(11, 5, "CT břicha s k.l.",
                f"Bolesti břicha. CT břicha z Nemocnice Kladno {ext.month:02d}/{ext.year} neprovedeno, pacient se nedostavil.")
    sc.append(Scenario(p, [], expected="NO_PRIOR_EXPECTED"))

    # 12) Fast track: suspektní ložisko z regionu (dojíždí do Prahy), "snímky nejsou k dispozici" NENÍ negace
    #     -> ePACS, priorita HIGH, termín úkolu zítra (zatím bez eskalace)
    reg = T(-10)
    p = planned(12, 4, "CT hrudníku s k.l.",
                f"Susp. karcinom plic, fast track. CT hrudníku z Nemocnice Kladno {reg.day}. {reg.month}. {reg.year}, "
                "snímky nejsou k dispozici.", True, "HIGH")
    sc.append(Scenario(p, [], expected="EXTERNAL_REQUEST_EPACS"))

    # 13) Zmínka s datem PO plánovaném CT (překlep nebo teprve plánované vyšetření) -> ověřit ručně
    fut = T(40)
    p = planned(13, 6, "CT mozku nativ", f"Závratě. MR mozku z Nemocnice Na Homolce {fut.month:02d}/{fut.year}.")
    sc.append(Scenario(p, [], expected="NEEDS_HUMAN"))
    return sc


def _dicom_instance(study: Study, series: Series, patient_name: str) -> Dataset:
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = CT_IMAGE_STORAGE if series.modality == "CT" else "1.2.840.10008.5.1.4.1.1.7"
    meta.MediaStorageSOPInstanceUID = generate_uid(UID_ROOT)
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds = Dataset()
    ds.file_meta = meta
    ds.SpecificCharacterSet = "ISO_IR 192"
    ds.SOPClassUID = meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.PatientID = study.patient_id
    ds.PatientName = patient_name
    ds.StudyInstanceUID = study.study_uid
    ds.StudyDate = study.study_date.strftime("%Y%m%d")
    ds.StudyDescription = study.description
    ds.AccessionNumber = study.accession
    ds.InstitutionName = study.institution
    ds.SeriesInstanceUID = series.series_uid
    ds.SeriesDescription = series.description
    ds.SeriesNumber = 1
    ds.InstanceNumber = 1
    ds.Modality = series.modality
    if series.body_part:
        ds.BodyPartExamined = series.body_part
    if series.slice_thickness is not None:
        ds.SliceThickness = series.slice_thickness
    if series.contrast_agent:
        ds.ContrastBolusAgent = series.contrast_agent
    ds.InstanceAvailability = series.availability.value
    return ds


def _worklist_item(p: PlannedExam) -> Dataset:
    ds = Dataset()
    ds.file_meta = FileMetaDataset()
    ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds.file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.31"
    ds.file_meta.MediaStorageSOPInstanceUID = generate_uid(UID_ROOT)
    ds.SpecificCharacterSet = "ISO_IR 192"
    ds.PatientID = p.patient_id
    ds.PatientName = p.patient_name
    ds.AccessionNumber = p.accession
    ds.RequestedProcedureDescription = p.description
    ds.ReasonForTheRequestedProcedure = p.referral_text[:64]
    ds.RequestedProcedureComments = p.referral_text
    ds.RequestedProcedurePriority = p.priority
    sps = Dataset()
    sps.Modality = p.modality
    sps.ScheduledStationAETitle = "CT_MOTOL_1"
    sps.ScheduledProcedureStepStartDate = p.scheduled_date.strftime("%Y%m%d")
    sps.ScheduledProcedureStepDescription = p.description
    ds.ScheduledProcedureStepSequence = [sps]
    return ds


def generate(out_dir: Path, today: date | None = None) -> list[Scenario]:
    today = today or date.today()
    scenarios = build_scenarios(today)
    for sub in ("dicom", "worklists"):
        shutil.rmtree(out_dir / sub, ignore_errors=True)
        (out_dir / sub).mkdir(parents=True)

    (out_dir / "meta.json").write_text(f'{{"today": "{today.isoformat()}"}}\n')
    dump(out_dir / "worklist.json", [s.planned for s in scenarios])
    dump(out_dir / "ris.json", [r for s in scenarios for r in s.ris])
    dump(out_dir / "pacs.json", [st for s in scenarios for st in s.priors])
    (out_dir / "expected.json").write_text(
        "{\n" + ",\n".join(f'  "{s.planned.accession}": "{s.expected}"' for s in scenarios) + "\n}\n")

    for s in scenarios:
        for st in s.priors:
            for se in st.series:
                _dicom_instance(st, se, s.planned.patient_name).save_as(
                    out_dir / "dicom" / f"{se.series_uid}.dcm", enforce_file_format=True)
        _worklist_item(s.planned).save_as(out_dir / "worklists" / f"{s.planned.accession}.wl",
                                          enforce_file_format=True)
    return scenarios
