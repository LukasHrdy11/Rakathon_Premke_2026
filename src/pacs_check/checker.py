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
    Availability, CaseResult, Finding, Owner, PlannedExam, RisRecord, Series, Status, Study,
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
    # Úkol = vlastník + kolik dní PŘED plánovaným CT musí být hotovo. Odhady, ověřit se zadavatelem
    # (kdo co dnes dělá, jak dlouho trvá prefetch a ePACS). Nejde o klinické lhůty.
    tasks: dict[Status, tuple[Owner, int]] = field(default_factory=lambda: {
        Status.ARCHIVED_PREFETCH: (Owner.RAD_ASSISTANT, 1),
        Status.INCOMPLETE_SERIES: (Owner.RAD_ASSISTANT, 1),
        Status.NEEDS_HUMAN: (Owner.CLINICIAN, 2),
        Status.EXTERNAL_REQUEST_EPACS: (Owner.RAD_ASSISTANT, 3),
        Status.MISSING_IN_PACS: (Owner.PACS_ADMIN, 2),
    })


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


def _assign_tasks(result: CaseResult, rules: Rules, today: date | None) -> None:
    """Každý nález k dořešení dostane vlastníka a termín; nestihnutelný termín se eskaluje."""
    for f in result.findings:
        if f.status not in rules.tasks:
            continue
        f.owner, lead_days = rules.tasks[f.status]
        f.due = result.planned.scheduled_date - timedelta(days=lead_days)
        f.escalate = today is not None and f.due < today


def check_case(planned: PlannedExam, pacs: PacsSource, ris: RisSource | None = None,
               rules: Rules | None = None, today: date | None = None) -> CaseResult:
    """`today` = den běhu kontroly; bez něj se nepočítá eskalace (žádné date.today() v jádře)."""
    rules = rules or Rules()
    result = CaseResult(planned)
    studies = [s for s in pacs.studies_for_patient(planned.patient_id) if s.accession != planned.accession]
    relevant = sorted((s for s in studies if is_relevant(planned, s, rules)), key=lambda s: s.study_date)

    # 1) RIS říká "provedeno", PACS nemá
    pacs_accessions = {s.accession for s in studies if s.accession}
    ris_dates: list[date] = []   # relevantní vyšetření, o kterých ví RIS (i když nejsou v PACS)
    if ris is not None:
        for rec in ris.history_for_patient(planned.patient_id):
            if rec.accession == planned.accession or rec.status != "COMPLETED":
                continue
            fake = Study("", rec.patient_id, rec.exam_date, [rec.modality], rec.description, rec.accession)
            if not is_relevant(planned, fake, rules):
                continue
            ris_dates.append(rec.exam_date)
            if rec.accession not in pacs_accessions:
                result.findings.append(Finding(
                    Status.MISSING_IN_PACS,
                    f"RIS: {rec.modality} {rec.exam_date:%d.%m.%Y} „{rec.description}“ (acc. {rec.accession}) není v PACS",
                    "Ověřit odeslání z modality / reindexaci v PACS"))

    # 2) Žádanka zmiňuje externí vyšetření, které v PACS není
    for m in extract_mentions(planned.referral_text):
        if m.internal:
            continue
        if m.negated:
            # nic se nevyžaduje, ale nález zůstane viditelný se zdrojem (extrakce může chybovat)
            result.findings.append(Finding(
                Status.OK, f"Žádanka: „{m.text}“ – podle textu neproběhlo, nevyžaduje se", source=m.text))
            continue
        if m.approx_date and m.approx_date > planned.scheduled_date:
            result.findings.append(Finding(
                Status.NEEDS_HUMAN,
                f"Žádanka: „{m.text}“ – datum je po termínu plánovaného CT",
                "Ověřit datum (překlep / teprve plánované vyšetření?)", source=m.text))
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
                f"Žádanka zmiňuje {m.modality} – {m.place_text}{when}, v PACS nenalezeno (zdroj: „{m.text}“)",
                f"Vyžádat snímky přes ePACS/ReDiMed z: {m.place_text}", source=m.text))

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
        # mezera podle nejnovějšího známého vyšetření (PACS i RIS), jinak falešný úkol pro lékaře
        gap = (planned.scheduled_date - max([latest.study_date, *ris_dates])).days
        if follow_up and gap > rules.oncology_followup_days:
            result.findings.append(Finding(
                Status.NEEDS_HUMAN,
                f"Poslední relevantní vyšetření je {gap} dní staré – chybí mezikontrola?",
                "Ověřit u pacienta/ošetřujícího, zda nebyl vyšetřen jinde"))
    elif follow_up and not any(f.status in (Status.EXTERNAL_REQUEST_EPACS, Status.MISSING_IN_PACS)
                               for f in result.findings):
        result.findings.append(Finding(
            Status.NEEDS_HUMAN,
            "Kontrolní/onkologické vyšetření, ale žádné předchozí relevantní snímky",
            "Ověřit, kde byl pacient dříve vyšetřen"))
    elif all(f.status == Status.OK for f in result.findings):
        result.findings.append(Finding(Status.NO_PRIOR_EXPECTED, "První vyšetření oblasti, nic se nečeká"))
    _assign_tasks(result, rules, today)
    return result


def check_all(planned: list[PlannedExam], pacs: PacsSource, ris: RisSource | None = None,
              rules: Rules | None = None, today: date | None = None) -> list[CaseResult]:
    results = [check_case(p, pacs, ris, rules, today) for p in planned]
    # v rámci dne napřed eskalované (termín už nestihneme), pak podle závažnosti
    return sorted(results, key=lambda r: (r.planned.scheduled_date, not r.escalate, -r.status.severity))


def planned_in_window(planned: list[PlannedExam], start: date, days: int) -> list[PlannedExam]:
    end = start + timedelta(days=days)
    return [p for p in planned if start <= p.scheduled_date <= end]
