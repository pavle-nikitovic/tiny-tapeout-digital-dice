# Detaljan izveštaj RTL sinteze jezgra `pcg32_oneseq_core`

| Stavka | Vrednost |
|---|---|
| Projekat | Tiny Tapeout digitalna kockica — poređenje PRNG jezgara |
| Analizirano jezgro | `pcg32_oneseq_core` |
| Vrsta analize | Pre-layout RTL sinteza i multi-corner STA |
| Tehnologija | SKY130A |
| Biblioteka standardnih ćelija | `sky130_fd_sc_hd` |
| Alat i verzija | LibreLane `2.4.2` |
| Tok | `SynthesisExploration` |
| Nominalna učestanost | 50 MHz |
| Perioda takta | 20.0 ns |
| Referentna strategija | `AREA 0` |
| Datum eksperimenta | 26. avgust 2026. |

## 1. Svrha dokumenta

Ovaj dokument opisuje kompletan postupak i rezultate RTL sinteze modula
`pcg32_oneseq_core`. Cilj je da rezultat bude:

- tehnički objašnjen, a ne samo sačuvan kao skup brojčanih metrika;
- ponovljiv pomoću tačno navedenog alata, PDK-a, konfiguracije i komande;
- direktno uporediv sa rezultatima jezgara `lfsr64_core` i
  `xoroshiro64ss_core`;
- pogodan kao osnova za tekst diplomskog rada i kasnije fizičko poređenje;
- jasno ograničen na ono što pre-layout sinteza zaista može da pokaže.

Izveštaj opisuje rezultat konkretnog algoritma **i konkretne izabrane
mikroarhitekture**. Drugačija PCG32 realizacija, na primer višeciklusni ili
pipeline množilac, mogla bi dati bitno drugačije rezultate površine, kašnjenja
i potrošnje.

## 2. Kratak zaključak unapred

Sinteza je uspešno završena, a svih devet istraženih strategija prolazi
setup uslov za takt od 50 MHz. Zajednička referentna strategija `AREA 0`
prolazi i setup i hold proveru u svim analiziranim PVT uglovima:

- najgori setup slack iznosi **+0.571877 ns** u SS uglu;
- najgori hold slack iznosi **+0.142826 ns** u FF uglu;
- setup i hold TNS iznose **0 ns**;
- nema inferovanih latch-eva, memorija ni Yosys strukturnih problema;
- netlist sadrži **5 998 standardnih ćelija** i zauzima
  **64 853.4496 µm² cell area**;
- čak **96.82%** cell area pripada kombinacionoj logici;
- SS analiza prijavljuje **1 962 max-slew**, **81 max-fanout** i
  **1 max-capacitance** prekršaj;
- preliminarna TT vectorless procena ukupne snage je **579.0544 mW** i ne
  predstavlja signoff ni izmerenu potrošnju čipa.

Kritični setup put prolazi kroz mrežu koja realizuje 64-bitno LCG ažuriranje
stanja. To potvrđuje da je glavno ograničenje ove jedno-ciklusne
PCG32 realizacije konstantno 64-bitno množenje i sabiranje, a ne izlazna
promenljiva rotacija.

## 3. Funkcija i mikroarhitektura jezgra

### 3.1. Osnovna operacija PCG32

PCG32 kombinuje dve funkcionalne celine:

1. 64-bitni linearni kongruentni generator (LCG) ažurira interno stanje:

   ```text
   novo_stanje = staro_stanje × konstanta_množioca + konstanta_priraštaja
   ```

2. Iz starog 64-bitnog stanja formira se 32-bitni izlaz pomoću XSH-RR
   izlazne transformacije:

   ```text
   xorshift + promenljiva rotacija udesno
   ```

Softverski procesor 64-bitno množenje vidi kao jednu instrukciju. U ASIC
netlistu ono mora biti realizovano velikom mrežom standardnih logičkih ćelija.
Zbog toga ista algoritamska operacija može biti znatno skuplja u namenskom
hardveru nego u softveru.

### 3.2. Interfejs modula

Sintezovani modul ima šest portova, odnosno ukupno 37 port-bitova:

| Port | Širina | Uloga |
|---|---:|---|
| `clk_i` | 1 | Takt |
| `rst_ni` | 1 | Aktivno-nizak reset |
| `next_i` | 1 | Zahtev za sledeću pseudoslučajnu reč |
| `ready_o` | 1 | Indikacija da jezgro može da prihvati zahtev |
| `random_o` | 32 | Registrovan 32-bitni pseudoslučajni izlaz |
| `valid_o` | 1 | Indikacija validnosti izlaza |

Netlist pokazuje da je `ready_o` kombinacioni izlaz; u FF setup izveštaju se
vidi put `rst_ni` → bafer → `ready_o`. Zato `ready_o` nema poseban flip-flop.

### 3.3. Registrovano stanje

Ukupno 97 flip-flopova tačno odgovara registrovanim RTL signalima:

| Registrovana veličina | Broj bitova |
|---|---:|
| `state_reg` | 64 |
| `random_o` | 32 |
| `valid_o` | 1 |
| **Ukupno** | **97** |

