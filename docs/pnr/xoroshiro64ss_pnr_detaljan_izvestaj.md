# Detaljan izveštaj o PnR realizaciji modula `xoroshiro64ss_core`

**Projekat:** poređenje hardverskih implementacija PRNG algoritama
**Modul:** `xoroshiro64ss_core`
**Vrsta eksperimenta:** standalone, core-only, relative-floorplan full PnR
**Tehnologija:** SkyWater SKY130A, `sky130_fd_sc_hd`
**Alat i tok:** LibreLane 2.4.2, `Classic`
**Radna frekvencija:** 50 MHz (`CLOCK_PERIOD = 20 ns`)
**Datum obrade rezultata:** 28. avgust 2026.

## 1. Cilj i metodološko pravilo

Cilj je da se `xoroshiro64ss_core` realizuje pod istim zajedničkim uslovima kao ostali generatori i da se sačuvaju rezultati pogodni za kasnije PPA poređenje.

Zvanični rezultat zajedničkog eksperimenta jeste prvi run sa neizmenjenom zajedničkom konfiguracijom. Naknadne popravke se vode odvojeno kao optimizacioni ili rescue eksperimenti i ne smeju retroaktivno zameniti zajednički baseline.

Zbog toga se u ovom izveštaju čuvaju dva glavna rezultata:

| Rezultat | Namena | Status |
|---|---|---|
| `COMMON BASELINE` | fer poređenje sa drugim generatorima | **FAIL:** 3 antenna kršenja; prisutno i 6 max-fanout kršenja |
| `TARGETED ECO3` | dokaz da se antenna problem može precizno popraviti | **Antenna/DRC/LVS/timing clean**, ali i dalje 6 max-fanout kršenja |

Dakle, full PnR oba run-a se tehnički završio, ali nijedan nije potpuno čist prema najstrožem kriterijumu koji zahteva i nula max-fanout kršenja.

## 2. Zamrznuta zajednička konfiguracija

| Parametar | Vrednost |
|---|---:|
| `DESIGN_NAME` | `xoroshiro64ss_core` |
| RTL | `src/xoroshiro64ss_core.v` |
| PDK | `sky130A` |
| Standard-cell biblioteka | `sky130_fd_sc_hd` |
| LibreLane | `2.4.2` |
| Flow | `Classic` |
| `SYNTH_STRATEGY` | `AREA 0` |
| `CLOCK_PORT` | `clk_i` |
| `CLOCK_PERIOD` | `20 ns` |
| `FP_SIZING` | `relative` |
| `FP_CORE_UTIL` | `50%` |
| `FP_ASPECT_RATIO` | `1` |
| `PL_TARGET_DENSITY_PCT` | `60%` |
| `IO_DELAY_CONSTRAINT` | `20%` periodе, odnosno `4 ns` |
| `CLOCK_UNCERTAINTY_CONSTRAINT` | `0.25 ns` |
| `CLOCK_TRANSITION_CONSTRAINT` | `0.15 ns` |
| `MAX_TRANSITION_CONSTRAINT` | `0.75 ns` |
| `MAX_FANOUT_CONSTRAINT` | `10` |
| `OUTPUT_CAP_LOAD` | `33.442 fF` |
| `TIME_DERATING_CONSTRAINT` | `5%` |
| Implementacioni ugao | `nom_tt_025C_1v80` |
| STA uglovi | TT, SS i FF navedeni ispod |

Analizirani STA uglovi:

- `nom_tt_025C_1v80`
- `nom_ss_100C_1v60`
- `nom_ff_n40C_1v95`

## 3. Zajednički baseline run

**Run:** `relative_u50_d60_50mhz_docker`
**Putanja:** `pnr/xoroshiro64ss_core/runs/relative_u50_d60_50mhz_docker`

Tok je završio kompletnih 78 koraka i proizveo finalne fizičke prikaze i signoff izveštaje.

### 3.1. Površina i struktura dizajna

