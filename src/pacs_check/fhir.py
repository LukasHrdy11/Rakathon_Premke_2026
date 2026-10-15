"""Export nálezů k dořešení jako FHIR R4 `Task` (Bundle typu collection).

FHIR jen na okraji systému: jádro (checker) o FHIR neví, tady se jen mapuje CaseResult -> Task.
Ilustrativní základní R4, NE český profil (CZ Core / HIE IG) – před integrací ověřit profil,
terminologii a validátorem (OperationOutcome). Viz docs/06_poznatky_ze_zdroju.md.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from .models import OWNER_LABEL_CS, STATUS_LABEL_CS, CaseResult, Finding, Status

SYSTEM_STATUS = "urn:pacs-check:finding-status"   # vlastní kódy stavů (žádný standardní ValueSet neexistuje)
SYSTEM_ACCESSION = "urn:pacs-check:accession"     # v nemocnici: systém accession čísel RIS
SYSTEM_PATIENT = "urn:pacs-check:patient-id"      # v nemocnici: interní ID / RČ s IssuerOfPatientID

# RequestedProcedurePriority (DICOM) -> Task.priority (routine | urgent | asap | stat)
_PRIORITY = {"STAT": "stat", "HIGH": "urgent"}


def _priority(case: CaseResult, f: Finding) -> str:
    p = _PRIORITY.get(case.planned.priority.upper(), "routine")
    return "asap" if f.escalate and p == "routine" else p


def finding_to_task(case: CaseResult, f: Finding, authored: datetime) -> dict:
    p = case.planned
    task: dict = {
        "resourceType": "Task",
        "status": "requested",
        "intent": "order",
        "priority": _priority(case, f),
        "code": {"coding": [{"system": SYSTEM_STATUS, "code": f.status.value,
                             "display": STATUS_LABEL_CS[f.status]}]},
        "description": f.message,
        "focus": {"type": "ServiceRequest", "identifier": {"system": SYSTEM_ACCESSION, "value": p.accession}},
        "for": {"type": "Patient", "identifier": {"system": SYSTEM_PATIENT, "value": p.patient_id}},
        "authoredOn": authored.isoformat(timespec="seconds"),
    }
    if f.owner.value:
        task["owner"] = {"display": OWNER_LABEL_CS[f.owner]}
    if f.due:
        task["restriction"] = {"period": {"end": f.due.isoformat()}}
    if f.action:
        task["note"] = [{"text": f.action}]
    inputs = []
    if f.study_uid:
        inputs.append({"type": {"text": "ImagingStudy"},
                       "valueIdentifier": {"system": "urn:dicom:uid", "value": f"urn:oid:{f.study_uid}"}})
    if f.source:
        inputs.append({"type": {"text": "Zdroj (citace žádanky)"}, "valueString": f.source})
    if inputs:
        task["input"] = inputs
    return task


def to_bundle(results: list[CaseResult], authored: datetime | None = None) -> dict:
    authored = authored or datetime.now().astimezone()
    tasks = [finding_to_task(r, f, authored) for r in results for f in r.findings
             if f.status.severity > Status.NO_PRIOR_EXPECTED.severity]
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "timestamp": authored.isoformat(timespec="seconds"),
        "entry": [{"fullUrl": f"urn:uuid:{uuid.uuid4()}", "resource": t} for t in tasks],
    }


def write_bundle(results: list[CaseResult], path: Path) -> None:
    path.write_text(json.dumps(to_bundle(results), ensure_ascii=False, indent=2), encoding="utf-8")
