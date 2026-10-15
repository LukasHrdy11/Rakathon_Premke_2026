"""FHIR export: povinná pole R4 Task a mapování priority/termínu."""
from datetime import date

from pacs_check.checker import check_all
from pacs_check.fhir import to_bundle
from test_scenarios import PACS, RIS, SCENARIOS, TODAY


def test_bundle_has_valid_r4_tasks():
    results = check_all([s.planned for s in SCENARIOS], PACS, RIS, today=TODAY)
    tasks = [e["resource"] for e in to_bundle(results)["entry"]]
    assert tasks and all(t["status"] == "requested" and t["intent"] == "order" for t in tasks)
    assert all(t["priority"] in {"routine", "urgent", "asap", "stat"} for t in tasks)
    assert {t["code"]["coding"][0]["code"] for t in tasks} >= {"EXTERNAL_REQUEST_EPACS", "MISSING_IN_PACS"}
    fast = next(t for t in tasks if t["focus"]["identifier"]["value"] == "PLAN012")
    assert fast["priority"] == "urgent" and date.fromisoformat(fast["restriction"]["period"]["end"]) > TODAY
    escalated = next(t for t in tasks if t["focus"]["identifier"]["value"] == "PLAN004")
    assert escalated["priority"] == "asap"
