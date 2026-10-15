"""Klasický DICOM DIMSE: C-FIND (Study Root Q/R) a Modality Worklist. Vyžaduje `uv sync --extra dimse`.

Většina nemocničních PACS podporuje DIMSE vždy, DICOMweb ne vždy.
"""

from __future__ import annotations

from datetime import date

from pydicom.dataset import Dataset

from ..models import Availability, PlannedExam, Series, Study
from ..referral import implies_oncology


def _date(s: str) -> date:
    return date(int(s[:4]), int(s[4:6]), int(s[6:8]))


class DimsePacs:
    def __init__(self, host="localhost", port=4242, called_aet="ORTHANC", calling_aet="PACSCHECK"):
        from pynetdicom import AE
        from pynetdicom.sop_class import ModalityWorklistInformationFind, StudyRootQueryRetrieveInformationModelFind
        self.ae = AE(ae_title=calling_aet)
        self.ae.add_requested_context(StudyRootQueryRetrieveInformationModelFind)
        self.ae.add_requested_context(ModalityWorklistInformationFind)
        self._qr = StudyRootQueryRetrieveInformationModelFind
        self._mwl = ModalityWorklistInformationFind
        self.addr = (host, port, called_aet)

    def _find(self, query: Dataset, model) -> list[Dataset]:
        host, port, aet = self.addr
        assoc = self.ae.associate(host, port, ae_title=aet)
        if not assoc.is_established:
            raise ConnectionError(f"Asociace s {aet}@{host}:{port} selhala")
        try:
            out = []
            for status, ds in assoc.send_c_find(query, model):
                if not status:
                    raise ConnectionError("C-FIND: žádná odpověď (timeout / přerušená asociace)")
                if status.Status in (0xFF00, 0xFF01):
                    out.append(ds)
                elif status.Status != 0x0000:
                    raise RuntimeError(f"C-FIND selhal se stavem 0x{status.Status:04X}")
            return out
        finally:
            assoc.release()

    def studies_for_patient(self, patient_id: str) -> list[Study]:
        q = Dataset()
        q.QueryRetrieveLevel = "STUDY"
        q.PatientID = patient_id
        for k in ("StudyInstanceUID", "StudyDate", "StudyDescription", "AccessionNumber",
                  "ModalitiesInStudy", "InstitutionName"):
            setattr(q, k, "")
        studies = []
        for ds in self._find(q, self._qr):
            sq = Dataset()
            sq.QueryRetrieveLevel = "SERIES"
            sq.StudyInstanceUID = ds.StudyInstanceUID
            for k in ("SeriesInstanceUID", "Modality", "SeriesDescription", "BodyPartExamined",
                      "SliceThickness", "ContrastBolusAgent", "NumberOfSeriesRelatedInstances",
                      "InstanceAvailability"):
                setattr(sq, k, "")
            series = [Series(
                series_uid=s.SeriesInstanceUID, modality=s.get("Modality", ""),
                description=s.get("SeriesDescription", ""), body_part=s.get("BodyPartExamined", ""),
                slice_thickness=float(s.SliceThickness) if s.get("SliceThickness") else None,
                contrast_agent=s.get("ContrastBolusAgent", ""),
                n_instances=int(s.get("NumberOfSeriesRelatedInstances") or 0),
                availability=Availability(s.get("InstanceAvailability") or "ONLINE"),
            ) for s in self._find(sq, self._qr)]
            mods = ds.get("ModalitiesInStudy", [])
            studies.append(Study(
                study_uid=ds.StudyInstanceUID, patient_id=patient_id, study_date=_date(ds.StudyDate),
                modalities=[mods] if isinstance(mods, str) else list(mods),
                description=ds.get("StudyDescription", ""), accession=ds.get("AccessionNumber", ""),
                institution=ds.get("InstitutionName", ""), series=series))
        return studies

    def worklist(self, modality: str = "CT") -> list[PlannedExam]:
        q = Dataset()
        q.PatientID = q.PatientName = q.AccessionNumber = q.RequestedProcedureDescription = ""
        q.ReasonForTheRequestedProcedure = q.RequestedProcedureComments = ""
        q.RequestedProcedurePriority = ""
        sps = Dataset()
        sps.Modality = modality
        sps.ScheduledProcedureStepStartDate = ""
        sps.ScheduledProcedureStepDescription = ""
        q.ScheduledProcedureStepSequence = [sps]
        out = []
        for ds in self._find(q, self._mwl):
            step = ds.ScheduledProcedureStepSequence[0]
            # plný text žádanky; Reason (LO) má max. 64 znaků
            reason = ds.get("RequestedProcedureComments", "") or ds.get("ReasonForTheRequestedProcedure", "")
            out.append(PlannedExam(
                accession=ds.AccessionNumber, patient_id=ds.PatientID, patient_name=str(ds.PatientName),
                scheduled_date=_date(step.ScheduledProcedureStepStartDate), modality=step.Modality,
                description=ds.get("RequestedProcedureDescription", "") or step.get("ScheduledProcedureStepDescription", ""),
                referral_text=reason, oncology=implies_oncology(reason),
                priority=ds.get("RequestedProcedurePriority", "") or "ROUTINE"))
        return out
