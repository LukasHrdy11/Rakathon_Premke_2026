"""DICOMweb QIDO-RS adaptér (Orthanc, dcm4chee, většina moderních PACS/VNA)."""

from __future__ import annotations

from datetime import date

import httpx

from ..models import Availability, Series, Study

# DICOM tagy jako hex klíče v DICOM JSON
T = {
    "StudyInstanceUID": "0020000D", "StudyDate": "00080020", "StudyDescription": "00081030",
    "AccessionNumber": "00080050", "PatientID": "00100020", "ModalitiesInStudy": "00080061",
    "InstitutionName": "00080080", "SeriesInstanceUID": "0020000E", "Modality": "00080060",
    "SeriesDescription": "0008103E", "BodyPartExamined": "00180015", "SliceThickness": "00180050",
    "ContrastBolusAgent": "00180010", "NumberOfSeriesRelatedInstances": "00201209",
    "InstanceAvailability": "00080056",
}


def _v(ds: dict, name: str, default=""):
    vals = ds.get(T[name], {}).get("Value")
    return vals[0] if vals else default


def _date(s: str) -> date:
    return date(int(s[:4]), int(s[4:6]), int(s[6:8]))


class DicomWebPacs:
    def __init__(self, base_url: str = "http://localhost:8042/dicom-web", auth: tuple[str, str] | None = None):
        self.client = httpx.Client(base_url=base_url, auth=auth, timeout=30,
                                   headers={"Accept": "application/dicom+json"})

    def _get(self, path: str, params: dict) -> list[dict]:
        r = self.client.get(path, params=params)
        r.raise_for_status()
        return r.json() if r.content else []

    def studies_for_patient(self, patient_id: str) -> list[Study]:
        studies = []
        for ds in self._get("/studies", {"PatientID": patient_id, "includefield": "StudyDescription,InstitutionName"}):
            uid = _v(ds, "StudyInstanceUID")
            mods = ds.get(T["ModalitiesInStudy"], {}).get("Value", [])
            series = [self._series(s) for s in self._get(
                f"/studies/{uid}/series",
                {"includefield": "BodyPartExamined,SliceThickness,ContrastBolusAgent,InstanceAvailability"})]
            studies.append(Study(
                study_uid=uid, patient_id=patient_id, study_date=_date(_v(ds, "StudyDate")),
                modalities=mods, description=_v(ds, "StudyDescription"),
                accession=_v(ds, "AccessionNumber"), institution=_v(ds, "InstitutionName"), series=series))
        return studies

    @staticmethod
    def _series(ds: dict) -> Series:
        thick = _v(ds, "SliceThickness", None)
        avail = _v(ds, "InstanceAvailability", "ONLINE") or "ONLINE"
        return Series(
            series_uid=_v(ds, "SeriesInstanceUID"), modality=_v(ds, "Modality"),
            description=_v(ds, "SeriesDescription"), body_part=_v(ds, "BodyPartExamined"),
            slice_thickness=float(thick) if thick not in (None, "") else None,
            contrast_agent=_v(ds, "ContrastBolusAgent"),
            n_instances=int(_v(ds, "NumberOfSeriesRelatedInstances", 0) or 0),
            availability=Availability(avail))


class OrthancPacs(DicomWebPacs):
    """Orthanc vrací InstanceAvailability vždy ONLINE. Archivní vrstvu (NEARLINE/OFFLINE)
    proto simulujeme štítkem (label) na sérii – nastaví ho `pacs-check upload`.
    U skutečného PACS tohle není potřeba, stačí DicomWebPacs."""

    def __init__(self, orthanc_url: str = "http://localhost:8042"):
        super().__init__(orthanc_url.rstrip("/") + "/dicom-web")
        self.rest = httpx.Client(base_url=orthanc_url, timeout=30)

    def studies_for_patient(self, patient_id: str) -> list[Study]:
        studies = super().studies_for_patient(patient_id)
        for st in studies:
            for se in st.series:
                hits = self.rest.post("/tools/lookup", content=se.series_uid).json()
                for h in (h for h in hits if h["Type"] == "Series"):
                    labels = self.rest.get(f"/series/{h['ID']}/labels").json()
                    for a in (Availability.OFFLINE, Availability.NEARLINE):
                        if a.value in labels:
                            se.availability = a
        return studies
