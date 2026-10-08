"""JSON export (worklist, RIS historie, index PACS). Funguje bez Dockeru."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from ..models import Availability, PlannedExam, RisRecord, Series, Study


def _d(v: str) -> date:
    return date.fromisoformat(v)


def _default(o):
    if isinstance(o, date):
        return o.isoformat()
    if isinstance(o, Availability):
        return o.value
    raise TypeError(o)


def dump(path: Path, items: list) -> None:
    path.write_text(json.dumps([asdict(i) for i in items], default=_default, ensure_ascii=False, indent=2))


def load_worklist(path: Path) -> list[PlannedExam]:
    return [PlannedExam(**{**r, "scheduled_date": _d(r["scheduled_date"])}) for r in json.loads(path.read_text())]


def load_ris(path: Path) -> list[RisRecord]:
    return [RisRecord(**{**r, "exam_date": _d(r["exam_date"])}) for r in json.loads(path.read_text())]


def study_from_dict(r: dict) -> Study:
    series = [Series(**{**s, "availability": Availability(s["availability"])}) for s in r.get("series", [])]
    return Study(**{**r, "study_date": _d(r["study_date"]), "series": series})


class JsonPacs:
    def __init__(self, path: Path):
        self.studies = [study_from_dict(r) for r in json.loads(Path(path).read_text())]

    def studies_for_patient(self, patient_id: str) -> list[Study]:
        return [s for s in self.studies if s.patient_id == patient_id]


class JsonRis:
    def __init__(self, path: Path):
        self.records = load_ris(Path(path))

    def history_for_patient(self, patient_id: str) -> list[RisRecord]:
        return [r for r in self.records if r.patient_id == patient_id]
