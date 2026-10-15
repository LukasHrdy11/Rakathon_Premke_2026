"""End-to-end nad syntetickými scénáři: každý scénář musí dát očekávaný stav."""
from datetime import date

import pytest

from pacs_check.checker import check_case
from pacs_check.synth.generate import build_scenarios

TODAY = date(2026, 10, 8)
SCENARIOS = build_scenarios(TODAY)


class _Pacs:
    def __init__(self, studies):
        self.studies = studies

    def studies_for_patient(self, pid):
        return [s for s in self.studies if s.patient_id == pid]


class _Ris:
    def __init__(self, records):
        self.records = records

    def history_for_patient(self, pid):
        return [r for r in self.records if r.patient_id == pid]


PACS = _Pacs([st for s in SCENARIOS for st in s.priors])
RIS = _Ris([r for s in SCENARIOS for r in s.ris])


@pytest.mark.parametrize("sc", SCENARIOS, ids=lambda s: f"{s.planned.accession}-{s.expected}")
def test_scenario_status(sc):
    assert check_case(sc.planned, PACS, RIS).status.value == sc.expected


def test_all_statuses_covered():
    from pacs_check.models import Status
    assert {s.expected for s in SCENARIOS} == {s.value for s in Status}


def test_oncology_gets_baseline_and_latest():
    sc = SCENARIOS[0]
    res = check_case(sc.planned, PACS, RIS)
    assert [c.study_date for c in res.comparators] == sorted(st.study_date for st in sc.priors)


def test_tasks_have_owner_due_and_escalation():
    from pacs_check.models import Owner, Status
    by_acc = {s.planned.accession: s for s in SCENARIOS}
    ext = check_case(by_acc["PLAN004"].planned, PACS, RIS, today=TODAY)   # CT za 2 dny, ePACS potřebuje 3
    f = next(f for f in ext.findings if f.status == Status.EXTERNAL_REQUEST_EPACS)
    assert f.owner == Owner.RAD_ASSISTANT and f.due < TODAY and ext.escalate
    fast = check_case(by_acc["PLAN012"].planned, PACS, RIS, today=TODAY)  # CT za 4 dny -> termín zítra
    assert not fast.escalate and fast.findings[0].due > TODAY
    assert "Kladno" in fast.findings[0].source


def test_gap_uses_ris_date():
    """PLAN005: RIS ví o CT před 40 dny (v PACS chybí) -> žádný falešný úkol 'chybí mezikontrola'."""
    from pacs_check.models import Status
    sc = next(s for s in SCENARIOS if s.planned.accession == "PLAN005")
    assert all(f.status != Status.NEEDS_HUMAN for f in check_case(sc.planned, PACS, RIS).findings)


def test_no_escalation_without_reference_date():
    assert not any(check_case(s.planned, PACS, RIS).escalate for s in SCENARIOS)


def test_negated_mention_stays_visible():
    sc = next(s for s in SCENARIOS if s.planned.accession == "PLAN011")
    res = check_case(sc.planned, PACS, RIS)
    assert any("neproběhlo" in f.message and f.source for f in res.findings)
