# Rakathon 2026 – co to je a jak to poběží

> Stav k 8. 10. 2026. Zdroje: [rakathon.cz](https://www.rakathon.cz/), [pravidla (PDF)](https://bqcunktidwhqgkjnisbp.supabase.co/storage/v1/object/public/terms/terms/1782206443390-Rakathon_2026_pravidla_a_podminky_ucasti_2_.pdf), [Luma](https://luma.com/vyf6uavq).

## V kostce
- **Národní AI hackathon proti rakovině**, 2. ročník (1. ročník 2025 jen v Praze, 8 výzev z FN Motol).
- Pořadatel: **Insane Business Ideas s.r.o. / CEE Hacks** (info@ceehacks.com), ve spolupráci s FN Motol, Nemocnicí Na Homolce a 2. LF UK.
- Tři města současně: **Praha** (FN Motol a Homolka, akademičtí partneři 2. LF UK a ČVUT), Brno (MOÚ), Ostrava (FN Ostrava). Očekává se 500+ účastníků.
- 23 výzev, z toho 9 pražských. **PACS Comparator Check** zadává FN Motol a Homolka.
- Týmy 2–4 lidi, interdisciplinární (IT + medicína + data + design).

## Harmonogram
| Kdy | Co |
|---|---|
| **čt 15. 10.** | **Online session**: experti představí nástroje a zdroje dat k výzvám. **Povinně sledovat!** |
| pá 16. 10. 9:30 | Registrace, představení výzev, seznámení s mentory |
| **pá 16. 10. 12:00** | **Start hackování** |
| **so 17. 10. 12:00** | **Deadline odevzdání** (24 h práce) |
| so 17. 10. 13:00 | Lokální pitch v Praze |
| so 17. 10. 17:00 | Vyhlášení lokálních TOP týmů → postup do finále |
| ne 18. 10. od 14:00 | Národní finále (kampus 2. LF UK, Plzeňská 2), nový pitch před hlavní porotou |
| ne 18. 10. 17:00 | Vyhlášení vítězů |

## Ceny
- Celkově: 100 000 / 50 000 / 25 000 Kč.
- **InterSystems Prize** 1 500 EUR (předává se na pražském finále). Zjistit podmínky: pravděpodobně chtějí využití jejich technologií (IRIS for Health, FHIR server, HealthShare). Pro naši výzvu by dávalo smysl FHIR `ImagingStudy` / `ServiceRequest`.
- MEDDI ONCO Award za největší praktický potenciál.

## Pravidla, která nás ovlivňují
- **§4 Data:** do řešení se nesmí dávat reálná osobní data pacientů bez písemného oprávnění. Data od pořadatele používat jen k danému účelu a po akci smazat. **Proto pracujeme jen se syntetickými daty** (viz `src/pacs_check/synth`).
- **§4 Charakter:** výstupy jsou prototypy, ne zdravotnický prostředek. Do UI i do pitche patří disclaimer.
- **§5 Licence:** odevzdáním dáváme pořadateli a partnerům **nevýhradní, bezúplatnou a neomezenou licenci** včetně komerčního užití a sublicencí. Autorství zůstává nám a kód můžeme dál používat.
- **§6 Open source/AI:** dodržet licence knihoven a na vyžádání uvést použité komponenty (Orthanc je GPLv3, jeho DICOMweb plugin AGPLv3, pydicom MIT, pynetdicom MIT, httpx BSD). AI nástroje nesmí zpracovávat osobní údaje.
- **§7 Veřejnost:** výstupy mohou být zveřejněny. Nic citlivého do repa.
- **§8 Hodnocení:** relevance k výzvě, inovativnost, technická proveditelnost, dopad na zdravotnictví, kvalita prototypu, práce s daty, uživatelská přívětivost, implementační potenciál, kvalita prezentace.

## ⚠️ Otevřená otázka: kód připravený předem
Pravidla předpřipravený kód **výslovně nezakazují, ale ani nepovolují**. Doporučení:
1. Zeptat se na online session 15. 10. nebo e-mailem na info@ceehacks.com.
2. Do té doby brát tento repozitář jako **přípravu znalostí, prostředí a syntetických dat**. Prototyp je „spike“ na ověření, že se s PACS dá mluvit.
3. Na pitchi transparentně říct, co vzniklo před akcí a co během ní.
