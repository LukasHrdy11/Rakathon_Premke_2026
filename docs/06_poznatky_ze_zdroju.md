# Poznatky z podkladů pořadatele a co z nich plyne pro nás

Zdroje (ve složce `zdroje/`; materiály třetích stran, zatím necommitované – repo může být zveřejněno, pravidla §7):
- **[FBMI]** A. Tichopád (ČVUT FBMI, Health Data Lab): *Systémová koordinace cesty pacienta – Analýza cesty onkologického pacienta* (kurz z ledna 2026, doplněný o principy a výzvy pro hackathon), `analyza_cesty_onkologickeho_pacienta_fbmi_final.pptx`.
- **[eHealth]** M. Opatřil (Umbrellateam): *České eHealth v kostce* (webinář pro soutěžící, 15. 10. 2026), `Ceske_eHealth_v_kostce_Rakathon_2026_Michal_Opatril.pdf`.
- **[HL7]** HL7 Česká republika: *HL7: propojené informace pro zdravotnictví* (úvod pro soutěžní týmy, zdroje ověřeny k 10. 10. 2026), `hl7_rakathon_2026___u__vod-1.pptx`.

Čísla slidů jsou uvedena v závorce. [FBMI] a [eHealth] řeší hlavně **koordinaci péče**, ne PACS. Převzali jsme jen to, co se týká naší výzvy. Ostatní výzvy z [FBMI] (doprava pacientů, předání mezi KOC a regionem, diagnostická epizoda) patří jiným týmům.

## Shrnutí: poznatek → změna v projektu
| Poznatek | Zdroj | Co jsme udělali |
|---|---|---|
| Koordinace = **úkol + vlastník + termín + eskalace**. Odeslaná žádost ještě neznamená vyřízenou. | [FBMI 20] | Každý nález má `owner`, `due` a `escalate` (`models.Finding`, `Rules.tasks`) |
| Klinická rozhodnutí zůstávají u oprávněného zdravotníka. Koordinátor zajišťuje jen návaznost. | [FBMI 20] | `NEEDS_HUMAN` jde indikujícímu lékaři, logistika asistentovi a PACS adminovi |
| Výstup AI musí mít **zdroj, nejistotu a člověka**. Typické chyby: negace, staré nebo špatné datum, vynechání, záměna pacienta. | [FBMI 49–50], [eHealth 19] | Citace žádanky v nálezu (`Finding.source`), detekce negace, zmínka s datem po plánovaném CT jde na `NEEDS_HUMAN` |
| Negativní nebo neúplný výsledek nesmí případ automaticky uzavřít. | [FBMI 44] | Negovaná zmínka nezmizí, zůstane jako poznámka se zdrojem |
| **FHIR na okraji**, oddělený interní model. Procesní jádro (úkol, stav, audit). Žádná fiktivní produkční integrace. | [eHealth 17] | `fhir.py` exportuje FHIR R4 `Task`, jádro o FHIR neví. Jako ilustrativní R4, ne CZ profil. |
| Výzva typu „cesta pacienta“: chybějící podklady a termíny. FHIR `Task`, `DocumentReference`, IHE MHD. | [eHealth 19] | Pozicování v pitchi, `Task` export, MHD jako další krok (viz níže) |
| Audit přístupu (IHE ATNA, zákon 372/2011) | [eHealth 12, 16], [FBMI 48–49] | `reports/audit.jsonl`: kdo, kdy, zdroj, účel, kterých pacientů se dotaz týkal |
| Fast track u podezření na ca plic: CT objednat do 24 h, termín do týdne (max. 14 dní) | [FBMI 32] | Priorita z MWL (`RequestedProcedurePriority`) se zobrazuje a promítá do `Task.priority`. Scénář 12. |

