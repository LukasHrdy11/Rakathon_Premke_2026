"""Datový model nezávislý na zdroji dat (PACS, RIS, export CSV/JSON)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class Availability(str, Enum):
    """Odpovídá DICOM tagu InstanceAvailability (0008,0056)."""

    ONLINE = "ONLINE"
    NEARLINE = "NEARLINE"
    OFFLINE = "OFFLINE"
    UNAVAILABLE = "UNAVAILABLE"


class Status(str, Enum):
    """Výsledek kontroly. Pořadí = závažnost (poslední je nejhorší)."""

    OK = "OK"
    NO_PRIOR_EXPECTED = "NO_PRIOR_EXPECTED"
    ARCHIVED_PREFETCH = "ARCHIVED_PREFETCH"
    INCOMPLETE_SERIES = "INCOMPLETE_SERIES"
    NEEDS_HUMAN = "NEEDS_HUMAN"
    EXTERNAL_REQUEST_EPACS = "EXTERNAL_REQUEST_EPACS"
    MISSING_IN_PACS = "MISSING_IN_PACS"

    @property
    def severity(self) -> int:
        return list(Status).index(self)


STATUS_LABEL_CS = {
    Status.OK: "V pořádku",
    Status.NO_PRIOR_EXPECTED: "Bez předchozího vyšetření (očekávaně)",
    Status.ARCHIVED_PREFETCH: "Nutný prefetch z archivu",
    Status.INCOMPLETE_SERIES: "Neúplné série",
    Status.NEEDS_HUMAN: "Ověřit ručně",
    Status.EXTERNAL_REQUEST_EPACS: "Vyžádat z jiného pracoviště (ePACS)",
    Status.MISSING_IN_PACS: "Chybí v PACS (v RIS provedeno)",
}


@dataclass
class Series:
    series_uid: str
    modality: str
    description: str = ""
    body_part: str = ""
    slice_thickness: float | None = None
    contrast_agent: str = ""
    n_instances: int = 0
    availability: Availability = Availability.ONLINE


@dataclass
class Study:
    """Studie nalezená v PACS."""

    study_uid: str
    patient_id: str
    study_date: date
    modalities: list[str]
    description: str = ""
    accession: str = ""
    institution: str = ""
    series: list[Series] = field(default_factory=list)

    @property
    def availability(self) -> Availability:
        if not self.series:
            return Availability.ONLINE
        order = list(Availability)
        return max((s.availability for s in self.series), key=order.index)


@dataclass
class PlannedExam:
    """Plánované vyšetření (z RIS / Modality Worklist)."""

    accession: str
    patient_id: str
    patient_name: str
    scheduled_date: date
    modality: str
    description: str
    referral_text: str = ""
    oncology: bool = False


@dataclass
class RisRecord:
    """Historický záznam v RIS – vyšetření, které podle RIS proběhlo."""

    accession: str
    patient_id: str
    exam_date: date
    modality: str
    description: str
    institution: str = ""
    status: str = "COMPLETED"


@dataclass
class Finding:
    status: Status
    message: str
    action: str = ""
    study_uid: str = ""


@dataclass
class CaseResult:
    planned: PlannedExam
    comparators: list[Study] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    @property
    def status(self) -> Status:
        if not self.findings:
            return Status.OK
        return max((f.status for f in self.findings), key=lambda s: s.severity)
