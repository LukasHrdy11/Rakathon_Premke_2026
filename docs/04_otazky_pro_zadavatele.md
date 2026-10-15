# Otázky pro zadavatele a mentory (FN Motol a Homolka)

Položit na **online session 15. 10.** nebo hned v pátek ráno. Odpovědi zapisovat sem.

## Data a přístup
- [ ] Jaká data dostaneme? Export (CSV/JSON), anonymizovaný dump, testovací PACS, nebo nic a máme si je nasimulovat?
- [ ] Bude k dispozici testovací PACS/RIS s DICOMweb nebo DIMSE (AE Title, IP, port)?
- [ ] Dostaneme ukázky reálných (anonymizovaných) **textů žádanek** a **popisů studií/sérií**?
- [ ] Smíme na data použít externí LLM API, nebo jen lokální model?
- [x] Je v pořádku použít kód připravený před akcí? **Ano, ale jasně říct, co vzniklo před akcí a co během ní** (viz [docs/01, §1](01_implementace.md#1-zadání-a-pravidla-v-kostce)).

## Systémy
- [ ] Jaký PACS a RIS používá Motol a jaký Homolka (dodavatel, verze)? Podporuje DICOMweb?
- [ ] Sdílí Motol a Homolka PACS, nebo jde o dvě oddělené instance? Jak se mezi nimi předávají snímky?
- [ ] Jak se dnes vyžadují externí snímky (ePACS, ReDiMed, CD)? Kdo to dělá a jak dlouho to trvá?
- [ ] Mají archivní vrstvy (online/nearline/offline)? Jak dlouho trvá prefetch?
- [ ] Jak je identifikován pacient (rodné číslo, interní ID, IssuerOfPatientID)?

## Definice „relevantního“
- [ ] Které předchozí vyšetření radiolog ke CT chce? Jen CT stejné oblasti, nebo i PET/CT, MR, UZ?
- [ ] Jaké časové okno? Liší se pro onkologii (baseline + nadir dle RECIST) a ostatní?
- [ ] Kolik komparátorů: jen poslední, nebo poslední + baseline?
- [ ] Jsou pro ně důležité i **zprávy** (popisy) předchozích vyšetření, nebo jen obrazy?
- [ ] Které série jsou nutné (tenké řezy, konkrétní fáze)?

## Workflow a uživatel
- [ ] Kdo bude výstup používat: radiolog, radiologický asistent, plánovačka, onkolog?
- [ ] Kolik dní předem? Kolik CT denně (řádově)?
- [ ] V jaké podobě: seznam, e-mail, značka v RIS, úkol? Kde by to „žilo“?
- [ ] **Kdo vlastní který úkol?** Prefetch, ePACS žádost, chybějící série, RIS≠PACS, ověření u lékaře. Odpovídá to `Rules.tasks`?
- [ ] **Jak dlouho trvá** prefetch z archivu a vyžádání přes ePACS? (předstih úkolu, teď odhad 1 a 3 dny)
- [ ] Nese MWL/RIS **prioritu** (`RequestedProcedurePriority`) nebo příznak fast track / suspekce na nádor?
- [ ] V jakém formátu jdou objednávky a zprávy mezi NIS, RIS a PACS: **HL7 v2** (ORM/ORU), MWL, nebo FHIR? [HL7 6]
- [ ] Je v RIS/NIS strukturovaně vidět, že jde o **onkologického pacienta v léčbě** (diagnóza, fáze léčby)? Šlo by o vstup pro prioritu a `Task.reasonReference`.
- [ ] Používá Motol/Homolka **eŽádanky**? Je žádanka na CT dostupná strukturovaně (FHIR `ServiceRequest`)?
- [ ] Přicházejí externí snímky dnes přes ePACS jako studie s `InstitutionName` jiné nemocnice? Jak poznáme, že vyžádané snímky dorazily?
- [ ] Jak často se dnes stane, že komparace chybí? Existují čísla nebo příklady?
- [ ] Co je nejčastější příčina: externí vyšetření, archiv, chybějící série, nebo chyba v ID?

## Hodnocení
- [ ] Co by zadavatel považoval za úspěch prototypu?
- [ ] Co konkrétně chce InterSystems pro svou cenu (IRIS, FHIR)? Stačí export FHIR `Task`, nebo chtějí FHIR server?
- [ ] Mentor HL7 ČR: dává smysl odkazovat v pitchi na Cancer Common / mCODE (hodnocení vývoje onemocnění potřebuje komparátor), nebo je to mimo rozsah?
- [ ] Mentor pro eHealth (M. Opatřil): je pro prototyp vhodné ukázat MHD ITI-67 stub nad CZ HIE IG?