Sinteza koristi obične `sky130_fd_sc_hd__dfxtp_2` flip-flopove. Reset i
enable/hold ponašanje realizovani su kombinacionom logikom na D ulazima, pa
nije bila potrebna posebna memorija niti latch.

## 4. Kontrolisani uslovi eksperimenta

### 4.1. Zamrznuti RTL baseline

Pre sinteze je potvrđeno da je `src/pcg32_oneseq_core.v` identičan zamrznutoj
verziji:

| Git identifikator | Vrednost |
|---|---|
| Baseline tag | `prng-core-baseline-v1` |
| Baseline commit | `edbc39c` |

Tag je anotiran, pa objekat taga i commit na koji tag pokazuje mogu imati
različite hash vrednosti. Za identifikovanje RTL verzije koristi se commit
dobijen izrazom `prng-core-baseline-v1^{commit}`.

RTL nije menjan niti optimizovan pre referentne sinteze. Time su očuvani isti
uslovi pod kojima su analizirana prethodna dva jezgra.

### 4.2. Konfiguracija sinteze

Korišćena je konfiguracija:

```json
{
  "DESIGN_NAME": "pcg32_oneseq_core",
  "VERILOG_FILES": [
    "dir::../../src/pcg32_oneseq_core.v"
  ],
  "CLOCK_PORT": "clk_i",
  "CLOCK_PERIOD": 20.0,
  "PDK": "sky130A",
  "STD_CELL_LIBRARY": "sky130_fd_sc_hd",
  "SYNTH_STRATEGY": "AREA 0"
}
```

Konfiguracija je sačuvana u:

```text
synthesis/pcg32_oneseq_core/config.json
```

Commit kojim je dodata konfiguracija:

```text
b919a81  Add PCG32 core synthesis configuration
```

### 4.3. Verzije alata i PDK-a

| Parametar | Vrednost |
|---|---|
| LibreLane | `2.4.2` |
| PDK | `sky130A` |
| Standard-cell library | `sky130_fd_sc_hd` |
| Open-PDKs snapshot | `0fe599b2afb6708d281543108caf8310912f54af` |
| Docker | Korišćen preko LibreLane `--dockerized` režima |
| Paralelizam | `-j 1` |

Isti alat, biblioteka, PDK snapshot, takt i stepen paralelizma korišćeni su za
sva tri jezgra. To smanjuje mogućnost da razlike potiču od okruženja umesto od
algoritma i mikroarhitekture.

### 4.4. Komanda za pokretanje

Iz korena repozitorijuma pokrenuto je:

```bash
python -m librelane --pdk-root "$PDK_ROOT" \
  --docker-no-tty \
  --dockerized \
  -j 1 \
  --flow SynthesisExploration \
  --run-tag pcg32_oneseq_core_50mhz \
  synthesis/pcg32_oneseq_core/config.json
```

Tok je završen porukom `Flow complete`.

## 5. Synthesis Exploration

### 5.1. Istražene strategije

LibreLane `SynthesisExploration` automatski je pokrenuo devet Yosys/ABC
strategija:

- `AREA 0`, `AREA 1`, `AREA 2`, `AREA 3`;
- `DELAY 0`, `DELAY 1`, `DELAY 2`, `DELAY 3`, `DELAY 4`.

Nazivi `AREA` i `DELAY` označavaju različite unapred definisane sekvence
optimizacionih prolaza. Oni ne garantuju da će svaka naredna strategija imati
manju površinu ili bolje kašnjenje za svaki dizajn.

### 5.2. Rezime svih devet strategija

Sve strategije imaju pozitivan setup slack na 50 MHz i setup TNS jednak nuli.
Najvažnije razlike su:

| Strategija | Setup na 50 MHz | Setup TNS | Najvažniji nalaz |
|---|---:|---:|---|
| `AREA 0` | MET | 0 ns | 5 998 ćelija, 64 853.4496 µm², setup WS +0.571877 ns |
| `AREA 1` | MET | 0 ns | Najmanji broj ćelija: 5 943 |
| `AREA 2` | MET | 0 ns | Najmanja cell area: 64 559.4176 µm² |
| `AREA 3` | MET | 0 ns | Najbolji setup WS: približno +9.5659 ns, uz oko 30% veću površinu |
| `DELAY 0` | MET | 0 ns | Prolazi zajednički timing uslov |
| `DELAY 1` | MET | 0 ns | Prolazi zajednički timing uslov |
| `DELAY 2` | MET | 0 ns | Prolazi zajednički timing uslov |
| `DELAY 3` | MET | 0 ns | Prolazi zajednički timing uslov |
| `DELAY 4` | MET | 0 ns | Veća površina od `AREA 0`, uz nešto lošiji slack od `AREA 0` |

Potpuna, nezaokružena tabela koju je generisao alat sačuvana je u artefaktu
`exploration_summary.rpt`. Ovde su navedene potvrđene vrednosti potrebne za
tumačenje izbora strategije, bez prepisivanja neproverenih cifara.

