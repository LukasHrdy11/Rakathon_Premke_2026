# Plán: příprava, 24 hodin hackování, pitch

## Před akcí (do čt 15. 10.)
- [ ] Projít `docs/02_domena_pacs_dicom.md` a rozběhnout prototyp (README → Rychlý start).
- [ ] Zkusit `pacs-check generate` → `docker compose up -d` → `pacs-check upload` → `run --source dicomweb` na notebooku, se kterým pojedu.
- [ ] Mít stažené Docker image (`docker compose pull`), na místě může být pomalá Wi-Fi.
- [ ] Sestavit tým: ideálně **radiolog / radiologický asistent / medik** + backend + frontend/UX + někdo na pitch a data.
- [ ] 15. 10.: online session, ptát se podle `docs/04_otazky_pro_zadavatele.md`.
- [ ] Ujasnit, zda smí být použit předpřipravený kód (viz `docs/01_rakathon_2026.md`).
- [ ] Nachystat si API klíč k LLM (pokud bude povoleno) a ověřit limity.

## Role v týmu (3–4 lidi)
| Role | Zodpovědnost |
|---|---|
| Backend / integrace | adaptér na data zadavatele, checker, akce (prefetch) |
| NLP / LLM | extrakce z žádanek a zpráv, vyhodnocení proti regex baseline |
| UI / UX | worklist „k dořešení“ pro asistenta, detail případu |
| Klinik / pitch | validace pravidel relevance, příběh pacienta, prezentace |

## 24 hodin (pá 12:00 → so 12:00)
| Čas | Co | Výstup |
|---|---|---|
| pá 12–14 | rozhovor se zadavatelem a mentory, upřesnění pravidel, formát dat | vyplněné otázky, scope |
| 14–18 | adaptér na jejich data, úprava `Rules`, nové syntetické scénáře podle jejich příkladů | end-to-end běh na jejich datech |
| 18–22 | hlavní „wow“ feature (LLM extrakce žádanek, nebo akce prefetch/ePACS) | demo funkce |
| 22–02 | UI worklist (HTML nebo Streamlit), metriky | použitelný výstup |
| 02–06 | spánek ve směnách (!) | |
| 06–09 | stabilizace, testy, demo data, screenshoty | **zamrazit funkce v 9:00** |
| 09–11 | prezentace, demo video jako záloha pro případ, že živé demo selže | slidy + video |
| 11–12 | odevzdání (README, repo, slidy) | **odevzdáno do 12:00** |
| 13:00 | pitch | |

## Kostra pitche (3–5 min, podle kritérií §8)
1. **Příběh** (relevance, dopad): „Pacientka s ca prsu, restaging. Radiolog otevře CT a chybí baseline z jiné nemocnice. Popis je bez srovnání, nebo se odkládá.“
2. **Problém v číslech**: kolik CT denně, jak často chybí komparace (od zadavatele). Kontext z podkladů pořadatele ([docs/06](06_poznatky_ze_zdroju.md)):
   - Do 4 týdnů od bronchoskopie zahájí léčbu jen 21–31 % pacientů s ca plic.
   - Praha léčí 1 011 pacientů s ca plic, bydlí v ní ale jen 674. Diagnostika proběhne v regionu, snímky jsou jinde.
   - Každé 4 týdny odkladu léčby jsou asociovány s vyšší mortalitou (Hanna, BMJ 2020; asociace, ne individuální efekt).
3. **Vhled**: co chybí, pozná jen ten, kdo ví, co čekat (RIS, žádanka, onkologický rytmus).
4. **Demo** (kvalita prototypu, UX): worklist na zítřek, barvy stavů, konkrétní akce.
5. **Jak to funguje** (proveditelnost, práce s daty): standardy DICOMweb/DIMSE/MWL/HL7/FHIR, IHE SWF, napojení na ePACS.
6. **Implementace** (potenciál): běží vedle PACS, jen čte data, nediagnostikuje, takže nízké regulatorní riziko. Pilot na jedné CT lince.
7. **Další kroky**: LLM nad zprávami, učení z audit logu, Motol ↔ Homolka.

## „Minimum pro uvěřitelné MVP“ (webinář eHealth, slide 20) → kde to máme
| Bod | V projektu |
|---|---|
| 1. Klinická potřeba a odpovědná role | komparace před CT; úkoly mají vlastníka (`Rules.tasks`), klinická rozhodnutí má lékař |
| 2. Zdroj pravdy a identifikátory | PACS (obrazy), RIS (provedeno), accession number a PatientID. Limit: identita napříč nemocnicemi (PDQm/PIXm) |
| 3. Konkrétní FHIR/IHE profil | `Task` (R4, ilustrativní), DICOMweb/DIMSE/MWL, IHE SWF; další krok MHD ITI-67 |
| 4. Pravidla přístupu a audit | `audit.jsonl` (kdo, kdy, účel, pacienti), jen metadata bez pixelů. RBAC zatím ne |
| 5. Syntetická data a test chyb | 13 scénářů včetně negace, chybného data a nestihnutelného termínu; `pytest` |

## Checklist odevzdání
- [ ] README s popisem, spuštěním, architekturou a seznamem použitých komponent a licencí (§6).
- [ ] Žádná reálná data v repu (§4). Disclaimer „není zdravotnický prostředek“.
- [ ] Slidy a demo video.
- [ ] Jasně oddělit, co vzniklo před akcí a co během ní.
