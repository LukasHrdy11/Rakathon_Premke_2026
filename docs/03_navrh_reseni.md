# Návrh řešení

## Problém jednou větou
Radiolog otevře plánované CT a zjistí, že předchozí vyšetření chybí, je v archivu nebo leží v jiné nemocnici. Komparace pak buď chybí, nebo se čeká.
**Cíl:** pár dní předem projít plánovaná CT, ke každému najít relevantní předchozí vyšetření a vyřešit dostupnost dřív, než pacient přijde.

## Klíčový vhled (pro pitch)
> Zjistit, co v PACS **je**, zvládne jeden dotaz. Těžké je poznat, co v PACS **chybí**.

Chybějící vyšetření se dá poznat jen tak, že ho **očekává jiný zdroj**:
1. **RIS ↔ PACS**: RIS má vyšetření jako provedené, PACS nemá obrazy.
2. **Žádanka**: volný text zmiňuje externí vyšetření („CT z Kladna 07/2026“). Tady se hodí NLP nebo LLM.
3. **Onkologický rytmus**: restaging bývá po 2–3 měsících. Když je poslední kontrola starší než rok, je mezera podezřelá.
4. **Úroveň sérií**: studie existuje, ale chybí diagnostická série (jen topogram nebo 8mm řezy).
5. **Archivní vrstva**: vyšetření je v PACS, ale NEARLINE/OFFLINE, takže je potřeba prefetch.

## Architektura
```
 ┌─────────────┐   ┌──────────────┐   ┌────────────────────┐
 │ Plánovaná CT│   │ PACS dotazy  │   │ RIS historie       │   ← adaptéry (vyměnitelné podle dat)
 │ MWL / JSON  │   │ DICOMweb /   │   │ JSON / HL7 / FHIR  │
 │ / HL7 / FHIR│   │ DIMSE / JSON │   │                    │
 └──────┬──────┘   └──────┬───────┘   └─────────┬──────────┘
        └─────────────────┼─────────────────────┘
                    ┌─────▼──────┐   normalize.py (čeština, zkratky → oblasti)
                    │  checker   │   referral.py  (žádanka → zmínky o vyšetřeních)  [LLM slot]
                    │  (pravidla)│   Rules        (okno, modality, interval kontrol)
                    └─────┬──────┘
                    ┌─────▼──────┐
                    │  report    │   HTML worklist „k dořešení“, CSV, (e-mail/RIS flag/FHIR Task)
                    └────────────┘
```
Jádro (`checker.py`) nezná zdroj dat. **Na hackathonu se podle dat od zadavatele píše jen adaptér.**

Odpovídá doporučené architektuře z webináře k českému eHealth ([docs/06](06_poznatky_ze_zdroju.md)):
- klinické UI = `report.py` (worklist)
- procesní jádro (úkol, stav, audit) = `checker.py` + `audit.py`
- FHIR adaptér na okraji = `fhir.py` (`Task`)
- HIE/API stub = zatím chybí (MHD ITI-67, viz roadmapa)

Každý nález je **úkol s vlastníkem, termínem a eskalací** (`Rules.tasks`). Předstihy jsou provozní odhady, ne klinické lhůty.

## Stavy (výstup pro každé plánované CT)
| Stav | Význam | Akce |
|---|---|---|
| `OK` | komparátor dostupný online | – |
| `NO_PRIOR_EXPECTED` | první vyšetření oblasti, nic se nečeká | – |
| `ARCHIVED_PREFETCH` | komparátor je NEARLINE/OFFLINE | spustit prefetch (C-MOVE) na stanici |
| `INCOMPLETE_SERIES` | jen topogram nebo tlusté řezy | dohledat rekonstrukce |
| `NEEDS_HUMAN` | podezřelá mezera, kontrola bez předchozího vyšetření | ověřit u pacienta nebo klinika |
| `EXTERNAL_REQUEST_EPACS` | žádanka zmiňuje externí vyšetření, které v PACS není | vyžádat přes ePACS/ReDiMed |
| `MISSING_IN_PACS` | RIS: provedeno, PACS: nic | IT/PACS admin: ověřit odeslání |