### 5.3. Zašto je izabrana strategija `AREA 0`

`AREA 2` je apsolutni minimum cell area, ali je samo:

```text
(64 853.4496 - 64 559.4176) / 64 853.4496 × 100% ≈ 0.453%
```

manja od `AREA 0`. `AREA 1` koristi 55 ćelija manje, ali broj ćelija sam po
sebi ne određuje ukupnu površinu jer različite ćelije imaju različite dimenzije.

`AREA 0` je zadržana zato što:

- prolazi zajednički cilj od 50 MHz;
- ima setup i hold TNS jednak nuli;
- površina joj je veoma blizu pronađenog minimuma;
- unapred je izabrana kao zajednički baseline za LFSR64, xoroshiro64ss i
  PCG32, što omogućava fer poređenje.

Izbor ne znači da je `AREA 0` najbolja moguća strategija za svaki pojedinačni
dizajn. Ona je najbolji **zajednički eksperimentalni baseline**.

## 6. Struktura sintetizovanog `AREA 0` netlista

### 6.1. Glavne metrike

| Metrika | Rezultat |
|---|---:|
| Standardne ćelije | 5 998 |
| Flip-flopovi | 97 |
| Kombinacione ćelije | 5 901 |
| Ukupna cell area | 64 853.4496 µm² |
| Sekvencijalna cell area | 2 063.2288 µm² |
| Udeo sekvencijalne površine | 3.18% |
| Kombinaciona cell area | 62 790.2208 µm² |
| Udeo kombinacione površine | 96.82% |
| Memorijske ćelije | 0 |
| Preostali procesi nakon sinteze | 0 |
| Portovi / port-bitovi | 6 / 37 |
| Yosys `CHECK` problemi | 0 |
| Inferovani latch-evi | 0 |

Cell area je zbir površina standardnih ćelija iz biblioteke. Ona nije isto što
i fizička površina postavljenog i rutiranog bloka. Konačna površina mora da
uključi razmake za placement, napajanje, clock tree i rutiranje.

### 6.2. Dominantne vrste logike

U mapiranom netlistu posebno su zastupljene:

- 1 244 XNOR2 ćelije;
- 613 XOR2 ćelija;
- veliki broj AND, NAND, OR, NOR, AOI i OAI ćelija;
- ukupno 135 eksplicitnih MUX2/MUX4 ćelija;
- 97 `dfxtp_2` flip-flopova.

Ovakva raspodela je očekivana za mrežu koja u jednom taktu realizuje
64-bitno konstantno množenje i sabiranje, kao i xorshift i promenljivu
32-bitnu rotaciju.

Odnos kombinacione i sekvencijalne cell area iznosi približno 30.4 : 1.
Zato eventualna optimizacija broja registara ne bi rešila glavni problem;
dominantni trošak je kombinaciona funkcija između registara.

### 6.3. Strukturna ispravnost

Yosys `CHECK` nije prijavio:

- undriven signale;
- višestruke drajvere;
- kombinacione petlje;
- druge strukturne probleme.

Izveštaj `latch.rpt` sadrži poruku da je pokrenut `PROC_DLATCH` prolaz, ali
ne sadrži listu inferovanih latch-eva. Pokretanje provere nije isto što i
pronalaženje latch-a; rezultat je **nula latch-eva**.

## 7. Statička vremenska analiza i PVT uglovi

### 7.1. Šta predstavljaju PVT uglovi

PVT označava kombinaciju:

- **P — process:** tehnološka varijacija brzine NMOS i PMOS tranzistora;
- **V — voltage:** napon napajanja korišćen u karakterizaciji ćelija;
- **T — temperature:** temperatura korišćena u karakterizaciji.

Korišćena su tri Liberty ugla biblioteke:

| Ugao | Process | Temperatura | Napon | Tipično značenje |
|---|---|---:|---:|---|
| `nom_tt_025C_1v80` | TT — typical/typical | +25 °C | 1.80 V | Nominalni uslovi |
| `nom_ss_100C_1v60` | SS — slow/slow | +100 °C | 1.60 V | Najsporije ćelije; često najgori setup |
| `nom_ff_n40C_1v95` | FF — fast/fast | −40 °C | 1.95 V | Najbrže ćelije; često najgori hold |

Ove kombinacije nisu proizvoljna procena autora niti preporuka da se Tiny
Tapeout čip napaja sa 1.60 V ili 1.95 V. To su karakterizacione tačke koje
obezbeđuju SKY130/Open-PDKs Liberty modeli. Tiny Tapeout nominalno koristi
napajanje od 1.8 V, dok se ostali uglovi koriste za konzervativnu STA proveru.

### 7.2. Setup, hold, WS i TNS

- **Setup provera** ispituje da li podatak stiže dovoljno rano pre sledeće
  aktivne ivice takta.
- **Hold provera** ispituje da li se podatak posle aktivne ivice ne menja
  prerano.
- **WS (Worst Slack)** je najgori slack među svim analiziranim putanjama.
- **TNS** je zbir svih negativnih slack vrednosti.

