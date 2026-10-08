# Doménový tahák: PACS, RIS, DICOM

## Systémy v nemocnici a tok dat
```
 Klinik (onkolog)                    RIS (Radiologický IS)                 Modalita (CT)
 ─────────────────                   ─────────────────────                 ─────────────
 NIS: žádanka  ──HL7 ORM / FHIR──▶   objednání, termín, accession  ──MWL──▶ pracovní seznam
                                     stav vyšetření, popis (zpráva)        nasnímá studii
                                                ▲                               │ C-STORE
                                                │ HL7 ORU (zpráva)              ▼
 Radiolog ◀── prohlížeč (viewer) ◀── C-MOVE/WADO ── PACS / VNA (archiv obrazů) ◀┘
                                                       ▲          │ online / nearline / offline úložiště
                       ePACS / ReDiMed (jiné nemocnice)┘          └ prefetch = přesun z archivu na rychlé úložiště
```
- **NIS/HIS**: nemocniční informační systém. Odtud přichází žádanka (indikace = volný text).
- **RIS**: plánování a evidence radiologických vyšetření. Ví, **co mělo proběhnout** (accession number, stav COMPLETED).
- **PACS** (Picture Archiving and Communication System): ví, **co reálně dorazilo** (obrazy). **VNA** = vendor-neutral archive.
- **Modalita**: CT/MR/PET přístroj. Pracovní seznam si stahuje z RIS přes **Modality Worklist (MWL)**.
- **Radiolog** při popisu potřebuje **komparaci** (srovnání s předchozím vyšetřením), jinak nepozná progresi/regresi. V onkologii jde o hodnocení odpovědi na léčbu podle **RECIST 1.1**, které potřebuje **baseline** (vyšetření před léčbou) a **nadir** (nejmenší naměřený nádor), ne jen poslední kontrolu.

## Proč komparace chybí (to řešíme)
| Příčina | Jak ji poznat | Akce |
|---|---|---|
| Vyšetření bylo v jiné nemocnici | zmínka v žádance, zpráva v NIS, údaj od pacienta | vyžádat přes **ePACS / ReDiMed** |
| Je v PACS, ale v pomalém archivu | `InstanceAvailability` = NEARLINE/OFFLINE | **prefetch** (C-MOVE) předem |
| RIS má COMPLETED, PACS nemá obrazy | rozdíl RIS vs. PACS podle accession | ověřit odeslání z modality, reindexaci |
| Studie je, ale bez potřebných sérií | jen topogram, tlusté řezy, chybí fáze | dohledat rekonstrukce |
| Jiný PatientID (cizinec, novorozenec, sloučení) | demografická shoda bez shody ID | merge v PACS / ruční ověření |
| Popis/BodyPart je nekonzistentní | zkratky „hr+bř“, „TAP“, prázdný BodyPartExamined | normalizace textu (RadLex/LOINC) |

## DICOM – hierarchie a klíčové tagy
`Patient → Study → Series → Instance (snímek)`

| Úroveň | Tag | (gggg,eeee) | Poznámka |
|---|---|---|---|
| Patient | PatientID | (0010,0020) | v ČR často rodné číslo nebo interní ID. Pozor na **IssuerOfPatientID** u více nemocnic |
| Patient | PatientName, PatientBirthDate | (0010,0010), (0010,0030) | |
| Study | StudyInstanceUID | (0020,000D) | globálně unikátní |
| Study | AccessionNumber | (0008,0050) | **spojka s RIS** |
| Study | StudyDate | (0008,0020) | |
| Study | StudyDescription | (0008,1030) | volný text, „CT hr+bř s k.l.“ |
| Study | ModalitiesInStudy | (0008,0061) | jen v dotazech |
| Study | InstitutionName | (0008,0080) | kde se snímalo, rozliší externí studie |
| Series | Modality | (0008,0060) | CT, MR, PT, CR, US… |
| Series | SeriesDescription | (0008,103E) | „Venózní fáze 1.0 mm“, „Topogram“ |
| Series | BodyPartExamined | (0018,0015) | **často prázdné nebo chybné** |
| Series | SliceThickness | (0018,0050) | tlusté řezy (≥5 mm) se ke komparaci hodí málo |
| Series | ContrastBolusAgent | (0018,0010) | kontrastní látka |
| Any | InstanceAvailability | (0008,0056) | ONLINE / NEARLINE / OFFLINE / UNAVAILABLE |