| Metrika | Vrednost |
|---|---:|
| Die dimenzije | `221.48 × 232.20 µm` |
| Die površina | `51,427.7 µm²` |
| Core dimenzije | `210.22 × 209.44 µm` |
| Core površina | `44,028.5 µm²` |
| Finalna standard-cell površina | `20,006.7 µm²` |
| Ostvarena standard-cell popunjenost core-a | `45.4403%` |
| Broj standard-cell instanci | `2,801` |
| Sekvencijalne ćelije | `97` |
| Višeulazne kombinacione ćelije | `1,856` |
| Inverteri | `33` |
| Opšti baferi | `1` |
| Timing-repair baferi | `166` |
| Hold baferi | `38` |
| Clock baferi | `9` |
| Clock inverteri | `7` |
| Filler ćelije | `3,154` |
| Tap ćelije | `632` |
| I/O pinovi | `39` |
| Makroi | `0` |

Filler i tap ćelije nisu funkcionalna logika i zato ih ne treba sabirati sa standard-cell površinom pri algoritamskom poređenju.

### 3.2. Post-route timing

| Ugao | Hold WNS [ns] | Hold TNS [ns] | Setup WNS [ns] | Setup TNS [ns] | Setup/hold status |
|---|---:|---:|---:|---:|---|
| `nom_tt_025C_1v80` | `+0.314999` | `0` | `+10.512235` | `0` | PASS |
| `nom_ss_100C_1v60` | `+0.883365` | `0` | `+1.133300` | `0` | PASS |
| `nom_ff_n40C_1v95` | `+0.109180` | `0` | `+10.999970` | `0` | PASS |
| **Overall** | **`+0.109180`** | **`0`** | **`+1.133300`** | **`0`** | **PASS** |

Najkritičniji setup ugao je SS, a najkritičniji hold ugao je FF. Dizajn zadovoljava cilj od 50 MHz sa pozitivnom rezervom u sva tri ugla.

### 3.3. Routing, signoff i električke provere

| Provera/metrika | Rezultat |
|---|---:|
| Routed wirelength | `48,319 µm` |
| Procena wirelength-a pre finalnog rutiranja | `45,242.3 µm` |
| Broj via | `13,577` |
| Finalni routing overflow | `0` |
| KLayout/Magic DRC | `0` kršenja — PASS |
| LVS | circuits match uniquely — PASS |
| Setup | PASS |
| Hold | PASS |
| Max slew | `0` — PASS |
| Max capacitance | `0` — PASS |
| Max fanout | `6` — **FAIL prema ograničenju 10** |
| Antenna | `3` neta / `3` pina — **FAIL** |
| Najgori VPWR IR drop | `0.0127969 V` |
| Najgori VGND IR drop | `0.0103665 V` |

Šest max-fanout kršenja pojavljuje se u sva tri STA ugla i uglavnom je vezano za clock-tree baferе. Ona se moraju navesti u konačnoj metodologiji; ne smeju se sakriti samo zato što setup, hold, slew i capacitance prolaze.

### 3.4. Uzrok antenna neuspeha

Finalna antenna provera je identifikovala tačno tri problematična pina:

| Net | Pin | Sloj | Odnos | Parcijalna površina | Dozvoljeno | Status |
|---|---|---|---:|---:|---:|---|
| `net104` | `fanout103/A` | `met1` | `2.02` | `809.01` | `400` | VIOLATED |
| `net2` | `fanout116/A` | `met1` | `1.56` | `624.10` | `400` | VIOLATED |
| `net1` | `fanout128/A` | `met1` | `1.36` | `545.74` | `400` | VIOLATED |

Ovo je lokalizovan fizički problem rutiranja, a ne funkcionalna greška RTL algoritma. Ipak, zajednički baseline se zbog njega mora označiti kao `FAIL_ANTENNA_3`.

### 3.5. Vectorless procena potrošnje

| Komponenta | LibreLane vrednost [W] | Približno [mW] |
|---|---:|---:|
| Internal | `0.0186581761` | `18.6582` |
| Switching | `0.0226840042` | `22.6840` |
| Leakage | `2.23284e-8` | `0.0000223` |
| **Total** | **`0.0413422026`** | **`41.3422`** |

Ovo je vectorless procena i služi samo kao sekundarna indikacija. Za zaključke o energiji po generisanoj 32-bitnoj reči potrebno je koristiti isti post-route VCD/SAIF scenario za sva tri generatora.

## 4. Pokušaji otklanjanja antenna kršenja