Pozitivan WS znači da najgora putanja prolazi. Odvojena negative-slack-only
`WNS` polja iznose nula jer nema negativnih putanja. TNS jednak nuli znači da
nema putanja sa negativnim slack-om.

### 7.3. Multi-corner rezultat

| Ugao | Setup WS | Hold WS | Setup/Hold TNS | Max-slew prekršaji | Max-fanout prekršaji | Max-cap prekršaji |
|---|---:|---:|---:|---:|---:|---:|
| TT, +25 °C, 1.80 V | +10.5383 ns | +0.3501 ns | 0 / 0 ns | 362 | 81 | 0 |
| SS, +100 °C, 1.60 V | **+0.571877 ns** | +0.8968 ns | 0 / 0 ns | **1 962** | 81 | **1** |
| FF, −40 °C, 1.95 V | +11.233163 ns | **+0.142826 ns** | 0 / 0 ns | 0 | 81 | 0 |

SS određuje ukupni najgori setup rezultat, dok FF određuje ukupni najgori
hold rezultat. To odgovara uobičajenom ponašanju: spore ćelije otežavaju da
podatak stigne na vreme, a brze ćelije povećavaju opasnost da stigne prerano.

## 8. Kritični setup put

### 8.1. Potvrđeni podaci iz izveštaja

| Stavka | Vrednost |
|---|---|
| PVT ugao | `nom_ss_100C_1v60` |
| Početak | `_11833_`, odnosno `state_reg[0]` |
| Kraj | `_11896_/D`; Q mreža tog registra je `rotation_wire[4]`, optimizovani alias RTL bita `state_reg[63]` |
| Tip | Register-to-register, max/setup |
| Broj kombinacionih ćelija na najgorem putu | 27 |
| Data arrival time | 18.924706 ns |
| Data required time | 19.496582 ns |
| Setup slack | **+0.571877 ns — MET** |
| Clock uncertainty | 0.250000 ns |
| Clock mreža | Idealna, bez CTS kašnjenja |

Put se može funkcionalno predstaviti kao:

```text
state_reg[0]
    → XOR/XNOR i složena AND/OR/AOI/OAI mreža
    → prenos kroz 64-bitno LCG množenje i sabiranje
    → state_reg[63]
```

### 8.2. Zašto je ovo važan rezultat

Krajnja tačka je D ulaz `_11896_`. Q izlaz tog registra u optimizovanom
netlistu nosi ime `rotation_wire[4]`, što funkcionalno odgovara RTL bitu
`state_reg[63]`. Put se zato završava na registru stanja, a ne na `random_o`;
kritični put pripada LCG state-update mreži, a ne barrel rotatoru izlazne
XSH-RR transformacije.

Početni bit `state_reg[0]` ima fanout 38. Već prvi Q izlaz u SS uglu ima slew
1.324952 ns, a sledeći XOR izlaz 1.063398 ns; oba su iznad ograničenja od
0.75 ns. To pokazuje da se vremensko i električno opterećenje pojavljuju na
istom delu velike mreže.

### 8.3. Kolika je vremenska rezerva

Rezerva od 0.571877 ns predstavlja samo oko 2.86% periode od 20 ns. Gruba
pre-layout procena minimalne periode, pod pretpostavkom da se ostali uslovi ne
promene, jeste:

```text
Tmin ≈ 20 ns - 0.571877 ns = 19.428123 ns
Fmax ≈ 1 / Tmin ≈ 51.47 MHz
```

Ovo nije garantovana maksimalna učestanost. Posle placement-a, clock-tree
synthesis-a, rutiranja i ekstrakcije parazita kašnjenja se menjaju. Mala
pre-layout rezerva upozorava da 50 MHz može postati teško ostvarivo posle
fizičke realizacije.

## 9. Kritični hold put

### 9.1. Potvrđeni podaci

| Stavka | Vrednost |
|---|---|
| PVT ugao | `nom_ff_n40C_1v95` |
| Početak | `random_o[17]` flip-flop `_11818_` |
| Kraj | D ulaz istog `random_o[17]` flip-flopa |
| Tip | Register-to-same-register, min/hold |
| Kombinacione ćelije | `a21oi_2` + `nor2_2` |
| Data arrival time | 0.378002 ns |
| Data required time | 0.235176 ns |
| Hold slack | **+0.142826 ns — MET** |

Jednaka najgora vrednost pojavljuje se i za kratku povratnu putanju registra
`random_o[18]`.

### 9.2. Tumačenje

Kratka povratna putanja potiče od logike koja zadržava prethodnu vrednost
izlaznog registra kada nema upisa nove reči. U najbržem FF uglu podatak može
vrlo brzo da stigne nazad do D ulaza, pa se zato taj ugao koristi za najgoru
hold proveru.

Slack je pozitivan, što znači da pre-layout netlist prolazi hold proveru.
Međutim, konačna hold provera mora se ponoviti sa stvarnom clock mrežom i
ekstrahovanim kašnjenjima posle rutiranja.

## 10. Električni prekršaji

### 10.1. Rezime

Timing je zadovoljen, ali netlist nije electrical-clean:

