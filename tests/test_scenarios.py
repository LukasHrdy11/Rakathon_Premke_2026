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