| Pokušaj | Izmena | Antenna rezultat | Neželjeni efekat | Odluka |
|---|---|---:|---|---|
| `antfix1` | `GRT_ANTENNA_ITERS=10`, `GRT_ANTENNA_MARGIN=15` | 3 kršenja; ubačena 1 dioda | nema stvarnog poboljšanja finalnog rezultata | ODBAČENO |
| `antfix2` | heurističko ubacivanje dioda | 0 kršenja | 821 antenna ćelija, 22,061.2 µm², 3,622 instance, 12 max-slew i 82 max-fanout kršenja | ODBAČENO |
| built-in ECO | `Odb.InsertECODiodes` | nije završen | OpenROAD `GRT-0226: Type2 ripup not type L` tokom inkrementalnog `updateRoutes(True)` | ODBAČENO |
| `eco3_only` | 3 ciljane diode + novo standardno globalno rutiranje | 0 kršenja | samo +3 instance i +7.5 µm²; ostaje 6 max-fanout kršenja | PRIHVAĆEN kao rescue rezultat |

Heuristički pokušaj je pokazao zašto nasumično/agresivno ubacivanje velikog broja dioda nije dobar konačni metod: rešio je antenna proveru, ali je ozbiljno povećao površinu i proizveo nova električka kršenja.

## 5. Ciljani ECO rezultat

**Run:** `relative_u50_d60_50mhz_eco3_only`
**Putanja:** `pnr/xoroshiro64ss_core/runs/relative_u50_d60_50mhz_eco3_only`

Napravljen je lokalni LibreLane dodatak sa korakom `Odb.InsertECODiodesOnly`. On je ubacio po jednu antenna ćeliju na svaki od tri prethodno identifikovana pina:

- `fanout103/A`
- `fanout116/A`
- `fanout128/A`

Posle ubacivanja ćelija nije korišćen problematični inkrementalni `updateRoutes(True)`. Tok je nastavio standardnim globalnim i detaljnim rutiranjem, što je uklonilo grešku `GRT-0226`.

### 5.1. ECO signoff rezultat

| Provera | Rezultat |
|---|---:|
| Antenna | `0` netova / `0` pinova — PASS |
| DRC | `0` — PASS |
| LVS | PASS |
| Setup | PASS u TT/SS/FF |
| Hold | PASS u TT/SS/FF |
| Max slew | `0` — PASS |
| Max capacitance | `0` — PASS |
| Max fanout | `6` — ostaje FAIL prema ograničenju 10 |
| Broj ciljano dodatih antenna ćelija | `3` |

U `metrics.csv` polje `design__instance__count__class:antenna_cell` pravilno pokazuje `3`. Polje `antenna_diodes_count` ostaje `0` zato što su ćelije ubačene prilagođenim ECO korakom, a ne LibreLane-ovim standardnim brojačem dioda. To nije dokaz da diode nisu ubačene; fizički rezultat i klasifikacija instanci potvrđuju tri dodatne antenna ćelije.

### 5.2. ECO post-route timing

| Ugao | Hold WNS [ns] | Hold TNS [ns] | Setup WNS [ns] | Setup TNS [ns] | Status |
|---|---:|---:|---:|---:|---|
| `nom_tt_025C_1v80` | `+0.3172` | `0` | `+10.5326` | `0` | PASS |
| `nom_ss_100C_1v60` | `+0.8871` | `0` | `+1.1544` | `0` | PASS |
| `nom_ff_n40C_1v95` | `+0.1107` | `0` | `+10.9999` | `0` | PASS |
| **Overall** | **`+0.1107`** | **`0`** | **`+1.1544`** | **`0`** | **PASS** |

## 6. Direktno poređenje baseline-a i ciljanog ECO-a

| Metrika | Common baseline | Targeted ECO3 | Promena |
|---|---:|---:|---:|
| Standard-cell instance | `2,801` | `2,804` | `+3` (`+0.1071%`) |
| Standard-cell površina | `20,006.7 µm²` | `20,014.2 µm²` | `+7.5 µm²` (`+0.0375%`) |
| Antenna ćelije | `0` | `3` | `+3` |
| Antenna kršenja | `3` | `0` | `-3` |
| Max-fanout kršenja | `6` | `6` | bez promene |
| Overall hold WNS | `+0.109180 ns` | `+0.1107 ns` | približno `+0.00152 ns` |
| Overall setup WNS | `+1.133300 ns` | `+1.1544 ns` | približno `+0.02110 ns` |
| Internal power | `0.0186581761 W` | `0.0186569262 W` | `-0.0067%` |
| Switching power | `0.0226840042 W` | `0.0225992929 W` | `-0.3734%` |
| Leakage power | `2.23284e-8 W` | `2.23436e-8 W` | `+0.0682%` |
| Total vectorless power | `0.0413422026 W` | `0.0412562415 W` | `-0.2079%` |