| Provera | Ograničenje / najgori slučaj | Broj prekršaja u SS uglu |
|---|---|---:|
| Max slew | Limit 0.750000 ns; najgori slew 1.487774 ns | 1 962 |
| Max fanout | Limit 10; najveći pronađeni fanout 68 | 81 |
| Max capacitance | 0.081330 naspram limita 0.080576 | 1 |

U TT uglu postoji 362 max-slew prekršaja, dok ih u FF uglu nema. Max-fanout
broj ostaje 81 u sva tri ugla jer fanout prvenstveno zavisi od topologije
netlista, a ne od brzine tranzistora.

### 10.2. Slew

Slew je vreme potrebno da signal pređe između logičkih nivoa. Previše spor
prelaz može:

- povećati kašnjenje naredne ćelije;
- povećati dinamičku i kratkospojnu potrošnju;
- smanjiti otpornost na šum;
- otežati pouzdanu fizičku realizaciju i timing closure.

Broj 1 962 ne označava 1 962 pogrešna izlaza. To je broj pinova/provera čiji
izračunati slew u SS uglu prekoračuje limit.

Limit `0.75 ns` nije procena autora i nije posebno Tiny Tapeout pravilo. On je
preuzet iz tačne LibreLane/Open-PDKs konfiguracije korišćene u eksperimentu.
Isti limit je primenjen na sva tri jezgra, pa je poređenje konzistentno.
Bibliotečka granica iznosi 1.5 ns. Najgori PCG32 slew od 1.487774 ns krši
stroži cilj od 0.75 ns, ali je još neposredno ispod bibliotečke granice; zato
se ne sme opisati kao dokaz izlaska iz karakterisanog Liberty opsega.

### 10.3. Fanout

Fanout je broj ulaza ćelija koje pogoni jedan drajver. Najopterećenije mreže
uključuju:

| Drajver/mreža | Fanout |
|---|---:|
| Interna mreža `_05928_/Y` | 68 |
| `rst_ni` | 60 |
| Interna mreža / bit stanja | 46 |
| `next_i` | 43 |
| `state_reg[0]` | 38 |

Veliki fanout povećava ukupnu ulaznu kapacitivnost koju drajver mora da puni i
prazni. Posledice su sporije ivice, veće kašnjenje i veća dinamička potrošnja.

### 10.4. Capacitance

Jedini SS max-capacitance prekršaj nalazi se na `_06431_/X`:

```text
dozvoljeno: 0.080576
izračunato: 0.081330
prekoračenje: 0.000754
```

Prekoračenje je malo, ali je ispravno evidentirano. `Cap = 1` u zbirnom
izveštaju znači **jedan kapacitivni prekršaj**, a ne kapacitivnost jednaku
jedinici.

### 10.5. Zašto je ovo problem iako setup i hold prolaze

Setup i hold odgovaraju na pitanje da li podatak stiže unutar dozvoljenog
vremenskog prozora pri trenutnom modelu. Slew, fanout i capacitance proveravaju
da li su same ćelije i mreže korišćene u dozvoljenom električnom režimu.

Moguće je istovremeno imati pozitivan setup/hold slack i električne prekršaje.
Takav netlist funkcionalno nije automatski pogrešan, ali procene kašnjenja i
snage postaju manje pouzdane, a fizički tok mora da uloži dodatne resurse u
popravku mreža.

Place-and-route može da:

- doda bafere;
- zameni ćelije jačim drajverima;
- napravi stabla za signale velikog fanout-a;
- replicira kontrolnu logiku;
- poboljša placement i rutiranje.

Cena je obično veći broj ćelija, veća površina i potrošnja. Popravke mogu i da
promene setup i hold slack. Zato trenutni pozitivan slack ne garantuje da će
post-route rezultat ostati pozitivan.

## 11. Preliminarna procena snage i energije

### 11.1. TT vectorless `report_power`

Procena je izvršena u uglu `nom_tt_025C_1v80`:

| Grupa | Internal | Switching | Leakage | Ukupno | Udeo |
|---|---:|---:|---:|---:|---:|
| Sekvencijalna logika | 1.179875 mW | 0.594854 mW | 0.000818 µW | 1.774729 mW | 0.3% |
| Kombinaciona logika | 310.7419 mW | 266.5375 mW | 0.026264 µW | 577.2794 mW | 99.7% |
| Clock | 0 mW | 0 mW | 0 mW | 0 mW | 0.0% |
| **Ukupno** | **311.9218 mW** | **267.1326 mW** | **0.027082 µW** | **579.0544 mW** | **100%** |

Ukupna snaga je raspodeljena na približno:

- 53.9% internal power;
- 46.1% switching power;
- zanemarljiv prijavljeni leakage u ovom pre-layout modelu.

Nulta clock snaga nije dokaz da takt ne troši energiju. U ovoj fazi nema
realne clock-tree mreže, pa njen doprinos još nije modelovan.

### 11.2. Šta predstavlja snaga od 579.0544 mW

Vat je džul po sekundi:

```text
1 W = 1 J/s
```