## Protokoly – jak se ptát PACS
### DIMSE (klasický DICOM, port 104/11112, „AE Title“)
- **C-ECHO**: ping. **C-FIND**: dotaz (Patient/Study/Series level). **C-MOVE / C-GET**: stažení nebo přesun (= prefetch). **C-STORE**: uložení.
- **MWL C-FIND**: dotaz na plánovaná vyšetření (Scheduled Procedure Step).
- Potřebuje registraci našeho AE Title v PACS (IP, port, AET). Nemocnice to musí povolit.
- Python: `pynetdicom`. Implementace: `src/pacs_check/adapters/dimse.py`.

### DICOMweb (REST, moderní PACS/VNA)
- **QIDO-RS** = dotaz: `GET /studies?PatientID=X&StudyDate=20250101-`, `GET /studies/{uid}/series`
- **WADO-RS** = stažení: `GET /studies/{uid}/series/{uid}/metadata`
- **STOW-RS** = uložení: `POST /studies`
- Implementace: `src/pacs_check/adapters/dicomweb.py`.

### HL7 v2 / FHIR (objednávky a zprávy)
- HL7 v2 **ORM^O01 / OMI** (objednávka), **ORU^R01** (zpráva), **SIU** (termíny).
- FHIR: `ServiceRequest` (žádanka), `ImagingStudy` (studie v PACS), `DiagnosticReport` (zpráva), `Appointment`. Hodí se pro InterSystems cenu.

### IHE profily (pro pitch: řešení zapadá do standardů)
- **SWF / SWF.b** (Scheduled Workflow): objednávka → MWL → snímání → archiv.
- **XDS-I.b**: sdílení obrazů napříč institucemi.
- **PIR** (Patient Information Reconciliation): opravy identit pacienta.
- Automatický prefetch předchozích studií je běžná funkce komerčních PACS. Zda a jak ho konkrétně popisuje IHE (SWF, případně Radiology TF), **ověřit před pitchem** v IHE Radiology Technical Framework.

## Český kontext
- **ePACS** (ICZ): decentralizovaná síť pro výměnu DICOM mezi nemocnicemi. Podle studie z roku 2020 je zapojeno všech 140 akutních nemocnic a 105 ambulantních zařízení. V roce 2018 přeneseno přes 640 tisíc studií, zhruba 4 % všech. Zdroj: [Bruthans 2020, ACI](https://www.thieme-connect.de/products/ejournals/abstract/10.1055/s-0040-1701252).
- **ReDiMed**: druhá síť, centrální uzel ÚVT MU Brno, šifrování a podpis. Srovnání obou sítí: [ČVUT DP Kadeřábek](https://dspace.cvut.cz/handle/10467/67582).
- Výměna stále napodobuje CD workflow: data se pošlou na vyžádání, automaticky se nedohledávají. **Tady je přidaná hodnota**: vědět předem, co vyžádat.
- Motol a Homolka jsou dvě samostatné nemocnice. Zjistit, zda sdílejí PACS (viz otázky).
- Rodné číslo jako PatientID: pozor na GDPR. V prototypu pseudonymizovat.

## Nástroje
- **Orthanc**: open-source mini-PACS (REST, DICOMweb, MWL, C-FIND/C-MOVE). V repu přes `docker-compose.yml`.
- **pydicom**: čtení a zápis DICOM. **pynetdicom**: DIMSE klient i server.
- **dcm4che** toolkit (`findscu`, `movescu`) a **dcmtk** (`findscu`, `echoscu`) pro rychlé ruční testy v CLI.
- Testovací data: [TCIA](https://www.cancerimagingarchive.net/) (reálné anonymizované onkologické CT) a [SIIM hackathon dataset](https://github.com/ImagingInformatics/hackathon-dataset) (FHIR + DICOM vignety).

## Slovníček
- **Komparace / prior / komparátor**: předchozí vyšetření ke srovnání.
- **Accession number**: číslo žádanky/vyšetření v RIS.
- **k.l.**: kontrastní látka. **Nativ**: bez k.l. **Fáze**: arteriální, portální/venózní, pozdní.
- **Topogram / scout**: přehledový snímek pro plánování, ke srovnání nepoužitelný.
- **Restaging**: přešetření rozsahu nádoru po léčbě. **Dispenzarizace**: pravidelné sledování.
- **Hanging protocol**: rozložení sérií na monitoru radiologa (aktuální vedle předchozí).
- **MDT / MDK**: multidisciplinární tým nebo komise.