## Čísla pro pitch (citovat opatrně)
- **Odklad léčby** (Hanna et al., BMJ 2020; 34 observačních studií, > 1,2 mil. pacientů): každé 4 týdny odkladu jsou **asociovány** s vyšší mortalitou, a to u chirurgie, systémové léčby i radioterapie [FBMI 24]. Poznámka autora slidu: jde o asociace z observačních studií a log-lineární model, ne o stejný individuální efekt u každého pacienta. „4 týdny nejsou univerzální bezpečná čekací doba“ [FBMI 50].
- **Karcinom plic v ČR** (administrativní data plátců, kohorta od první bronchoskopie; agregovaná data, ne radiologie):
  - 5 819 pacientů s první bronchoskopií, 45,6 % prošlo MDT, medián BX → MDT 20 dní [FBMI 23].
  - Do 4 týdnů od bronchoskopie zahájí léčbu jen **21 % operovaných, 23 % ozařovaných a 31 % pacientů na farmakoterapii**. Déle než 6 týdnů čeká 58 % na operaci, 64 % na RT a 47 % na farmakoterapii [FBMI 27]. Doporučení je operovat do 4 týdnů (Banks et al., World J Surg 2023).
- **Pacienti se léčí jinde, než bydlí** [FBMI 28–29]: Praha má 674 pacientů s bydlištěm, ale **léčí 1 011**. Středočeský kraj má 539 pacientů s bydlištěm, ale léčí jen 229. Podobná migrace do center je vidět u IBD [FBMI 43].
  → **Pro nás:** diagnostika často proběhne v regionu (např. Kladno) a léčba v pražském centru. Předchozí CT pak leží v jiném PACS, a proto potřebujeme `EXTERNAL_REQUEST_EPACS`.
- **Fast track plíce** (návrh algoritmu implementovaného jako léčebný plán do NIS) [FBMI 32]: všechna vyšetření do 7–14 dní, objednat ideálně do 3 dnů od prvního kontaktu, pak triáž a MDT.
  → **Pro nás:** u fast-track CT je na zajištění komparátoru jen pár dní. Když ePACS trvá déle, vznikne eskalace dřív, než pacient přijde.

## Koordinační principy [FBMI 20] → náš model
| Princip | U nás |
|---|---|
| Úkol: co má následovat a proč | `Finding.message` + `Finding.action` |
| Vlastník a termín od jasného milníku | `Finding.owner`, `Finding.due` = plánované CT − předstih (`Rules.tasks`) |
| Potvrzení převzetí | **zatím ne**: stav úkolu (požádáno → přijato → snímky dorazily). Inspirace: eŽádanka jako stavový automat [eHealth 9] |
| Výjimka a eskalace | `Finding.escalate`, když termín úkolu už uplynul. V reportu „Termín ohrožen“, v FHIR `priority=asap` |
| Pacient ví, co dál | mimo náš rozsah (nástroj pracuje pro radiologii) |

Předstihy v `Rules.tasks` (prefetch 1 den, ePACS 3 dny, …) jsou **provozní odhady k ověření se zadavatelem**, ne klinické lhůty.

## České eHealth: co potřebujeme vědět [eHealth]
- **Čtyři vrstvy:** EU (EHDS, MyHealth@EU, NCPeH) → stát/centrální služby (identity, oprávnění, eŽádanky) → výměnná vrstva (AAfD, registrované sítě, **navrhovaný model**) → poskytovatelé a jejich IS včetně PACS [3].
- **Právo:** stavět na platném právu (372/2011, 444/2024, 325/2021 + 236/2025, GDPR). Novela 325 je jen **návrh 2026**: povinné eŽádanky 2027/2028, povinná elektronická dokumentace 2029 [4].
- **EHDS:** primární využití (péče o pacienta) je odděleno od sekundárního (výzkum přes HDAB). **Zprávy z obrazových vyšetření a snímky** spadají do vlny 2031 [5–6].
- **„Zpřístupnit“, ne „sdílet“:** data zůstávají u poskytovatele (source of truth). Index nebo registr drží metadata, „kde a jaký dokument“. Oprávnění a účel se ověřují při přístupu [10].
- **AAfD:** federovaná síť, ne centrální databáze. Registr drží metadata a reference, obsah zůstává v repozitáři PZS, k tomu autorizace, směrování a audit [11].
- **IHE MHD nad FHIR R4:** publish (ITI-65) → index (`DocumentReference`) → find (ITI-67) → retrieve (ITI-68). MHDS = architektura výměnné sítě. ATNA = audit [12].
- **Další IHE profily** [16]:
  - PDQm a PIXm/PMIR: identita pacienta napříč nemocnicemi
  - mCSD: adresář organizací a endpointů
  - IUA/ATNA: autorizace a audit
  - DSUBm: odběr notifikací o nových dokumentech
  - Profil sám o sobě **nedává právní oprávnění**.