Prema tome, izveštaj procenjuje prosečnu brzinu trošenja energije pri
modelovanoj vectorless aktivnosti. To nije „potrošnja po izlazu“ niti
„potrošnja po taktu“ sama po sebi.

Ako se samo kao normalizacioni proxy pretpostavi neprekidan rad na 50 MHz:

```text
proxy_po_taktu = P / f
            = 0.5790544 W / 50 000 000 Hz
            ≈ 11.5811 nJ/takt
```

Ovo je vectorless energy-per-cycle proxy. Deljenjem iste snage idealnim
protokom od 50 Mword/s dobija se brojčano isti power/throughput proxy od
11.5811 nJ/reč. To nije potvrđena energija po izlazu, jer vectorless analiza
nije izvedena iz zasićenog `next_i` workload-a.

### 11.3. Ograničenja power rezultata

Ova vrednost nije:

- merenje fizičkog čipa;
- post-route ili signoff power analiza;
- analiza zasnovana na stvarnom VCD/SAIF preklapanju;
- konačna energija po pseudoslučajnom izlazu;
- dovoljna za zaključak o Tiny Tapeout termičkom ili strujnom budžetu.

Dominacija kombinacione snage odgovara velikoj jedno-ciklusnoj mreži, tipovima
mapiranih ćelija, njihovim kapacitivnostima i statistički propagiranoj
aktivnosti. Doprinos glitch prelaza ovaj izveštaj ne izdvaja; on ostaje
hipoteza za proveru zajedničkom VCD/SAIF analizom i istim post-route tokom.

## 12. Latencija, protok i normalizovane metrike

### 12.1. Latencija i protok

Za registrovani interfejs ove mikroarhitekture:

| Metrika | Vrednost pri 50 MHz |
|---|---:|
| Arhitekturna latencija | 1 takt |
| Vreme jednog takta | 20 ns |
| Maksimalni održivi protok | 1 × 32-bitna reč/takt |
| Reči u sekundi | 50 miliona reči/s |
| Ekvivalentni sirovi izlazni bit-rate | 1.6 Gbit/s |

Održivi protok važi kada je `next_i` aktivan u svakom taktu u kojem je jezgro
spremno. Ne opisuje brzinu sporijeg spoljnog interfejsa niti učestanost stvarne
Tiny Tapeout pločice.

### 12.2. Protok normalizovan površinom

Na osnovu pre-layout cell area:

```text
50 000 000 reči/s / 64 853.4496 µm² ≈ 770.97 reči/(s·µm²)
```

Ekvivalentno:

```text
64 853.4496 µm² / 50 Mreči/s ≈ 1 297.07 µm² po Mreči/s
```

Ova metrika služi samo za poređenje sintezovanih jezgara. Ne koristi konačnu
fizičku core area i zato mora biti ponovo izračunata posle PnR-a.

## 13. Šta rezultat znači za PCG32 algoritam

### 13.1. Prednosti potvrđene mikroarhitekturom

- Jezgro daje 32-bitnu reč sa jednociklusnim održivim protokom.
- Potreban je samo 64-bitni interni state register.
- Nema memorija, makroa ni složene upravljačke mašine.
- Setup i hold cilj od 50 MHz prolazi u svim analiziranim uglovima.

### 13.2. Glavni hardverski trošak

PCG32 koristi operacije koje su elegantne i brze na procesoru, ali skupe kao
potpuno kombinacioni ASIC datapath:

- 64-bitno konstantno množenje;
- 64-bitno sabiranje;
- xorshift mreža;
- promenljiva 32-bitna rotacija.

Zbog toga 5 901 od ukupno 5 998 ćelija pripada kombinacionoj logici, a
kombinaciona cell area čini 96.82% ukupne vrednosti.

### 13.3. Kontekst prethodna dva jezgra

Za isti `AREA 0` pre-layout tok ranije su dobijene cell area vrednosti:

| Jezgro | Cell area | Max-slew prekršaji |
|---|---:|---:|
| `lfsr64_core` | 5 058.60 µm² | 347 |
| `xoroshiro64ss_core` | 22 142.49 µm² | 441 |
| `pcg32_oneseq_core` | **64 853.4496 µm²** | **1 962** |

PCG32 je približno:

- 2.93 puta veći od xoroshiro64ss jezgra;
- 12.82 puta veći od LFSR64 jezgra;
- ima 4.45 puta više SS slew prekršaja od xoroshiro64ss;
- ima 5.65 puta više SS slew prekršaja od LFSR64.

Ovo još nije konačno ASIC poređenje jer cell area ne uključuje fizičku
implementaciju. Ipak, razlika je dovoljno velika da jasno pokaže cenu
jedno-ciklusnog 64-bitnog LCG datapath-a.

### 13.4. Moguće buduće optimizacije

Ako PCG32 posle PnR-a ne zadovolji površinu, timing ili power cilj, mogu se
ispitati:

- pipeline podela množenja i izlazne transformacije;
- višeciklusno shift-add množenje konstantom;
- deljenje kombinacione mreže na više registarskih etapa;
- niža ciljna učestanost;
- specifično restrukturiranje konstantnog množila.

