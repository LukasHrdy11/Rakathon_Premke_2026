"""Výstupy: konzole, CSV a HTML přehled případů k dořešení."""

from __future__ import annotations

import csv
import html
from datetime import datetime
from pathlib import Path

from .models import STATUS_LABEL_CS, CaseResult, Status

COLORS = {
    Status.OK: "#2e7d32", Status.NO_PRIOR_EXPECTED: "#607d8b", Status.ARCHIVED_PREFETCH: "#0277bd",
    Status.INCOMPLETE_SERIES: "#ef6c00", Status.NEEDS_HUMAN: "#f9a825",
    Status.EXTERNAL_REQUEST_EPACS: "#c62828", Status.MISSING_IN_PACS: "#6a1b9a",
}


def to_console(results: list[CaseResult]) -> str:
    lines = []
    for r in results:
        p = r.planned
        lines.append(f"{p.scheduled_date:%d.%m.} {p.accession} {p.patient_id} {p.description:<38} -> {r.status.value}")
        for f in r.findings:
            if f.status != Status.OK or len(r.findings) == 1:
                lines.append(f"      [{f.status.value}] {f.message}" + (f"  => {f.action}" if f.action else ""))
    return "\n".join(lines)


def to_csv(results: list[CaseResult], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["datum", "accession", "pacient_id", "vysetreni", "stav", "nalez", "akce"])
        for r in results:
            for f in r.findings:
                w.writerow([r.planned.scheduled_date.isoformat(), r.planned.accession, r.planned.patient_id,
                            r.planned.description, f.status.value, f.message, f.action])


def to_html(results: list[CaseResult], path: Path) -> None:
    e = html.escape
    todo = [r for r in results if r.status.severity > Status.NO_PRIOR_EXPECTED.severity]
    counts = {s: sum(r.status == s for r in results) for s in Status}
    chips = "".join(
        f'<span class="chip" style="background:{COLORS[s]}">{e(STATUS_LABEL_CS[s])}: {n}</span>'
        for s, n in counts.items() if n)
    rows = []
    for r in results:
        p = r.planned
        items = "".join(
            f'<li><b style="color:{COLORS[f.status]}">{e(STATUS_LABEL_CS[f.status])}</b> – {e(f.message)}'
            + (f'<br><i>→ {e(f.action)}</i>' if f.action else "") + "</li>"
            for f in r.findings)
        rows.append(
            f'<tr><td>{p.scheduled_date:%d.%m.%Y}</td><td>{e(p.accession)}<br><small>{e(p.patient_id)}</small></td>'
            f'<td>{e(p.description)}<br><small>{e(p.referral_text)}</small></td>'
            f'<td><span class="chip" style="background:{COLORS[r.status]}">{e(STATUS_LABEL_CS[r.status])}</span></td>'
            f'<td><ul>{items}</ul></td></tr>')
    path.write_text(f"""<!doctype html><html lang="cs"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>PACS Comparator Check</title>
<style>
body{{font-family:system-ui,sans-serif;margin:16px;background:#fafafa;color:#222}}
table{{border-collapse:collapse;width:100%;background:#fff}} td,th{{border-bottom:1px solid #ddd;padding:8px;vertical-align:top;text-align:left}}
.chip{{color:#fff;border-radius:12px;padding:2px 10px;margin:2px;display:inline-block;font-size:13px}}
ul{{margin:0;padding-left:18px}} small{{color:#666}}
</style></head><body>
<h1>PACS Comparator Check</h1>
<p>Vygenerováno {datetime.now():%d.%m.%Y %H:%M} · plánovaných CT: {len(results)} · k dořešení: <b>{len(todo)}</b></p>
<p>{chips}</p>
<table><tr><th>Termín</th><th>Žádanka</th><th>Vyšetření / indikace</th><th>Stav</th><th>Nálezy a akce</th></tr>
{''.join(rows)}</table>
<p><small>Syntetická data · prototyp z Rakathonu 2026, není zdravotnický prostředek.</small></p>
</body></html>""", encoding="utf-8")
