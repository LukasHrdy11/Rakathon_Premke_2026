"""Jádro: pro každé plánované CT najde relevantní předchozí vyšetření a ověří jejich dostupnost.

Klíčová myšlenka: "chybějící" vyšetření lze poznat jen tak, že ho očekává jiný zdroj
(RIS historie, text žádanky, onkologický rytmus kontrol). Samotný dotaz do PACS
ukáže jen to, co v PACS je.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Protocol

from .models import (
    Availability, CaseResult, Finding, PlannedExam, RisRecord, Series, Status, Study,
)
from .normalize import has_contrast, is_localizer, regions
from .referral import extract_mentions, implies_follow_up, implies_oncology


class PacsSource(Protocol):
    def studies_for_patient(self, patient_id: str) -> list[Study]: ...


class RisSource(Protocol):
    def history_for_patient(self, patient_id: str) -> list[RisRecord]: ...


@dataclass
class Rules:
    """Parametry relevance – ověřit se zadavatelem (viz docs/04_otazky_pro_zadavatele.md)."""

    comparable_modalities: dict[str, set[str]] = field(default_factory=lambda: {
        "CT": {"CT", "PT", "MR"},
    })
    lookback_days: int = 5 * 365
    oncology_followup_days: int = 180      # starší poslední kontrola => podezřelá mezera
    max_diagnostic_slice_mm: float = 5.0
    home_institutions: tuple[str, ...] = ("FN Motol",)
    mention_date_tolerance_days: int = 45


def _is_home(institution: str, rules: Rules) -> bool:
    return not institution or any(h.lower() in institution.lower() for h in rules.home_institutions)


def is_relevant(planned: PlannedExam, study: Study, rules: Rules) -> bool:
    allowed = rules.comparable_modalities.get(planned.modality, {planned.modality})
    if not set(study.modalities) & allowed:
        return False
    if not (study.study_date < planned.scheduled_date
            and (planned.scheduled_date - study.study_date).days <= rules.lookback_days):
        return False
    study_regions = regions(study.description) or set().union(
        *(regions(s.description, s.body_part) for s in study.series)
    )
    return bool(regions(planned.description) & study_regions)


def diagnostic_series(study: Study, rules: Rules) -> list[Series]:
    return [
        s for s in study.series
        if not is_localizer(s.description)
        and (s.slice_thickness is None or s.slice_thickness <= rules.max_diagnostic_slice_mm)
    ]


def _check_study(planned: PlannedExam, study: Study, role: str, rules: Rules) -> list[Finding]:
    out: list[Finding] = []
    label = f"{role} {study.study_date:%d.%m.%Y} {study.description}"
    if study.availability in (Availability.NEARLINE, Availability.OFFLINE):
        out.append(Finding(Status.ARCHIVED_PREFETCH,
                           f"{label}: data v archivu ({study.availability.value})",
                           "Spustit prefetch (C-MOVE) na diagnostickou stanici", study.study_uid))
    if study.series and not diagnostic_series(study, rules):
        out.append(Finding(Status.INCOMPLETE_SERIES,
                           f"{label}: jen topogram/tlusté řezy, chybí diagnostická série",
                           "Dohledat rekonstrukce / chybějící série (modalita, archiv)", study.study_uid))
    want_contrast = has_contrast(planned.description)
    if want_contrast and study.series and "CT" in study.modalities:
        if not any(has_contrast(s.description) or s.contrast_agent for s in diagnostic_series(study, rules)):
            out.append(Finding(Status.OK, f"{label}: pouze nativní série (plánováno s k.l.)", "", study.study_uid))
    if not out:
        out.append(Finding(Status.OK, f"{label}: dostupné", "", study.study_uid))
    return out


def check_case(planned: PlannedExam, pacs: PacsSource, ris: RisSource | None = None,
               rules: Rules | None = None) -> CaseResult:
    rules = rules or Rules()
    result = CaseResult(planned)
    studies = [s for s in pacs.studies_for_patient(planned.patient_id) if s.accession != planned.accession]
    relevant = sorted((s for s in studies if is_relevant(planned, s, rules)), key=lambda s: s.study_date)

    # 1) RIS říká "provedeno", PACS nemá
    pacs_accessions = {s.accession for s in studies if s.accession}
    if ris is not None:
        for rec in ris.history_for_patient(planned.patient_id):
            if rec.accession == planned.accession or rec.status != "COMPLETED":
                continue
            fake = Study("", rec.patient_id, rec.exam_date, [rec.modality], rec.description, rec.accession)
            if is_relevant(planned, fake, rules) and rec.accession not in pacs_accessions:
                result.findings.append(Finding(
                    Status.MISSING_IN_PACS,
                    f"RIS: {rec.modality} {rec.exam_date:%d.%m.%Y} „{rec.description}“ (acc. {rec.accession}) není v PACS",
                    "Ověřit odeslání z modality / reindexaci v PACS"))

    # 2) Žádanka zmiňuje externí vyšetření, které v PACS není
    for m in extract_mentions(planned.referral_text):
        if m.internal:
            continue
        matched = any(
            not _is_home(s.institution, rules)
            and (m.approx_date is None
                 or abs((s.study_date - m.approx_date).days) <= rules.mention_date_tolerance_days)
            for s in studies
        )
        if not matched:
            when = f" ({m.approx_date:%m/%Y})" if m.approx_date else ""
            result.findings.append(Finding(
                Status.EXTERNAL_REQUEST_EPACS,
                f"Žádanka zmiňuje {m.modality} – {m.place.title()}{when}, v PACS nenalezeno",
                f"Vyžádat snímky přes ePACS/ReDiMed z: {m.place.title()}"))

    # 3) Výběr komparátorů: poslední relevantní + u onkologie baseline (nejstarší v okně)
    oncology = planned.oncology or implies_oncology(planned.referral_text)
    follow_up = oncology or implies_follow_up(planned.referral_text)
    if relevant:
        latest = relevant[-1]
        result.comparators.append(latest)
        result.findings += _check_study(planned, latest, "Poslední", rules)
        if oncology and len(relevant) > 1:
            baseline = relevant[0]
            result.comparators.insert(0, baseline)
            result.findings += _check_study(planned, baseline, "Baseline", rules)
        gap = (planned.scheduled_date - latest.study_date).days
        if follow_up and gap > rules.oncology_followup_days:
            result.findings.append(Finding(
                Status.NEEDS_HUMAN,
                f"Poslední relevantní vyšetření je {gap} dní staré – chybí mezikontrola?",
                "Ověřit u pacienta/ošetřujícího, zda nebyl vyšetřen jinde"))
    elif follow_up and not any(f.status == Status.EXTERNAL_REQUEST_EPACS for f in result.findings):
        result.findings.append(Finding(
            Status.NEEDS_HUMAN,
            "Kontrolní/onkologické vyšetření, ale žádné předchozí relevantní snímky",
            "Ověřit, kde byl pacient dříve vyšetřen"))
    elif not result.findings:
        result.findings.append(Finding(Status.NO_PRIOR_EXPECTED, "První vyšetření oblasti, nic se nečeká"))
    return result


def check_all(planned: list[PlannedExam], pacs: PacsSource, ris: RisSource | None = None,
              rules: Rules | None = None) -> list[CaseResult]:
    results = [check_case(p, pacs, ris, rules) for p in planned]
    return sorted(results, key=lambda r: (r.planned.scheduled_date, -r.status.severity))


def planned_in_window(planned: list[PlannedExam], start: date, days: int) -> list[PlannedExam]:
    end = start + timedelta(days=days)
    return [p for p in planned if start <= p.scheduled_date <= end]