Male promene timing-a i vectorless power-a nisu dokaz da diode poboljšavaju brzinu ili potrošnju. One su dovoljno male da ih treba tretirati kao posledicu drugačijeg placement/routing rešenja i ograničene preciznosti vectorless procene. Robustan zaključak je samo da su tri ciljane ćelije uklonile sva tri antenna kršenja uz zanemarljiv površinski trošak.

## 7. Ograničenja i upozorenja

1. **Max fanout nije potpuno čist.** I baseline i ciljani ECO imaju šest kršenja ograničenja `MAX_FANOUT_CONSTRAINT=10`. Zato targeted ECO nije potpuno constraint-clean iako prolazi antenna, DRC, LVS, setup, hold, max slew i max capacitance.
2. **Power je vectorless.** Nije dovoljan za konačno rangiranje energije. Potreban je isti activity-based VCD/SAIF postupak za sva tri jezgra.
3. **Sedam clock-load drivera je bez parazitske anotacije.** To se odnosi na generičke `clkload` elemente u STA izveštaju i treba ga jednako tretirati kod svih generatora.
4. **IR-drop izveštaj je kontekstualan.** Upozorenje za `VSRC_LOC_FILES` je očekivano za standalone core koji nije finalno integrisan u top-level čip.
5. **Ovo nije Tiny Tapeout absolute-tile implementacija.** Rezultat je standalone relative-floorplan eksperiment namenjen međusobnom poređenju jezgara.

## 8. Sačuvani artefakti

Kurirani baseline rezultati:

```text
pnr/results/xoroshiro64ss_core/baseline_common/
├── config.json
├── metrics.csv
├── metrics.json
├── resolved_config.json
├── postroute_sta_summary.rpt
├── postroute_checks_nom_tt_025C_1v80.rpt
├── postroute_checks_nom_ss_100C_1v60.rpt
├── postroute_checks_nom_ff_n40C_1v95.rpt
└── postroute_antenna.rpt
```

Kurirani ciljani ECO rezultati:

```text
pnr/results/xoroshiro64ss_core/eco3_targeted/
├── config.json
├── metrics.csv
├── metrics.json
├── resolved_config.json
├── postroute_sta_summary.rpt
├── postroute_checks_nom_tt_025C_1v80.rpt
├── postroute_checks_nom_ss_100C_1v60.rpt
├── postroute_checks_nom_ff_n40C_1v95.rpt
└── postroute_antenna.rpt
```

Lokalni dodatak kojim je izveden ciljani ECO:

```text
librelane_plugin_targeted_eco/
├── __init__.py
└── insert_eco_diodes_only.py
```

## 9. Konačni zaključci

1. `xoroshiro64ss_core` uspešno prolazi kompletan synthesis + placement + CTS + routing + signoff tok pri 50 MHz u sva tri analizirana PVT ugla.
2. Zajednički baseline prolazi DRC, LVS, setup, hold, max slew i max capacitance, ali ima tri finalna antenna kršenja i šest max-fanout kršenja. Zato je njegov zvanični status za fer poređenje `FAIL_ANTENNA_3`.
3. Antenna problem je lokalizovan na tri konkretna pina i može se ukloniti sa samo tri ciljano ubačene antenna ćelije.
4. Ciljani ECO povećava standard-cell površinu za samo `7.5 µm²`, odnosno približno `0.0375%`, i zadržava pozitivne setup/hold margine u svim uglovima.
5. Heurističko ubacivanje 821 antenna ćelije jeste uklonilo antenna kršenja, ali je proizvelo 12 max-slew i 82 max-fanout kršenja i zato nije prihvatljivo rešenje.
6. Ciljani ECO je antenna-clean i manufacturability/timing clean, ali ostaje šest max-fanout kršenja. Njih treba rešavati zasebno ili eksplicitno zadržati kao poznato ograničenje metodologije.
7. Za kasnije poređenje sa LFSR64 i PCG32 koriste se **baseline** PPA metrike. ECO rezultat se prikazuje odvojeno kao dokaz popravljivosti i kao mera minimalnog troška antenna popravke.
