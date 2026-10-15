# PACS Comparator Check – implementace a jak odpovídá zdrojům

Tento dokument nahrazuje původní `01_rakathon_2026.md`, `02_domena_pacs_dicom.md` a `03_navrh_reseni.md`.
Související: [04 – Otázky pro zadavatele](04_otazky_pro_zadavatele.md), [06 – Poznatky ze zdrojů](06_poznatky_ze_zdroju.md) (podklady pořadatele, čísla pro pitch, eHealth, právo).

Stav k 15. 10. 2026. Všech 41 testů prochází (`uv run pytest`).

---

## 1. Zadání a pravidla v kostce

**Výzva (FN Motol a Homolka):** zajistit, aby měl radiolog před plánovaným CT k dispozici všechna důležitá předchozí vyšetření. Nástroj má v PACS automaticky ověřit dostupnost relevantních snímků a sérií, chybějící podklady včas označit a připravit přehled případů k dořešení.

**Rakathon 2026:** národní AI hackathon proti rakovině, 2. ročník. Pořádá Insane Business Ideas / CEE Hacks s FN Motol, Nemocnicí Na Homolce a 2. LF UK. Praha, Brno a Ostrava, 23 výzev, týmy 2–4 lidi. Zdroje: [rakathon.cz](https://www.rakathon.cz/), [pravidla (PDF)](https://bqcunktidwhqgkjnisbp.supabase.co/storage/v1/object/public/terms/terms/1782206443390-Rakathon_2026_pravidla_a_podminky_ucasti_2_.pdf), [Luma](https://luma.com/vyf6uavq).

| Kdy | Co |
|---|---|
| čt 15. 10. | online session k nástrojům a datům (povinná) |
| **pá 16. 10. 12:00** | start hackování → těsně předtím tag `pred-hackathonem` |
| **so 17. 10. 12:00** | deadline odevzdání, 13:00 lokální pitch, 17:00 postup do finále |
| ne 18. 10. 14:00 | národní finále (2. LF UK, Plzeňská 2) |

**Ceny:** 100/50/25 tis. Kč, **InterSystems Prize** 1 500 EUR (IRIS for Health / FHIR, viz §7.2), MEDDI ONCO Award (praktický potenciál).

**Pravidla, která ovlivňují implementaci:**
| § | Pravidlo | Důsledek v kódu |
|---|---|---|
| 4 | Žádná reálná osobní data. Prototyp, ne zdravotnický prostředek. | Jen syntetická data (`synth/`), disclaimer v README a v HTML reportu, `*.dcm` v `.gitignore`. |
| 5 | Nevýhradní licence pro pořadatele. | – |
| 6 | Dodržet licence a uvést komponenty. AI nesmí zpracovávat osobní údaje. | Seznam licencí v README. LLM extraktor jen nad syntetickými texty. |
| 7 | Výstupy mohou být zveřejněny. | Podklady pořadatele (`zdroje/`) mimo git. |
| 8 | Hodnocení: relevance, inovativnost, proveditelnost, dopad, kvalita prototypu, práce s daty, UX, implementační potenciál, prezentace. | Důraz na standardy (DICOM, FHIR) = implementační potenciál. |

**Kód připravený předem** je povolen (potvrzeno 15. 10.), pokud je jasně oddělený. Postup:
1. před startem `git tag pred-hackathonem && git push origin pred-hackathonem`;
2. změny během akce průběžně commitovat (`git diff pred-hackathonem..HEAD`);
3. sekci README „Co vzniklo před akcí a co během ní“ doplnit před odevzdáním.

---

## 2. Doména stručně

### 2.1 Systémy a tok dat
```
 Onkolog (NIS) ──žádanka: HL7 v2 ORM / FHIR ServiceRequest──▶ RIS ──MWL──▶ CT modalita
                                                              ▲              │ C-STORE
                                                    HL7 ORU   │              ▼
 Radiolog ◀── prohlížeč ◀── C-MOVE / WADO ─────────────── PACS (online / nearline / offline)
                                                              ▲
                                       ePACS / ReDiMed (jiné nemocnice)
```
- **NIS** je zdroj žádanky (volný text indikace). **RIS** ví, co **mělo proběhnout** (accession, stav COMPLETED). **PACS** ví, co **reálně dorazilo** (obrazy).
- Radiolog potřebuje **komparaci**. V onkologii hodnocení odpovědi na léčbu (RECIST 1.1) potřebuje **baseline** (před léčbou), nejen poslední kontrolu.

### 2.2 Tři standardy a jejich role
| Standard | Co přenáší | Kde v projektu |
|---|---|---|
| **DICOM** | obrazy a jejich hlavičky. Dotazy: DIMSE (C-FIND, C-MOVE, MWL) a DICOMweb (QIDO-RS, WADO-RS) | vstup z PACS: `adapters/dicomweb.py`, `adapters/dimse.py` |
| **HL7 v2** | zprávy o událostech: ORM/OMI (objednávka), ORU (zpráva), SIU (termín). V nemocnicích nejrozšířenější. | zatím ne (adaptér podle dat zadavatele) |
| **FHIR R4** | záznamy (zdroje) přes REST API: `ServiceRequest`, `ImagingStudy`, `Task`, `AuditEvent`… | výstup: `fhir.py` (`Task`) |

FHIR **není databáze**, ale formát a API. **Nenahrazuje DICOM**: `ImagingStudy` na studii v PACS jen odkazuje (UID, `endpoint`). Nenese ale `InstanceAvailability`, `SliceThickness` ani kontrastní látku (ověřeno na modelech `fhir.resources` 8.3.0, R4B). Stavy `ARCHIVED_PREFETCH` a `INCOMPLETE_SERIES` proto vždy vyžadují dotaz do PACS přes DICOM.

„FHIR kompatibilní“ = správná verze (R4 4.0.1) + profil (CZ Core, HL7 Europe) + terminologie (LOINC, SNOMED CT) + **projde validací serveru** (jinak `400 OperationOutcome`).

### 2.3 DICOM tagy, se kterými pracujeme
| Úroveň | Tag | (gggg,eeee) | Poznámka |
|---|---|---|---|
| Patient | PatientID | (0010,0020) | v ČR RČ nebo interní ID. Pozor na IssuerOfPatientID. |
| Study | StudyInstanceUID | (0020,000D) | globálně unikátní, odkaz z FHIR `ImagingStudy` |
| Study | AccessionNumber | (0008,0050) | **spojka s RIS** |
| Study | StudyDate, StudyDescription | (0008,0020), (0008,1030) | popis je volný text („CT hr+bř s k.l.“) |
| Study | ModalitiesInStudy, InstitutionName | (0008,0061), (0008,0080) | instituce rozliší externí studie |
| Series | Modality, SeriesDescription | (0008,0060), (0008,103E) | „Topogram“, „Venózní fáze 1.0 mm“ |
| Series | BodyPartExamined | (0018,0015) | často prázdné nebo chybné |
| Series | SliceThickness, ContrastBolusAgent | (0018,0050), (0018,0010) | tlusté řezy, kontrast |
| Any | InstanceAvailability | (0008,0056) | ONLINE / NEARLINE / OFFLINE / UNAVAILABLE |
| MWL | RequestedProcedurePriority | (0040,1003) | STAT / HIGH / ROUTINE… |

### 2.4 Český kontext
- **ePACS** (ICZ): v roce 2020 zapojeno 140 akutních nemocnic a 105 ambulantních zařízení. V roce 2018 přeneseno přes 640 tis. studií, zhruba 4 % všech ([Bruthans 2020](https://www.thieme-connect.de/products/ejournals/abstract/10.1055/s-0040-1701252)). **ReDiMed**: druhá síť s uzlem v ÚVT MU ([srovnání, ČVUT](https://dspace.cvut.cz/handle/10467/67582)).
- Výměna napodobuje „CD workflow“: snímky se pošlou **na vyžádání**, automaticky se nedohledávají. Přidaná hodnota nástroje je vědět předem, **co** a **do kdy** vyžádat.
- Pacient se často diagnostikuje v regionu a léčí v pražském centru [FBMI 28–29], takže komparátor leží v jiném PACS.
- Budoucnost: federovaná výměna AAfD nad IHE MHD (FHIR `DocumentReference`), zprávy a snímky v EHDS od roku 2031. Detail v [06](06_poznatky_ze_zdroju.md).

---

## 3. Klíčový vhled a architektura

> Zjistit, co v PACS **je**, zvládne jeden dotaz. Těžké je poznat, co v PACS **chybí**.

Chybějící vyšetření se pozná jen tak, že ho **očekává jiný zdroj**:
1. **RIS ↔ PACS:** RIS má COMPLETED, PACS nemá obrazy.
2. **Žádanka:** volný text zmiňuje externí vyšetření („CT z Kladna 07/2026“).
3. **Onkologický rytmus:** kontrolní vyšetření, ale poslední relevantní je starší než 180 dní.
4. **Úroveň sérií:** studie existuje, ale chybí diagnostická série.
5. **Archivní vrstva:** studie je NEARLINE/OFFLINE, je potřeba prefetch.
6. *(budoucí)* **Registr AAfD:** MHD ITI-67 vrátí zprávy z jiných nemocnic.

```
 VSTUPY (adaptéry, vyměnitelné)           JÁDRO (bez FHIR i DICOM)          VÝSTUPY
 plánovaná CT: JSON | MWL (DIMSE) ─┐      normalize.py  text → oblasti      report.py  HTML/CSV worklist
 PACS: JSON | QIDO-RS | C-FIND ────┼────▶ referral.py   žádanka → zmínky ─▶ fhir.py    FHIR R4 Task Bundle
 RIS:  JSON ───────────────────────┘      checker.py    pravidla, stavy,    audit.py   JSONL (ATNA minimum)
                                                        úkoly (Rules)
```
Jádro zná jen rozhraní `PacsSource` / `RisSource` (`checker.py`) a vlastní model (`models.py`). **Na hackathonu se podle dat zadavatele píše jen adaptér.** Odpovídá doporučené architektuře z webináře [eHealth 17]: klinické UI, procesní jádro (úkol, stav, audit), FHIR adaptér na okraji, žádná fiktivní produkční integrace.

---

## 4. Moduly podrobně

### 4.1 `models.py`: datový model
| Třída | Význam |
|---|---|
| `PlannedExam` | plánované vyšetření z RIS/MWL: accession, pacient, datum, modalita, popis, **text žádanky**, `oncology`, `priority` (DICOM 0040,1003) |
| `Study`, `Series` | studie a série v PACS. `Study.availability` = nejhorší dostupnost ze sérií. |
| `RisRecord` | vyšetření, které podle RIS proběhlo |
| `Status` | 7 stavů. **Pořadí výčtu = závažnost**, `CaseResult.status` = nejhorší nález. |
| `Finding` | nález = **úkol**: `message`, `action`, `owner`, `due`, `escalate`, `source` (citace žádanky) |
| `Owner` | radiologický asistent / PACS admin / indikující lékař |
| `CaseResult` | plánované CT + vybrané komparátory + nálezy |

### 4.2 `normalize.py`: čeština → anatomické oblasti
- `fold()`: malá písmena, **bez diakritiky** (kódování je reálný problém i v nemocnicích, Orthanc bez `DEFAULT_ENCODING: Utf8` udělá z „břicha“ „bicha“), `+` oddělené mezerami.
- `REGION_PATTERNS` (HEAD, NECK, CHEST, ABDOMEN, PELVIS, SPINE) + `COMPOSITE_PATTERNS` („TAP“, „celotěl.“, „PET“, „hr+bř“) + `BODY_PART_MAP` pro DICOM BodyPartExamined.
- `regions()`: **text má přednost**, BodyPartExamined jen doplní, když text nic neřekne (BodyPart bývá prázdné nebo chybné).
- `has_contrast()` → True / False / None (nevíme). `is_localizer()` → topogram, scout, surview, dose report.

### 4.3 `referral.py`: žádanka → zmínky o předchozích vyšetřeních
- Regex `_MENTION`: **modalita** (CT, MR, PET/CT, RTG, USG) … **místo** (z/ze/v/ve/na …) … **datum** (`d. m. rrrr`, `mm/rrrr`, `m. rrrr`).
- `PriorMention`: modalita, místo, přibližné datum, oblasti, `text` = **doslovná citace z původního textu** (indexy sedí díky `_fold_same_length`), `place_text` s diakritikou pro zobrazení, `negated`.
- **Negace** jen jednoznačné výrazy („neprovedeno“, „neproběhlo“, „nebylo provedeno“, „nerealizováno“) v klauzuli hned za zmínkou. „Odmítl kontrastní látku“ ani „snímky nejsou k dispozici“ negace **nejsou**.
- `implies_oncology()` (Ca, karcinom, lymfom, meta, restaging, RECIST…), `implies_follow_up()` (kontrola, restaging, dispenzarizace, po léčbě…).
- **Slot pro LLM:** stejné rozhraní (`extract_mentions(text) -> list[PriorMention]`), vyhodnotit proti regex baseline na ručně anotovaných syntetických žádankách.

### 4.4 `checker.py`: jádro
`check_case(planned, pacs, ris, rules, today)` v krocích:

1. **Studie pacienta z PACS** (bez aktuálního accession). **Relevance** (`is_relevant`):
   - modalita v `Rules.comparable_modalities` (pro CT: CT, PT, MR),
   - studie **před** plánovaným CT a nejvýše `lookback_days` (5 let) stará,
   - **průnik oblastí** (oblasti ze StudyDescription, jinak ze sérií a BodyPart).
2. **RIS ↔ PACS:** relevantní záznam RIS se stavem COMPLETED, jehož accession v PACS není → `MISSING_IN_PACS`. Data z RIS se pamatují pro výpočet mezery (krok 4).
3. **Žádanka:** pro každou externí zmínku:
   - negovaná → `OK` se zdrojem (zůstane viditelná, nic se nevyžaduje),
   - datum **po** plánovaném CT → `NEEDS_HUMAN` (překlep, nebo teprve plánované),
   - v PACS není studie z cizí instituce v toleranci ±45 dní → `EXTERNAL_REQUEST_EPACS` s citací.
4. **Komparátory:** **poslední** relevantní a u onkologie i **baseline** (nejstarší v okně). Pro každý `_check_study`:
   - NEARLINE/OFFLINE → `ARCHIVED_PREFETCH`,
   - žádná diagnostická série (ne topogram, řez ≤ 5 mm) → `INCOMPLETE_SERIES`,
   - plánováno s k.l., komparátor jen nativní → `OK` s poznámkou (ne chyba).
   - Mezera: u kontrolního nebo onkologického vyšetření, kde je nejnovější známé vyšetření (PACS **i RIS**) starší než 180 dní → `NEEDS_HUMAN`.
   - Kontrolní vyšetření bez jakéhokoli komparátoru (a bez nálezu z kroků 2–3) → `NEEDS_HUMAN`. Jinak `NO_PRIOR_EXPECTED`.
5. **Úkoly** (`_assign_tasks`): podle `Rules.tasks` vlastník a předstih, `due = plánované CT − předstih`, `escalate = due < today`. Bez `today` se eskalace nepočítá (jádro nevolá `date.today()`, je deterministické).

`check_all` řadí podle data, pak eskalované napřed, pak podle závažnosti.

**`Rules`** (vše konfigurovatelné, hodnoty ověřit se zadavatelem, viz [04](04_otazky_pro_zadavatele.md)):
| Parametr | Hodnota | Proč |
|---|---|---|
| `comparable_modalities` | CT → CT, PT, MR | onkologické restagingy kombinují modality |
| `lookback_days` | 5 let | odhad, ověřit |
| `oncology_followup_days` | 180 | restaging bývá po 2–3 měsících, rok bez kontroly je podezřelý |
| `max_diagnostic_slice_mm` | 5.0 | tlusté řezy (8 mm) se ke komparaci hodí málo |
| `mention_date_tolerance_days` | 45 | „07/2026“ je přibližné datum |
| `tasks` | prefetch a série 1 den, NEEDS_HUMAN a RIS≠PACS 2 dny, ePACS 3 dny | **provozní odhady, ne klinické lhůty** |

### 4.5 Stavy
| Stav | Kdy | Akce | Vlastník |
|---|---|---|---|
| 🟢 `OK` | komparátor dostupný | – | – |
| ⚪ `NO_PRIOR_EXPECTED` | první vyšetření oblasti | – | – |
| 🔵 `ARCHIVED_PREFETCH` | komparátor NEARLINE/OFFLINE | prefetch (C-MOVE) na stanici | rad. asistent |
| 🟠 `INCOMPLETE_SERIES` | jen topogram / tlusté řezy | dohledat rekonstrukce | rad. asistent |
| 🟡 `NEEDS_HUMAN` | podezřelá mezera, kontrola bez komparátoru, datum po CT | ověřit u pacienta nebo klinika | indikující lékař |
| 🔴 `EXTERNAL_REQUEST_EPACS` | žádanka zmiňuje externí vyšetření, v PACS není | vyžádat přes ePACS/ReDiMed | rad. asistent |
| 🟣 `MISSING_IN_PACS` | RIS: provedeno, PACS: nic | ověřit odeslání z modality nebo reindexaci | PACS admin |

### 4.6 Adaptéry
| Adaptér | Protokol | Poznámka |
|---|---|---|
| `json_files.py` | JSON export | běh bez Dockeru, společný formát pro neznámá data |
| `dicomweb.py` `DicomWebPacs` | QIDO-RS `GET /studies?PatientID=`, `/studies/{uid}/series` | DICOM JSON s hex klíči tagů |
| `dicomweb.py` `OrthancPacs` | + Orthanc REST (štítky) | Orthanc vrací InstanceAvailability vždy ONLINE, archiv se proto **simuluje štítkem** série |
| `dimse.py` `DimsePacs` | C-FIND Study Root (STUDY → SERIES) + **MWL C-FIND** | `pynetdicom`. Plný text žádanky z `RequestedProcedureComments` (Reason má max. 64 znaků). |

### 4.7 Výstupy
- `report.py`: konzole, CSV a HTML worklist (barvy podle stavu, vlastník, termín, „TERMÍN NESTIHNUTELNÝ“).
- `fhir.py`: každý nález závažnější než `NO_PRIOR_EXPECTED` → FHIR R4 `Task`:
  - `status=requested`, `intent=order`,
  - `code` = náš stav (`urn:pacs-check:finding-status`, standardní ValueSet neexistuje),
  - `focus` = `ServiceRequest` přes accession, `for` = `Patient` přes identifikátor,
  - `owner`, `restriction.period.end` = termín, `note` = akce, `input` = StudyInstanceUID a citace žádanky.
  - Priorita: STAT → `stat`, HIGH → `urgent`, eskalace u rutinních → `asap`.
  - Obálka je Bundle typu `collection`.
- `audit.py`: JSONL řádek za běh (čas, uživatel, zdroj, **účel**, okno, pacienti), minimum ve smyslu IHE ATNA a zákona 372/2011.

### 4.8 Syntetická data (`synth/generate.py`)
13 scénářů relativně k referenčnímu datu (`meta.json`). Výstupy: `worklist.json`, `ris.json`, `pacs.json`, `dicom/*.dcm` (hlavičky bez pixelů, UTF-8) a `worklists/*.wl` (MWL pro Orthanc).

| # | Scénář | Očekávaný stav |
|---|---|---|
| 1 | onkologie, poslední + baseline online | OK |
| 2 | lymfom, baseline OFFLINE | ARCHIVED_PREFETCH |
| 3 | jen topogram + 8 mm | INCOMPLETE_SERIES |
| 4 | Ca pankreatu, CT z Kladna, CT za 2 dny (ePACS potřebuje 3) | EXTERNAL_REQUEST_EPACS + eskalace |
| 5 | RIS má CT před 40 dny, PACS ne | MISSING_IN_PACS |
| 6 | Ca prsu, poslední kontrola před 420 dny | NEEDS_HUMAN |
| 7 | první CT hlavy, předchozí jen břicho a RTG kolene | NO_PRIOR_EXPECTED |
| 8 | externí MR z Homolky už v PACS | OK |
| 9 | prázdný BodyPart, oblast ze zkratky „TAP“ | OK |
| 10 | komparátor nativní, plánováno s k.l. | OK (poznámka) |
| 11 | žádanka: CT z Kladna „neprovedeno“ | NO_PRIOR_EXPECTED (zmínka viditelná) |
| 12 | fast track Ca plic, „snímky nejsou k dispozici“, priorita HIGH | EXTERNAL_REQUEST_EPACS, termín zítra |
| 13 | zmínka s datem po plánovaném CT | NEEDS_HUMAN |

---

## 5. Testy: jak implementace odpovídá zdrojům

Zkratky zdrojů: **[Zadání]** text výzvy · **[FBMI n]** Tichopád, *Analýza cesty onkologického pacienta*, slide n · **[eHealth n]** Opatřil, *České eHealth v kostce* · **[HL7 n]** HL7 ČR, úvod pro týmy · **[DICOM]** standard DICOM PS3.4/PS3.6 · **[FHIR R4]** hl7.org/fhir/R4 · **[Pravidla §n]**. Podrobnosti ke zdrojům jsou v [06](06_poznatky_ze_zdroju.md).

Testy: `tests/test_scenarios.py` (S), `tests/test_referral.py` (R), `tests/test_normalize.py` (N), `tests/test_fhir.py` (F).

### 5.1 Požadavky zadání
| Požadavek | Zdroj | Implementace | Test |
|---|---|---|---|
| Ověřit dostupnost relevantních snímků **a sérií** | [Zadání] | `is_relevant`, `diagnostic_series`, `_check_study` | S `test_scenario_status[PLAN001-OK]`, `[PLAN003-INCOMPLETE_SERIES]` |
| Dostupnost = i archivní vrstva | [Zadání], [DICOM] InstanceAvailability (0008,0056) | `Study.availability`, `ARCHIVED_PREFETCH` | S `[PLAN002-ARCHIVED_PREFETCH]` |
| **Chybějící** podklady označit | [Zadání] | kroky 2–4 v `check_case` | S `[PLAN004-…]`, `[PLAN005-MISSING_IN_PACS]`, `[PLAN006-NEEDS_HUMAN]` |
| **Včas**: přehled před vyšetřením | [Zadání] | `planned_in_window`, `due`, `escalate` | S `test_tasks_have_owner_due_and_escalation` |
| Přehled případů k dořešení | [Zadání] | `report.py`, řazení v `check_all` | – (ruční kontrola `reports/report.html`) |
| Každý stav je pokryt scénářem | – | `Status` | S `test_all_statuses_covered` |
| Nerelevantní vyšetření (jiná oblast, RTG) se nepočítá | doména (komparace = stejná oblast) | `is_relevant` | S `[PLAN007-NO_PRIOR_EXPECTED]` |

### 5.2 Koordinace péče [FBMI]
| Princip | Zdroj | Implementace | Test |
|---|---|---|---|
| Úkol = vlastník + termín + eskalace | [FBMI 20] | `Finding.owner/due/escalate`, `Rules.tasks` | S `test_tasks_have_owner_due_and_escalation` (PLAN004: termín uplynul → eskalace; PLAN012: termín zítra → bez eskalace) |
| Klinická rozhodnutí u lékaře, logistika u asistenta | [FBMI 20] | `NEEDS_HUMAN` → `CLINICIAN`, ePACS a prefetch → `RAD_ASSISTANT` | S `test_tasks_have_owner_due_and_escalation` (`Owner.RAD_ASSISTANT`) |
| Fast track Ca plic: CT do týdne, max. 14 dní | [FBMI 32] | `PlannedExam.priority` → `Task.priority=urgent` | S `[PLAN012-…]`, F `test_bundle_has_valid_r4_tasks` (PLAN012 `urgent`) |
| Onkologie potřebuje baseline i poslední | [HL7 13] („počáteční stadium není současný stav“), RECIST 1.1 | krok 4, `comparators` | S `test_oncology_gets_baseline_and_latest` |
| Žádné falešné úkoly (falešná upozornění sledovat) | [FBMI 44] | mezera počítaná i z data v RIS | S `test_gap_uses_ris_date` |

### 5.3 AI/extrakce: zdroj, nejistota, člověk [FBMI 49–50], [eHealth 19], [HL7 21]
| Princip | Zdroj | Implementace | Test |
|---|---|---|---|
| Zachovat **původ tvrzení** (citace) | [FBMI 49], [HL7 21] | `PriorMention.text`, `Finding.source`, FHIR `Task.input` | R `test_citation_keeps_original_text`, `test_place_keeps_diacritics_for_display`; S `test_tasks_have_owner_due_and_escalation` (`"Kladno" in source`) |
| Typická chyba: **negace** | [FBMI 50] | `_NOT_DONE` v klauzuli za zmínkou | R `test_negation_only_when_exam_did_not_happen` (4 varianty) |
| Negativní výsledek nesmí případ tiše uzavřít | [FBMI 44] | negovaná zmínka → `OK` nález se zdrojem | S `test_negated_mention_stays_visible`, `[PLAN011-NO_PRIOR_EXPECTED]` |
| Typická chyba: **špatné datum** | [FBMI 50] | datum po CT → `NEEDS_HUMAN` | S `[PLAN013-NEEDS_HUMAN]` |
| „Snímky nejsou k dispozici“ **není** negace | [FBMI 50] (vynechání) | úzký seznam negací | R `test_negation_…` (2. případ), S `[PLAN012-EXTERNAL_REQUEST_EPACS]` |
| Rozlišovat známé a chybějící údaje | [HL7 21] | `NO_PRIOR_EXPECTED` vs. `NEEDS_HUMAN` vs. chybí | S `[PLAN007-…]`, `[PLAN006-…]` |
| Extrakce zmínek: modalita, místo, datum | [Zadání], ePACS praxe | `_MENTION` | R `test_external_ct_mention`, `test_full_date_and_pet`, `test_no_mention` |
| Interní vs. externí pracoviště | ePACS jen pro cizí PACS | `INTERNAL_PLACES`, `_is_home` | R `test_full_date_and_pet` (Motol = interní); S `[PLAN008-OK]` (Homolka už v PACS) |
| Onkologie a kontrola z textu | [FBMI], [HL7] | `implies_oncology`, `implies_follow_up` | R `test_flags` |

### 5.4 Data a terminologie (DICOM, čeština)
| Problém | Zdroj | Implementace | Test |
|---|---|---|---|
| České zkratky („hr+bř“, „TAP“, „celotěl.“) | doména (popisy studií jsou volný text) | `normalize.regions` | N `test_regions_from_czech_text` (7 případů) |
| BodyPartExamined prázdné nebo chybné | [DICOM] (0018,0015), praxe | text má přednost, BodyPart jen záloha | N `test_body_part_only_as_fallback`; S `[PLAN009-OK]` |
| Topogram není diagnostická série | doména | `is_localizer` | N `test_localizer`; S `[PLAN003-…]` |
| Kontrast: nativní komparátor není chyba | doména | `has_contrast`, poznámka `OK` | N `test_contrast`; S `[PLAN010-OK]` |
| Kódování znaků (UTF-8) | praxe, Orthanc | `fold()` bez diakritiky, `ISO_IR 192` v generátoru | N `test_regions_from_czech_text` („CT BRICHA NATIV“) |

### 5.5 Standardy a interoperabilita
| Požadavek | Zdroj | Implementace | Test |
|---|---|---|---|
| FHIR na okraji, jádro o FHIR neví | [eHealth 17] | jen `fhir.py` importuje FHIR | strukturálně (jádro nemá FHIR import) |
| R4 `Task`: povinné `status`, `intent`, platná `priority` | [FHIR R4] Task | `finding_to_task` | F `test_bundle_has_valid_r4_tasks`; **server: 7/7 přijato** (§6) |
| Eskalace → `asap` | [FBMI 20] + [FHIR R4] request-priority | `_priority` | F `test_bundle_has_valid_r4_tasks` (PLAN004) |
| Deterministické jádro (bez `date.today()`) | testovatelnost, audit | `today` parametr | S `test_no_escalation_without_reference_date` |
| Audit přístupu | [eHealth 12, 16], zákon 372/2011 | `audit.py` | **chybí test** |
| Dotazy DICOMweb / DIMSE / MWL | [DICOM] | adaptéry | **chybí automatický test**, ověřeno ručně proti Orthancu (§6) |

---

## 6. Ručně ověřeno proti běžícím serverům (15. 10. 2026)

**Orthanc** (`docker compose up -d`, `uv run pacs-check upload`):
- `GET /dicom-web/studies?PatientID=SYN002` vrací DICOM JSON (hex klíče, `vr`), dvě studie po třech sériích. Baseline z 04/2024 má série se štítkem OFFLINE.
- `InstanceAvailability` na úrovni studie Orthanc hlásí vždy `ONLINE` → potvrzuje nutnost simulace štítky.
- `uv run pacs-check run --source dicomweb` dává stejné stavy jako běh nad JSON (13/13).
- `--source dimse --worklist mwl` se liší jen u PLAN002: `OK` místo `ARCHIVED_PREFETCH`. Přes C-FIND Orthanc štítky archivu nevidí, takže jde o limit simulace, ne o chybu jádra (§7.1).

**FHIR server InterSystems IRIS for Health Community** ([FHIR-AI-Hackathon-Kit](https://github.com/intersystems-community/FHIR-AI-Hackathon-Kit), `http://localhost:52773/fhir/r4`, SuperUser/SYS):
- `GET /metadata` → `fhirVersion 4.0.1`.
- `POST /ServiceRequest` (status, intent, priority, subject, occurrence) → `201`, dohledatelný přes `?patient=…&status=active`.
- Chybný `ServiceRequest` → `400 OperationOutcome`: chybí `status`, `priority` musí být `asap|routine|stat|urgent`.
- **Všech 7 `Task` z `reports/tasks.fhir.json` přijato jednotlivě (`POST /Task` → 201)**, dohledatelné `GET /Task?code=urn:pacs-check:finding-status|EXTERNAL_REQUEST_EPACS`.
- Celý Bundle typu `collection` na base URL → `400 InvalidBundleTypeForTransaction`. Pro hromadný zápis je potřeba Bundle typu `transaction` s `request` u každé položky.
- Na Linuxu kit spadne (`Unable to find/open file iris-main.log`), protože kontejner nemůže zapisovat do připojené složky. Oprava: `chmod o+w docker-iris-fhir`.

Validace na serveru je **základní R4**, ne CZ Core ani evropský profil.

---

## 7. Limity a další kroky

### 7.1 Známé limity
- Archivní vrstva v Orthancu jen simulovaná (štítky, čte jen `OrthancPacs`, přes DIMSE se neprojeví). U reálného PACS stačí standardní tag.
- FHIR `Task` odkazuje na `Patient`/`ServiceRequest` jen identifikátorem (logická reference), ne na existující zdroj na serveru.
- Kódy stavů jsou vlastní (`urn:pacs-check:…`). Standardní ValueSet pro tento účel neexistuje.
- Identita pacienta mezi nemocnicemi (RČ vs. interní ID) neřešena → IHE PIX/PDQm.
- Regexy na žádanky pokrývají jen typické formulace.

### 7.2 Priority během hackathonu
1. **Adaptér na data zadavatele** (formát zjistit, viz [04](04_otazky_pro_zadavatele.md)). Pravděpodobně HL7 v2 (ORM/ORU) nebo export z RIS. Knihovny `hl7apy` / `python-hl7`.
2. **FHIR plně na serveru** (InterSystems Prize):
   - `Task` stavět přes `fhir.resources` a posílat jako **transaction** Bundle,
   - odkazy na skutečné `Patient`/`ServiceRequest`,
   - FHIR adaptér pro vstup (`ServiceRequest?status=active`, `ImagingStudy?patient=`),
   - test validace proti IRIS.
3. **LLM extraktor žádanek** se stejným rozhraním jako `extract_mentions`, jen nad syntetickými texty [Pravidla §6], vyhodnotit proti regex baseline.
4. **Akce místo reportu:** prefetch přes Orthanc `/modalities/{id}/move` (C-MOVE), předvyplněná ePACS žádost, stav úkolu (požádáno → přijato → snímky dorazily).
5. **Relevance přes kódy:** LOINC/RSNA Radiology Playbook a SNOMED CT místo regexů (regexy zůstanou pro český volný text).
6. **MHD stub (AAfD):** ITI-67 vrací `DocumentReference` z jiných nemocnic. Šestý zdroj očekávání, prezentovat jen jako stub [eHealth 17].
7. **Metriky pro pitch:** kolik případů z X zachytí, falešná upozornění, ušetřený čas.

### 7.3 Užitečná data a nástroje
- **Orthanc** (mini-PACS v Dockeru), **pydicom**, **pynetdicom**, CLI **dcmtk** / **dcm4che** (`findscu`, `movescu`).
- **IRIS for Health FHIR server** (kit výše) a knihovny `fhir.resources` (pydantic modely, v8 má R5 a podbalík R4B) a `fhirpy` (klient).
- **[SYNDERAI](https://synderai.net/)** (HL7 Europe, AGPL-3.0): syntetická data FHIR R4 s evropskými profily (Patient Summary, Discharge Report, Lab). Je v nich asi 25 pacientů z Czechia a kolem 30 onkologických diagnóz. **Žádné** `ImagingStudy` ani DICOM, zobrazovací vyšetření jen jako `Procedure` (CT TAP 6×). Hodí se jako vzor evropského FHIR a onkologický kontext, ne pro stranu PACS.
- **[TCIA](https://www.cancerimagingarchive.net/)** (reálné anonymizované onkologické CT), **[SIIM hackathon dataset](https://github.com/ImagingInformatics/hackathon-dataset)** (FHIR + DICOM vignety).

---

## 8. Slovníček
| Pojem | Význam |
|---|---|
| Komparace / komparátor / prior | srovnání s předchozím vyšetřením / to předchozí vyšetření |
| Baseline, nadir | výchozí vyšetření před léčbou / nejmenší naměřený nádor (RECIST) |
| Accession number | číslo žádanky ve RIS, spojka RIS ↔ PACS |
| Prefetch | přesun snímků z pomalého archivu předem (C-MOVE) |
| MWL | Modality Worklist, plánovaná vyšetření pro přístroj |
| Topogram / scout | přehledový snímek pro plánování, ke srovnání nepoužitelný |
| k.l. / nativ / fáze | kontrastní látka / bez k.l. / arteriální, venózní, pozdní |
| Restaging, dispenzarizace | přešetření rozsahu nádoru po léčbě / pravidelné sledování |
| KOC / ROC, MDT | komplexní / regionální onkologické centrum, multidisciplinární tým |
| Fast track | zrychlená cesta při podezření na nádor |
| ePACS / ReDiMed | české sítě pro výměnu snímků mezi nemocnicemi |
| Resource, Bundle, OperationOutcome | FHIR zdroj („formulář“), obálka více zdrojů, odpověď „co je špatně“ |
| Profil | národní nebo oborové zpřesnění FHIR zdroje (CZ Core, HL7 Europe) |
| IHE | „kuchařky“ pro skládání standardů (SWF, XDS-I, MHD, ATNA, PIX/PDQ) |
| AAfD, EHDS | navrhovaná česká federovaná výměnná síť, Evropský prostor pro zdravotní data |