Svaka takva verzija mora biti vođena kao **nov eksperiment**, jer menja
latenciju, protok, broj registara i fer osnovu poređenja.

## 14. Upozorenja i ograničenja eksperimenta

### 14.1. Generički SDC

LibreLane je prijavio da `PNR_SDC_FILE` i `SIGNOFF_SDC_FILE` nisu posebno
definisani, pa je korišćen generički `base.sdc`. To nije prekinulo tok i isti
pristup je primenjen na sva tri jezgra.

U izveštajima se vide:

- perioda takta 20 ns;
- clock uncertainty 0.25 ns;
- generički ulazni i izlazni eksterni delay od 4 ns za I/O putanje;
- idealna clock mreža bez stvarnog CTS kašnjenja.

### 14.2. Pre-layout karakter rezultata

Analiza ne uključuje:

- placement standardnih ćelija;
- clock-tree synthesis;
- detaljno rutiranje;
- ekstrahovane RC parazite vodova;
- post-route optimizaciju setup/hold/slew/capacitance;
- IR drop i electromigration;
- DRC, LVS i signoff provere;
- realnu Tiny Tapeout tile površinu i popunjenost;
- aktivnost dobijenu iz reprezentativne funkcionalne simulacije.

Poruka o hiljadama `unannotated drivers` je očekivana u ovoj fazi: bez
placement-a i routinga nema ekstrahovanih parazita koji bi bili anotirani na
svaku mrežu.

### 14.3. Šta se iz ovog rezultata sme zaključiti

Može se zaključiti da:

- `AREA 0` netlist je uspešno sintetizovan bez prijavljenih strukturnih problema;
- prolazi zadati pre-layout setup i hold uslov na 50 MHz;
- PCG32 jedno-ciklusna realizacija zahteva veliku kombinacionu mrežu;
- mreža ima značajne električne prekršaje koje PnR mora da rešava;
- rezultat je validan kao zajednički synthesis baseline.

Ne može se još zaključiti da:

- dizajn sigurno prolazi 50 MHz posle routinga;
- staje u određeni Tiny Tapeout broj tile-ova;
- troši 579.0544 mW na stvarnom čipu;
- ima konačnu energiju od 11.5811 nJ po izlazu;
- nema post-route DRC, hold, slew ili IR-drop problema.

## 15. Sačuvani artefakti

Referentni paket se nalazi u:

```text
synthesis/results/pcg32_oneseq_core/
```

Paket sadrži tačno 13 artefakata:

| Fajl | Namena |
|---|---|
| `README .md` | Stvarni naziv manifesta u tagovanom commit-u `e29933e`; razmak pre `.md` ispravlja se tek u naknadnom dokumentacionom commit-u, bez pomeranja synthesis taga |
| `resolved_config.json` | Potpuno razrešena LibreLane konfiguracija |
| `exploration_summary.rpt` | Rezultati svih devet strategija |
| `area0_netlist.v` | Tehnološki mapiran `AREA 0` gate-level netlist |
| `area0_stat.rpt` | Čitljiv Yosys/LibreLane statistički izveštaj |
| `area0_stat.json` | Mašinski čitljive statistike |
| `area0_synthesis_state.json` | LibreLane state posle `AREA 0` sinteze |
| `area0_sta_summary.rpt` | Multi-corner STA sažetak |
| `area0_sta_state.json` | LibreLane state posle STA |
| `area0_setup_ss_max.rpt` | Detaljni SS max/setup putevi |
| `area0_hold_ff_min.rpt` | Detaljni FF min/hold putevi |
| `area0_ss_violators.rpt` | Sačuvano četvorolinijsko zaglavlje SS violator izveštaja; zbirni brojevi su u STA state/summary fajlovima, a konkretni primeri u setup izveštaju |
| `area0_power_tt_preliminary.rpt` | Preliminarni TT vectorless power izveštaj |

Sirovi `runs/` direktorijum ostaje ignorisan i nije commitovan. Time se u Git-u
čuvaju samo kontrolisani i potrebni rezultati, a ne veliki broj privremenih
fajlova toka.

## 16. Git arhiviranje i sledljivost

| Stavka | Vrednost |
|---|---|
| Commit rezultata | `e29933e` |
| Commit poruka | `Archive PCG32 AREA 0 synthesis results` |
| Anotirani tag | `pcg32-synthesis-area0-v1` |
| Tag poruka | `PCG32 AREA 0 synthesis baseline` |
| Remote stanje | Tag i commit poslati na `origin` |
| Završni status | `main` usklađen sa `origin/main`, radno stablo čisto |

Tag pokazuje na commit `e29933e` i predstavlja zamrznuti synthesis baseline.
Ovaj detaljni dokument može biti dodat naknadnim dokumentacionim commitom;
time se ne menja sadržaj već tagovanog paketa od 13 generisanih artefakata.

## 17. Postupak reprodukcije

### 17.1. Provera okruženja

