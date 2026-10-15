"""Auditní záznam běhu: kdo, kdy, z jakého zdroje, za jakým účelem a čí data četl.

Minimum v duchu IHE ATNA / zákona 372/2011 (záznam přístupu). Bez RBAC – v prototypu jeden uživatel.
"""

from __future__ import annotations

import getpass
import json
from datetime import date, datetime
from pathlib import Path

PURPOSE = "Příprava komparací před plánovaným CT (zajištění návaznosti péče)"


def append_audit(path: Path, source: str, start: date, days: int, patient_ids: list[str]) -> None:
    entry = {
        "time": datetime.now().astimezone().isoformat(timespec="seconds"),
        "user": getpass.getuser(),
        "action": "query",
        "source": source,
        "purpose": PURPOSE,
        "window": {"start": start.isoformat(), "days": days},
        "patients": sorted(set(patient_ids)),
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
