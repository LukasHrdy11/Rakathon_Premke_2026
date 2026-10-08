# PACS Comparator Check – Rakathon 2026 (Praha)

> **Výzva (FN Motol a Homolka):** Zajistěte, aby měl radiolog před plánovaným CT k dispozici všechna důležitá předchozí vyšetření. Vytvořte nástroj, který v systému PACS automaticky ověří dostupnost relevantních snímků a obrazových sérií. Chybějící podklady včas označí a připraví přehled případů, které je potřeba před vyšetřením dořešit.

Repozitář je **příprava před hackathonem** (16.–18. 10. 2026): rešerše, doménové znalosti, lokální PACS v Dockeru, syntetická data a funkční prototyp jádra.

⚠️ Pravidla předpřipravený kód výslovně neřeší. Ověřit na online session 15. 10. (viz [docs/01](docs/01_rakathon_2026.md)).
⚠️ Prototyp, **ne zdravotnický prostředek**. Pouze **syntetická data**, žádná reálná data pacientů.

## Dokumentace
| | |
|---|---|
| [01 – Rakathon 2026](docs/01_rakathon_2026.md) | harmonogram, pravidla, ceny, co z pravidel plyne |
| [02 – Doména PACS/DICOM](docs/02_domena_pacs_dicom.md) | RIS vs PACS, DICOM tagy, DIMSE/DICOMweb/MWL, ePACS, slovníček |
| [03 – Návrh řešení](docs/03_navrh_reseni.md) | klíčový vhled, architektura, stavy, roadmapa, rizika |
| [04 – Otázky pro zadavatele](docs/04_otazky_pro_zadavatele.md) | co zjistit 15. 10. / v pátek ráno |
| [05 – Plán hackathonu](docs/05_plan_hackathonu.md) | příprava, 24h plán, role, kostra pitche, checklist |

## Rychlý start
```bash
uv sync --extra dimse                  # závislosti (pydicom, httpx, pynetdicom, pytest)
uv run pacs-check generate             # syntetické scénáře -> data/generated/
uv run pacs-check run                  # kontrola nad JSON (bez Dockeru) -> reports/report.html
uv run pytest                          # testy

# s lokálním PACS (Orthanc): UI na http://localhost:8042
# POZOR: nejdřív `generate`, pak `docker compose up` (jinak Docker vytvoří data/generated/worklists jako root)
docker compose up -d
uv run pacs-check upload               # nahraje syntetické DICOM hlavičky
uv run pacs-check run --source dicomweb               # QIDO-RS
uv run pacs-check run --source dimse --worklist mwl   # C-FIND + Modality Worklist
```
`run` kontroluje plánovaná CT na 7 dní dopředu od data, ke kterému se generovalo (`data/generated/meta.json`). Jinak lze zadat `--today` a `--days`. `upload` před nahráním smaže staré syntetické pacienty (`SYN*`).

## Co prototyp umí
Pro každé plánované CT najde relevantní předchozí vyšetření (poslední a u onkologie i baseline) a přidělí stav:

| Stav | Kdy |
|---|---|
| 🟢 `OK` | komparátor dostupný |
| ⚪ `NO_PRIOR_EXPECTED` | první vyšetření oblasti |
| 🔵 `ARCHIVED_PREFETCH` | komparátor v NEARLINE/OFFLINE archivu |
| 🟠 `INCOMPLETE_SERIES` | jen topogram / tlusté řezy |
| 🟡 `NEEDS_HUMAN` | podezřelá mezera v onkologickém sledování |
| 🔴 `EXTERNAL_REQUEST_EPACS` | žádanka zmiňuje externí vyšetření, které v PACS není |
| 🟣 `MISSING_IN_PACS` | RIS: provedeno, PACS: nic |

Syntetická sada (`src/pacs_check/synth/generate.py`) má 10 pacientů a pokrývá všechny stavy. Obsahuje české zkratky („CT hr+bř s k.l.“, „TAP“), prázdný BodyPartExamined a externí MR z Homolky.

## Struktura
```
src/pacs_check/
  models.py        datový model (PlannedExam, Study, Series, RisRecord, Status…)
  normalize.py     český volný text -> anatomické oblasti, kontrast, topogram
  referral.py      žádanka -> zmínky o předchozích vyšetřeních (regex; slot pro LLM)
  checker.py       jádro: relevance, výběr komparátorů, stavy  (Rules = konfigurace)
  report.py        konzole, CSV, HTML worklist
  cli.py           pacs-check generate | upload | run
  adapters/        json_files (export), dicomweb (QIDO-RS, Orthanc), dimse (C-FIND, MWL)
  synth/           generátor syntetických scénářů + DICOM + MWL souborů
docker-compose.yml Orthanc (DICOMweb, MWL, C-FIND)
```

## Použité komponenty a licence (pravidla §6)
Orthanc (GPLv3) + DICOMweb plugin (AGPLv3), oba běží jako samostatná služba v Dockeru a nejsou součástí našeho kódu, pydicom (MIT), pynetdicom (MIT), httpx (BSD-3), pytest (MIT).

## Zdroje
- [rakathon.cz](https://www.rakathon.cz/) · [Pravidla a podmínky účasti (PDF)](https://bqcunktidwhqgkjnisbp.supabase.co/storage/v1/object/public/terms/terms/1782206443390-Rakathon_2026_pravidla_a_podminky_ucasti_2_.pdf) · [Luma](https://luma.com/vyf6uavq)
- [Bruthans 2020: ePACS v ČR (Applied Clinical Informatics)](https://www.thieme-connect.de/products/ejournals/abstract/10.1055/s-0040-1701252) · [ČVUT: ePACS vs ReDiMed](https://dspace.cvut.cz/handle/10467/67582)
- [Orthanc docker docs](https://orthanc.uclouvain.be/book/users/docker-orthancteam.html) · [SIIM hackathon dataset](https://github.com/ImagingInformatics/hackathon-dataset) · [TCIA](https://www.cancerimagingarchive.net/)