## Relevance předchozího vyšetření (MVP pravidla)
- Modalita: pro plánované CT se počítá CT, PET/CT a MR (konfigurovatelné v `Rules`).
- Oblast: průnik anatomických oblastí z popisu studie. Když popis nic neřekne, použijí se popisy sérií a BodyPartExamined.
- Časové okno: 5 let. Bere se **poslední** relevantní vyšetření a u onkologie i **baseline** (nejstarší v okně).
- Série: aspoň jedna diagnostická (ne topogram, řez ≤ 5 mm).
- Kontrast: nativní komparátor k plánovanému CT s k.l. je jen poznámka, ne chyba.

## Kam dál během hackathonu (priority)
1. **Adaptér na reálná data** od zadavatele (formát zjistit 15. 10.).
2. **LLM extraktor žádanek a zpráv**: stejné rozhraní jako `referral.extract_mentions`, vrací strukturované `PriorMention`. Lokální model nebo Claude API **jen nad syntetickými/anonymizovanými texty** (pravidla §6). Prompt: „vypiš všechna zmíněná předchozí zobrazovací vyšetření: modalita, oblast, místo, datum“. Vyhodnotit na sadě ručně anotovaných žádanek proti regex baseline.
3. **Relevance přes standardní kódy**: mapování popisů na LOINC/RSNA Radiology Playbook (RPID) místo regexů. Plus učení z historie, které komparace radiologové skutečně otevírali (pokud má PACS audit log).
4. **Akce, ne jen report**: tlačítko „prefetch“ (C-MOVE přes Orthanc `/modalities/{x}/move`) a předvyplněná ePACS žádost.
5. **Integrace do workflow**: denní běh (cron) v 6:00 na D+1…D+3, výstup do RIS jako flag nebo FHIR `Task` (export už je v `fhir.py`), e-mail pro radiologického asistenta.
   **Stav úkolu** (požádáno → přijato → snímky dorazily): odeslaná ePACS žádost ještě neznamená, že snímky jsou na místě.
5b. **MHD stub (budoucí AAfD)**:
   - Simulovaný registr odpoví na ITI-67 `DocumentReference` zprávami z obrazových vyšetření z jiných nemocnic.
   - Je to šestý zdroj „očekávání“: najde i externí CT, které žádanka nezmiňuje.
   - Prezentovat jen jako stub, ne jako produkční integraci.
6. **Metriky pro pitch**: kolik případů z X by systém zachytil, odhad ušetřeného času, méně neúplných popisů.

## Rizika a jak je zmírnit
- **Neznámý formát dat** → adaptéry a JSON jako společný formát.
- **Žádný přístup k reálnému PACS** (pravděpodobné) → Orthanc a syntetická data. Prezentovat jako „připojitelné přes DICOMweb/DIMSE“.
- **Falešně pozitivní nálezy** zahltí asistenty → stavy seřadit podle závažnosti, `NEEDS_HUMAN` jen tam, kde má smysl.
- **Regulace (MDR)**: nástroj nedělá diagnózu, jen logistiku dat. To je silný argument pro implementovatelnost.
- **Identita pacienta** mezi nemocnicemi (rodné číslo vs. interní ID) → zmínit jako známý limit (IHE PIX/PDQ).

## Známé limity simulace v Orthancu
- Orthanc vrací `InstanceAvailability` vždy ONLINE. Archivní vrstvu proto simulujeme štítkem (label) na sérii a čte ji jen `OrthancPacs` (DICOMweb + REST). Přes DIMSE se v Orthancu neprojeví. U reálného PACS stačí standardní tag.
- `ORTHANC__DEFAULT_ENCODING: Utf8` je nutné, jinak se z „břicha“ stane „bicha“. **Kódování znaků je reálný problém i v nemocnicích**, proto `normalize.fold()` odstraňuje diakritiku.