- **eŽádanka je stavový automat:** vystavit → uložit → vyhledat → přijmout → vyřídit → výsledek. Má výjimky: storno, neproveditelnost, rozdělení, výpadek [9].
- **FHIR:** „pošli JSON“ není zadání. Rozhoduje profil, terminologie (LOINC, SNOMED CT, NČLP) a validace (OperationOutcome). Čtení: hl7.org/fhir/R4 → CZ Core (hl7.cz/fhir) → doménový IG (CZ Imaging) → HIE IG (MHD/ATNA, CI build) [14–15].
- **Národní onkologický průvodce** (záměr, realizace nejistá): suspekce → epizoda → **podklady** → MDT → léčebný plán → follow-up [18]. **Náš nástroj je krok „podklady“ pro zobrazovací vyšetření.**

### Co z toho plyne pro naši výzvu
1. **Dnešek:** externí snímky se vyžadují ručně přes ePACS/ReDiMed. My předem víme, **co** vyžádat a **do kdy**.
2. **Budoucnost (AAfD/MHD):** dotaz ITI-67 na registr podle pacienta vrátí `DocumentReference` zpráv z obrazových vyšetření z jiných PZS. To je **šestý zdroj „očekávání“**, který najde i externí CT, které žádanka nezmiňuje. Na hackathonu jen jako **stub/simulátor**, ne jako tvrzení o produkční integraci [eHealth 17].
3. **Identita:** PDQm/PIXm řeší, že pacient má v Kladně a v Motole jiné ID.
4. **Notifikace:** DSUBm by mohl ohlásit, že vyžádané snímky dorazily. Tím se uzavírá smyčka „potvrzení převzetí“.

## Právo a data [FBMI 48–49], [eHealth 4, 10]
- Přístup se řídí skutečnou pracovní rolí a nezbytností pro péči. Označení „koordinátor“ samo oprávnění nevytváří.
- Pro každé zpracování je potřeba právní titul (GDPR čl. 6 a čl. 9 odst. 2 písm. h), minimalizace, audit a doba uchování. Dodavatel aplikace jedná jako zpracovatel (čl. 28).
- **U nás:** čteme jen metadata (DICOM hlavičky, ne pixely) a text žádanky. Účel je návaznost péče, výstup je pro role, které k pacientovi už přístup mají. Běh se zapisuje do auditu. Jde o koncepční rámec, **ne právní posouzení**.

## Akceptační scénáře [FBMI 50] → naše syntetické scénáře
| Scénář z prezentace | U nás |
|---|---|
| Ztracený výsledek (vyšetření proběhlo, výsledek chybí; kdo to řeší?) | scénář 5 `MISSING_IN_PACS` → PACS administrátor |
| Chyba extrakce (negovaný nález, starý nebo špatný termín) | scénář 11 (negace), 13 (datum po CT); „snímky nejsou k dispozici“ **není** negace (scénář 12) |
| Měřitelné výsledky: čas k dalšímu kroku, podíl dokončených úkolů, chyby, čas koordinátora | metriky pro pitch. Sledovat i **falešná upozornění** [FBMI 44] |

## HL7, FHIR a onkologické datové modely [HL7]
Edukativní úvod: HL7 jako organizace, rodina standardů, evropský **Cancer Common** (ECCDM) a americké **mCODE**. Pro PACS nic konkrétního, ale dává rámec, **proč** komparace v onkologii potřebujeme a jak o tom mluvit datově.

