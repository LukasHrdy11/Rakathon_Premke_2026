# Otázky pro zadavatele a mentory (FN Motol a Homolka)

Položit na **online session 15. 10.** nebo hned v pátek ráno. Odpovědi zapisovat sem.

## Data a přístup
- [ ] Jaká data dostaneme? Export (CSV/JSON), anonymizovaný dump, testovací PACS, nebo nic a máme si je nasimulovat?
- [ ] Bude k dispozici testovací PACS/RIS s DICOMweb nebo DIMSE (AE Title, IP, port)?
- [ ] Dostaneme ukázky reálných (anonymizovaných) **textů žádanek** a **popisů studií/sérií**?
- [ ] Smíme na data použít externí LLM API, nebo jen lokální model?
- [ ] Je v pořádku použít kód připravený před akcí? (pravidla to neřeší)

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
- [ ] Jak často se dnes stane, že komparace chybí? Existují čísla nebo příklady?
- [ ] Co je nejčastější příčina: externí vyšetření, archiv, chybějící série, nebo chyba v ID?

## Hodnocení
- [ ] Co by zadavatel považoval za úspěch prototypu?
- [ ] Co konkrétně chce InterSystems pro svou cenu (IRIS, FHIR)?
