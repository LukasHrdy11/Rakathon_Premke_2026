"""CLI: `pacs-check generate | upload | run`."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import httpx

from .adapters.json_files import JsonPacs, JsonRis, load_worklist
from .checker import check_all, planned_in_window
from .report import to_console, to_csv, to_html

DATA = Path("data/generated")


def cmd_generate(a):
    from .synth.generate import generate
    sc = generate(Path(a.out), date.fromisoformat(a.today) if a.today else None)
    print(f"Vygenerováno {len(sc)} scénářů do {a.out}")


def cmd_upload(a):
    import pydicom
    files = sorted(Path(a.data, "dicom").glob("*.dcm"))
    with httpx.Client(base_url=a.orthanc, timeout=30) as c:
        # generate tvoří pokaždé nová UID -> nejdřív smazat staré syntetické pacienty
        old = c.post("/tools/find", json={"Level": "Patient", "Query": {"PatientID": "SYN*"}}).json()
        for pid in old:
            c.delete(f"/patients/{pid}").raise_for_status()
        for f in files:
            r = c.post("/instances", content=f.read_bytes())
            r.raise_for_status()
            # simulace archivní vrstvy štítkem (Orthanc InstanceAvailability neukládá)
            avail = pydicom.dcmread(f, stop_before_pixels=True).get("InstanceAvailability", "ONLINE")
            if avail != "ONLINE":
                c.put(f"/series/{r.json()['ParentSeries']}/labels/{avail}").raise_for_status()
    print(f"Nahráno {len(files)} instancí do {a.orthanc}")


def _reference_date(data: Path) -> date:
    """Referenční datum, ke kterému byla data vygenerována (jinak dnes)."""
    meta = data / "meta.json"
    if meta.exists():
        return date.fromisoformat(json.loads(meta.read_text())["today"])
    return date.today()


def cmd_run(a):
    data = Path(a.data)
    if a.source == "dimse":
        from .adapters.dimse import DimsePacs
        pacs = DimsePacs(a.dimse_host, a.dimse_port, a.dimse_aet)
        planned = pacs.worklist("CT") if a.worklist == "mwl" else load_worklist(data / "worklist.json")
    else:
        if a.source == "dicomweb":
            from .adapters.dicomweb import OrthancPacs
            pacs = OrthancPacs(a.orthanc)
        else:
            pacs = JsonPacs(data / "pacs.json")
        planned = load_worklist(data / "worklist.json")
    ris = JsonRis(data / "ris.json") if (data / "ris.json").exists() else None
    start = date.fromisoformat(a.today) if a.today else _reference_date(data)
    results = check_all(planned_in_window(planned, start, a.days), pacs, ris)
    print(to_console(results))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    to_csv(results, out / "report.csv")
    to_html(results, out / "report.html")
    print(f"\nReport: {out / 'report.html'}  |  {out / 'report.csv'}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pacs-check")
    sub = ap.add_subparsers(required=True)

    g = sub.add_parser("generate", help="vygenerovat syntetické scénáře")
    g.add_argument("--out", default=str(DATA))
    g.add_argument("--today", help="referenční datum YYYY-MM-DD (default dnes)")
    g.set_defaults(fn=cmd_generate)

    u = sub.add_parser("upload", help="nahrát syntetické DICOM do Orthancu")
    u.add_argument("--data", default=str(DATA))
    u.add_argument("--orthanc", default="http://localhost:8042")
    u.set_defaults(fn=cmd_upload)

    r = sub.add_parser("run", help="spustit kontrolu a vytvořit report")
    r.add_argument("--source", choices=["json", "dicomweb", "dimse"], default="json")
    r.add_argument("--worklist", choices=["json", "mwl"], default="json")
    r.add_argument("--data", default=str(DATA))
    r.add_argument("--orthanc", default="http://localhost:8042")
    r.add_argument("--dimse-host", default="localhost")
    r.add_argument("--dimse-port", type=int, default=4242)
    r.add_argument("--dimse-aet", default="ORTHANC")
    r.add_argument("--today", help="začátek okna YYYY-MM-DD (default dnes)")
    r.add_argument("--days", type=int, default=7, help="kolik dní dopředu kontrolovat")
    r.add_argument("--out", default="reports")
    r.set_defaults(fn=cmd_run)

    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