- **Rodina HL7** [6]: V2 = zpráva o události (příjem, objednávka, výsledek), CDA = klinický dokument, FHIR = propojené záznamy. V nemocnici běží **souběžně**, nečekat, že každý systém má FHIR [6, pozn. 8].
  → **Pro nás:** objednávky a zprávy budou spíš HL7 v2 (ORM/ORU) nebo MWL, ne FHIR. Adaptéry na vstupu, FHIR jen na výstupu (`fhir.py`), jak už máme.
- **FHIR v EU a ČR** [8]: EHDS vyžaduje FHIR pro prioritní typy EHR (HL7 Europe, hl7.eu/fhir). České profily na hl7.cz/fhir. NCEZ uvádí REST API podle FHIR R4. Onkologické zdroje (Cancer Common, mCODE) stojí na **R4**.
- **Cancer Common (ECCDM)** [10–13, 18]: minimální, rozšiřitelný model napříč nádory, pro péči i výzkum. Verze **1.0.0-ballot** (k posouzení, ne normativní). Mapování na FHIR a OMOP se dokončuje. Oblasti: pacient, diagnóza a stadium, léčebné epizody, **vývoj onemocnění** (`ClinicalCancerProgression`, `OverallCancerTreatmentResponse`, `LastFollowUp`).
- **„Počáteční stadium není automaticky současným stavem.“** Onkologická data mají časový kontext, nové hodnocení doplňuje historii [13, pozn. 11].
  → **Pro nás:** hodnocení progrese a odpovědi na léčbu je přesně to, co radiolog bez komparátoru udělat nemůže. Proto u onkologie hledáme **baseline i poslední** vyšetření (`checker.py`, krok 3), ne jen poslední.
- **CancerStage** [15]: klasifikace (TNM, FIGO, Lugano), komponenty T/N/M, klinická vs. patologická. Pro nás mimo rozsah (stadium neurčujeme).
- **mCODE STU4 (4.0.0)** [19–20]: konkrétní FHIR profily a terminologie (pacient, nemoc, hodnocení, genomika, léčba, výsledky). Americký kontext, návaznost na US Core. Cancer Common a mCODE se doplňují, ale **nejsou zaměnitelné**: stejný název neznamená stejnou definici, kardinalitu ani terminologii [pozn. 20].
- **Doporučení pro týmy** [21, pozn. 21–22]:
  - vybrat **malý soubor** důležitých informací, vysvětlit strukturu a ověřit význam s klinickým mentorem;
  - u AI **zachovat původ tvrzení** a **rozlišovat známé a chybějící údaje**;
  - pro implementaci zafixovat **konkrétní publikovanou verzi** (ne CI build).

### Co z toho plyne pro naši výzvu
1. **Pitch, věta pro porotu:** „Bez komparátoru nevznikne hodnocení vývoje onemocnění (Cancer Common `ClinicalCancerProgression` / `OverallCancerTreatmentResponse`, v mCODE stav onemocnění). Hlídáme vstup, na kterém tento datový bod stojí.“ Neříkat, že je generujeme: nediagnostikujeme.
2. **Malý soubor informací:** pracujeme jen s tím, co potřebujeme k nalezení komparátoru (pacient, modalita, oblast, datum, místo, accession). Odpovídá doporučení [21].
3. **Původ a chybějící údaje:** už máme `Finding.source` (citace žádanky) a stavy rozlišují „předchozí se nečeká“ (`NO_PRIOR_EXPECTED`), „chybí“ a „nejisté“ (`NEEDS_HUMAN`).
4. **Verze:** `fhir.py` cílí na FHIR **R4 (4.0.1)**. Kdyby se Task napojoval na onkologický kontext, vycházet z Cancer Common 1.0.0-ballot nebo mCODE STU4 a mapování posoudit, ne převzít [20].
5. **Další krok (ne na hackathon):** `Task.reasonReference` na onkologickou diagnózu (`Condition`), pokud ji RIS/NIS předá. Pro prioritizaci by stačil příznak „onkologický pacient v léčbě“.