```bash
python -c "from importlib.metadata import version; print(version('librelane'))"
echo "PDK_ROOT=$PDK_ROOT"
echo "PDK=$PDK"
docker info >/dev/null 2>&1 && echo "Docker OK"
python -m json.tool synthesis/pcg32_oneseq_core/config.json >/dev/null
```

Očekivana LibreLane verzija je `2.4.2`, a PDK mora odgovarati zabeleženom
Open-PDKs snapshot-u.

### 17.2. Provera RTL baseline-a

```bash
git cat-file -e 'prng-core-baseline-v1^{commit}:src/pcg32_oneseq_core.v'

git diff --quiet 'prng-core-baseline-v1^{commit}' -- \
  src/pcg32_oneseq_core.v \
  && echo "RTL baseline OK" \
  || echo "STOP: RTL je promenjen"
```

### 17.3. Ponovno pokretanje

```bash
python -m librelane --pdk-root "$PDK_ROOT" \
  --docker-no-tty \
  --dockerized \
  -j 1 \
  --flow SynthesisExploration \
  --run-tag pcg32_oneseq_core_50mhz \
  synthesis/pcg32_oneseq_core/config.json
```

Za potpuno ponovljivo poređenje nije dovoljno koristiti samo isti RTL. Moraju
ostati isti LibreLane, PDK snapshot, standard-cell biblioteka, perioda, SDC
pretpostavke i način procene power aktivnosti.

## 18. Preporučeni sledeći koraci

1. Dodati ovaj detaljni izveštaj kao zaseban dokumentacioni commit.
2. Napraviti objedinjeno synthesis poređenje sva tri jezgra.
3. Pokrenuti isti full PnR tok za `lfsr64_core`, `xoroshiro64ss_core` i
   `pcg32_oneseq_core`.
4. Posle PnR-a proveriti:
   - konačnu core area i broj potrebnih Tiny Tapeout tile-ova;
   - post-route setup i hold u svim uglovima;
   - slew, fanout i capacitance nakon buffer/resize optimizacije;
   - DRC/LVS i routability;
   - clock-tree površinu i potrošnju;
   - power uz isti VCD/SAIF stimulus.
5. Tek nakon jednakog fizičkog toka doneti konačnu odluku o odnosu kvaliteta
   generatora, površine, brzine i energije.
6. Ako PCG32 ne prođe zajednički fizički cilj, analizirati optimizovanu
   mikroarhitekturu kao odvojen eksperiment.

## 19. Završni zaključak

RTL sinteza `pcg32_oneseq_core` je uspešna i reproduktivno arhivirana. Izabrani
`AREA 0` baseline zadovoljava setup i hold cilj od 50 MHz u sva tri PVT ugla,
bez negativnih timing putanja, latch-eva ili strukturnih problema.

Istovremeno, rezultat pokazuje da je PCG32 daleko zahtevniji od prethodna dva
jezgra u izabranoj jedno-ciklusnoj realizaciji. Gotovo cela površina i
preliminarna snaga pripadaju kombinacionoj logici, kritični put prolazi kroz
LCG state update, a SS ugao sadrži veliki broj slew i fanout prekršaja.

Zato je ispravan tehnički zaključak:

> PCG32 `AREA 0` predstavlja validan pre-layout synthesis baseline koji
> prolazi 50 MHz, ali ima malu setup rezervu i nije electrical-clean. Veliki
> hardverski trošak dominantno potiče od 64-bitnog konstantnog množenja i
> sabiranja realizovanih u jednom taktu. Konačna procena pogodnosti za Tiny
> Tapeout zahteva jednak post-route tok za sva tri jezgra.

## 20. Sažeti pasus pogodan za diplomski rad

Za modul `pcg32_oneseq_core` izvršena je RTL sinteza pomoću LibreLane 2.4.2
`SynthesisExploration` toka, uz SKY130A PDK, biblioteku
`sky130_fd_sc_hd` i periodu takta od 20 ns. Svih devet ispitanih strategija
zadovoljilo je setup uslov od 50 MHz, dok je strategija `AREA 0` izabrana kao
zajednički referentni rezultat radi poređenja sa LFSR64 i xoroshiro64ss
jezgrima. Dobijeni netlist sadrži 5 998 standardnih ćelija i ima cell area
64 853.4496 µm², pri čemu kombinaciona logika čini 96.82% površine. Najgori
setup slack iznosi +0.571877 ns u SS uglu, a najgori hold slack +0.142826 ns
u FF uglu, uz TNS jednak nuli. Kritični setup put pripada 64-bitnoj LCG mreži
za ažuriranje stanja, što pokazuje da je konstantno množenje dominantno
ograničenje jedno-ciklusne hardverske realizacije. Iako su setup i hold uslovi
zadovoljeni, SS analiza prijavljuje 1 962 slew, 81 fanout i jedan kapacitivni
prekršaj, pa netlist nije electrical-clean. Preliminarna TT vectorless procena
snage od 579.0544 mW koristi se samo kao pre-layout uporedni indikator i ne
predstavlja signoff potrošnju. Konačna ocena zahteva placement, clock-tree
synthesis, routing, ekstrakciju parazita i jednaku post-route analizu sva tri
generatora.
