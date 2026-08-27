# Završno poređenje RTL sinteze: `lfsr64_core`, `xoroshiro64ss_core` i `pcg32_oneseq_core`

| Stavka | Vrednost |
|---|---|
| Projekat | Tiny Tapeout digitalna kockica — poređenje PRNG jezgara |
| Jezgra | `lfsr64_core`, `xoroshiro64ss_core`, `pcg32_oneseq_core` |
| Vrsta analize | Pre-layout RTL sinteza i multi-corner STA |
| Alat i tok | LibreLane `2.4.2`, `SynthesisExploration` |
| Tehnologija | SKY130A |
| Biblioteka | `sky130_fd_sc_hd` |
| Ciljna učestanost | 50 MHz |
| Perioda takta | 20 ns |
| Zajednički baseline | `AREA 0` |
| Datum poređenja | 27. avgust 2026. |
| Status | Sva tri `AREA 0` netlista prolaze pre-layout setup i hold; nijedan još nije post-route/signoff rezultat |

## 1. Svrha i obim dokumenta

Ovaj dokument objedinjuje sve zaključke dobijene tokom kontrolisane RTL sinteze tri nekriptografska generatora pseudoslučajnih brojeva:

- 64-bitnog Galois LFSR-a;
- 64-bitnog xoroshiro64** generatora;
- PCG32 generatora sa 64-bitnim LCG stanjem i XSH-RR izlaznom transformacijom.

Cilj nije samo da se navedu površina i slack, već da se objasni:

1. koliko standardnih ćelija zahteva svaka konkretna mikroarhitektura;
2. koji deo algoritma određuje površinu i kritični put;
3. koliko je svaki rezultat osetljiv na strategiju sinteze;
4. da li zadovoljava cilj od 50 MHz u tri PVT ugla;
5. kakvi električni prekršaji ostaju pre fizičke optimizacije;
6. kolika je preliminarna vectorless procena snage i izvedeni power/throughput pokazatelj po reči;
7. kako se apsolutni trošak menja kada se normalizuje izlaznim protokom;
8. koji generator je povoljniji za različite hardverske ciljeve.

Porede se **algoritmi zajedno sa izabranim RTL mikroarhitekturama**. Rezultati ne dokazuju da će svaka moguća implementacija istog algoritma imati iste odnose.

## 2. Najvažniji zaključak unapred

Pre-layout sinteza pokazuje jasan rast apsolutnog hardverskog troška:

```text
LFSR64  ->  xoroshiro64ss  ->  jedno-ciklusni PCG32
```

Za zajedničku strategiju `AREA 0`:

| Metrika | LFSR64 | xoroshiro64ss | PCG32 |
|---|---:|---:|---:|
| Standardne ćelije | 381 | 1 987 | 5 998 |
| Cell area | 5 058.6016 µm² | 22 142.4864 µm² | 64 853.4496 µm² |
| Udeo kombinacione area | 44.08% | 90.68% | 96.82% |
| Najgori setup slack (WS) | +9.993491 ns | +1.949115 ns | +0.571877 ns |
| Najgori hold slack (WS) | +0.045761 ns | +0.097219 ns | +0.142826 ns |
| Održivi protok na 50 MHz | 1.5625 Mword/s | 50 Mword/s | 50 Mword/s |
| TT vectorless snaga | 0.3280666 mW | 44.34212 mW | 579.0544 mW |

Iz ovoga proizlazi:

- LFSR64 je apsolutno najmanji, najjednostavniji i ima najnižu preliminarnu snagu i najniži izvedeni power/throughput pokazatelj po reči, ali sklapa jednu 32-bitnu reč tokom 32 takta.
- xoroshiro64ss daje jednu reč po taktu i ima najbolji protok po jedinici cell area. Veći trošak potiče pre svega od `**` izlaznog scramblera.
- PCG32 takođe daje jednu reč po taktu, ali je 2.929 puta veći od xoroshiro jezgra i ima približno 13.06 puta veću vectorless snagu. Glavni uzrok je 64-bitno konstantno množenje i sabiranje u jednom taktu.
- Sva tri `AREA 0` rezultata prolaze pre-layout setup i hold na 50 MHz, ali nijedan nije electrical-clean niti fizički signoff-ready.
- Prema ključnim hardverskim metrikama, xoroshiro je bolji kompromis od PCG32 kada je potreban protok od jedne reči po taktu. To nije rangiranje statističkog kvaliteta sekvenci.

## 3. Zajednički i kontrolisani uslovi

| Parametar | Vrednost za sva tri jezgra |
|---|---|
| LibreLane | `2.4.2` |
| Tok | `SynthesisExploration` |
| PDK | `sky130A` |
| Standard-cell biblioteka | `sky130_fd_sc_hd` |
| Open-PDKs snapshot | `0fe599b2afb6708d281543108caf8310912f54af` |
| Clock port | `clk_i` |
| Clock period | 20 ns |
| Clock frequency | 50 MHz |
| Glavna strategija poređenja | `AREA 0` |
| Paralelizam | `-j 1` |
| PnR/CTS/routing | Nisu urađeni |
| Power stimulus | Vectorless, bez VCD/SAIF aktivnosti |

Korišćeni su isti Liberty PVT uglovi:

| Ugao | Proces | Temperatura | Napon | Tipična uloga |
|---|---|---:|---:|---|
| `nom_tt_025C_1v80` | TT | +25 °C | 1.80 V | nominalni uslovi |
| `nom_ss_100C_1v60` | SS | +100 °C | 1.60 V | najnepovoljniji setup |
| `nom_ff_n40C_1v95` | FF | −40 °C | 1.95 V | najnepovoljniji hold |

Naponi 1.60 V i 1.95 V nisu preporučeni naponi Tiny Tapeout pločice. To su karakterizacione tačke standardnih ćelija koje se koriste za proveru ponašanja u sporom i brzom uglu. Nominalno Tiny Tapeout digitalno napajanje je 1.8 V.

### 3.1. Generički SDC

Za sva tri jezgra korišćen je LibreLane fallback `base.sdc`, jer posebni `PNR_SDC_FILE` i `SIGNOFF_SDC_FILE` nisu definisani. U izveštajima se pojavljuju:

- ulazno kašnjenje od 4 ns;
- izlazno kašnjenje od 4 ns;
- clock uncertainty od 0.25 ns;
- clock transition od 0.15 ns;
- generičko izlazno opterećenje;
- idealna clock mreža bez CTS kašnjenja.

Isto ograničenje čini poređenje međusobno doslednim, ali nije zamena za SDC budućeg fizičkog top-level dizajna.

### 3.2. Šta predstavljaju `AREA` i `DELAY` strategije

Strategije `AREA 0`–`AREA 3` i `DELAY 0`–`DELAY 4` predstavljaju unapred definisane Yosys/ABC recepte za optimizaciju i tehnološko mapiranje.

One:

- nisu Tiny Tapeout strategije;
- nisu osobina Codespace okruženja;
- nisu univerzalni nivoi kvaliteta sinteze;
- ne garantuju da veći broj daje manju površinu ili bolji tajming;
- mogu imati vrlo različit rezultat za različite logičke strukture.

## 4. Arhitekture koje se stvarno porede

| Jezgro | Algoritamsko stanje | Izlaz | Dominantne operacije | Mikroarhitektura izlaza |
|---|---:|---:|---|---|
| `lfsr64_core` | 64 bita | 32 bita | pomeranje i uslovni XOR sa povratnom maskom | serijsko sklapanje reči tokom 32 takta |
| `xoroshiro64ss_core` | 64 bita | 32 bita | XOR, fiksne rotacije i `**` scrambler sa konstantnim množenjem | kompletna reč u jednom taktu |
| `pcg32_oneseq_core` | 64 bita | 32 bita | 64-bitni LCG multiply-add, xorshift i promenljiva rotacija | kompletna reč u jednom taktu |

### 4.1. LFSR64

Jedan Galois LFSR korak zahteva pomeranje i uslovni XOR sa maskom. Kombinaciona povratna mreža je mala, ali konkretni RTL sadrži dodatne registre za:

- 64-bitno stanje;
- parcijalno sklapanje 32-bitne reči;
- izlazni registar;
- brojač i handshake kontrolu.

Zato sintetizovano jezgro nije samo minimalni 64-bitni shift registar.

### 4.2. xoroshiro64ss

Tranzicija stanja koristi XOR i fiksne rotacije. Fiksna rotacija je uglavnom promena povezivanja bitova i sama ne zahteva barrel shifter. Glavni trošak je `**` izlazna funkcija:

```text
rotl32(s0 * konstanta, 5) * 5
```

Konstantno množenje sintetizovano je u mrežu standardnih ćelija, bez posebnog multiplier makroa. Ova mreža određuje kritični setup put.

### 4.3. PCG32

PCG32 ažurira stanje kao:

```text
novo_stanje = staro_stanje * multiplier + increment
```

Iz starog stanja formira se 32-bitni XSH-RR izlaz pomoću xorshift-a i promenljive rotacije. U izabranoj realizaciji sve se računa u jednom taktu, pa 64-bitni multiply-add postaje velika kombinaciona mreža.

Glavni sintezni zaključak jeste da softverski elegantna 64-bitna aritmetička operacija može biti veoma skupa kada se realizuje kao potpuno kombinacioni ASIC datapath.

## 5. Rezultati svih devet strategija

### 5.1. Broj ćelija i cell area

| Strategija | LFSR ćelije | LFSR area [µm²] | Xoro ćelije | Xoro area [µm²] | PCG ćelije | PCG area [µm²] |
|---|---:|---:|---:|---:|---:|---:|
| `AREA 0` | 381 | 5 058.6016 | 1 987 | 22 142.4864 | 5 998 | 64 853.4496 |
| `AREA 1` | 380 | 5 052.3456 | 1 998 | 22 004.8544 | 5 943 | 64 560.6688 |
| `AREA 2` | 382 | 5 069.8624 | 1 899 | 21 401.7760 | 5 976 | 64 559.4176 |
| `AREA 3` | 538 | 5 814.3264 | 3 608 | 28 573.6544 | 11 206 | 84 409.7056 |
| `DELAY 0` | 422 | 5 717.9840 | 3 369 | 35 188.7488 | 10 866 | 110 850.0640 |
| `DELAY 1` | 368 | 5 098.6400 | 3 274 | 32 956.6080 | 10 708 | 105 240.9344 |
| `DELAY 2` | 437 | 5 639.1584 | 3 321 | 33 360.7456 | 10 770 | 105 349.7888 |
| `DELAY 3` | 422 | 5 717.9840 | 3 472 | 36 013.2896 | 10 731 | 109 647.6608 |
| `DELAY 4` | 584 | 6 592.5728 | 2 688 | 28 456.0416 | 8 799 | 90 325.3792 |

### 5.2. Najgori setup slack, TNS i status na 50 MHz

| Strategija | LFSR slack / TNS [ns] | Xoro slack / TNS [ns] | PCG slack / TNS [ns] |
|---|---:|---:|---:|
| `AREA 0` | +9.993491 / 0 — MET | +1.949115 / 0 — MET | +0.571877 / 0 — MET |
| `AREA 1` | +9.883508 / 0 — MET | −1.111548 / −4.298491 — VIOLATED | +1.846543 / 0 — MET |
| `AREA 2` | +9.953978 / 0 — MET | −0.130683 / −0.130683 — VIOLATED | +0.835083 / 0 — MET |
| `AREA 3` | +8.642673 / 0 — MET | +9.279762 / 0 — MET | +9.565873 / 0 — MET |
| `DELAY 0` | +8.353116 / 0 — MET | +5.556994 / 0 — MET | +5.471037 / 0 — MET |
| `DELAY 1` | +9.366459 / 0 — MET | +6.493143 / 0 — MET | +5.900320 / 0 — MET |
| `DELAY 2` | +8.484931 / 0 — MET | +5.434911 / 0 — MET | +5.957278 / 0 — MET |
| `DELAY 3` | +8.353116 / 0 — MET | +5.703918 / 0 — MET | +5.456525 / 0 — MET |
| `DELAY 4` | +9.227755 / 0 — MET | +1.919666 / 0 — MET | +0.480862 / 0 — MET |

### 5.3. Glavni zaključci exploration analize

| Jezgro | Najmanje ćelija | Najmanja area | Najbolji setup slack | Broj strategija koje prolaze |
|---|---|---|---|---:|
| LFSR64 | `DELAY 1`: 368 | `AREA 1`: 5 052.3456 µm² | `AREA 0`: +9.993491 ns | 9/9 |
| xoroshiro64ss | `AREA 2`: 1 899 | `AREA 2`: 21 401.7760 µm² | `AREA 3`: +9.279762 ns | 7/9 |
| PCG32 | `AREA 1`: 5 943 | `AREA 2`: 64 559.4176 µm² | `AREA 3`: +9.565873 ns | 9/9 |

Zaključci po jezgru:

- **LFSR64:** sve strategije prolaze sa velikom rezervom. Mala i plitka logika čini rezultat relativno neosetljivim na mapiranje.
- **xoroshiro64ss:** `AREA 1` i `AREA 2` jesu manje, ali ne prolaze 20 ns. `AREA 0` je najmanji timing-clean rezultat među ispitivanim strategijama i zajednički baseline.
- **PCG32:** svih devet strategija prolazi. `AREA 1` ima manje ćelija i bolji slack od `AREA 0`, a `AREA 2` je 0.453% manje površine i takođe ima bolji slack. Zato `AREA 0` nije pojedinačni PCG optimum, već fer zajednički baseline.
- **Veći indeks nije bolji:** PCG `DELAY 4` je istovremeno veći i ima manji slack od `AREA 0`; LFSR delay strategije takođe ne daju nužno bolji tajming.
- **Cena velike rezerve:** `AREA 3` daje najbolji PCG setup slack, ali je približno 30.15% veća od PCG `AREA 0`.

LibreLane ove pozitivne vrednosti vodi kao `Worst Slack`, odnosno `WS`. Pošto nema negativnih putanja, odvojena negative-slack-only `WNS` polja u state fajlovima iznose 0. U ovom dokumentu zato se pozitivne vrednosti nazivaju **najgorim slack-om**, a ne WNS-om.

## 6. Zašto je glavno poređenje zasnovano na `AREA 0`

Za svaki generator mogla se izabrati druga strategija koja daje lokalno najbolju metriku. To bi, međutim, promenilo dva faktora odjednom: i algoritam i optimizacioni recept.

`AREA 0` je zadržana zato što:

- predstavlja unapred dogovoreni zajednički baseline;
- sva tri `AREA 0` rezultata prolaze cilj od 50 MHz;
- koristi isti optimizacioni recept za sva jezgra;
- omogućava da se razlike prvenstveno pripišu RTL strukturi;
- za sva tri postoje isti kurirani synthesis/STA/power artefakti.

`AREA 0` zato treba opisivati kao **najbolji zajednički eksperimentalni baseline**, a ne kao apsolutno optimalnu strategiju svakog jezgra.

## 7. Jedinstvena `AREA 0` tabela

| Metrika | `lfsr64_core` | `xoroshiro64ss_core` | `pcg32_oneseq_core` |
|---|---:|---:|---:|
| Algoritamsko stanje | 64 bita | 64 bita | 64 bita |
| Izlaz | 32 bita | 32 bita | 32 bita |
| Portovi / port-bitovi | 6 / 37 | 6 / 37 | 6 / 37 |
| Standardne ćelije | 381 | 1 987 | 5 998 |
| Flip-flopovi | 133 | 97 | 97 |
| Kombinacione ćelije | 248 | 1 890 | 5 901 |
| Ukupna cell area | 5 058.6016 µm² | 22 142.4864 µm² | 64 853.4496 µm² |
| Sekvencijalna area | 2 828.9632 µm² | 2 063.2288 µm² | 2 063.2288 µm² |
| Udeo sekvencijalne area | 55.92% | 9.32% | 3.18% |
| Kombinaciona area | 2 229.6384 µm² | 20 079.2576 µm² | 62 790.2208 µm² |
| Udeo kombinacione area | 44.08% | 90.68% | 96.82% |
| Memorije / latch-evi | 0 / 0 | 0 / 0 | 0 / 0 |
| Yosys strukturni problemi | 0 | 0 | 0 |
| Najgori setup slack (WS) | +9.993491 ns | +1.949115 ns | +0.571877 ns |
| Setup TNS | 0 ns | 0 ns | 0 ns |
| Najgori hold slack (WS) | +0.045761 ns | +0.097219 ns | +0.142826 ns |
| Hold TNS | 0 ns | 0 ns | 0 ns |
| SS max-slew prekršaji | 347 | 441 | 1 962 |
| SS max-fanout prekršaji | 6 | 33 | 81 |
| SS max-cap prekršaji | 2 | 1 | 1 |
| TT vectorless ukupna snaga | 0.3280666 mW | 44.34212 mW | 579.0544 mW |
| Latencija reči | 32 takta | 1 takt | 1 takt |
| Održivi protok | 1.5625 Mword/s | 50 Mword/s | 50 Mword/s |
| Bitni protok | 50 Mbit/s | 1.6 Gbit/s | 1.6 Gbit/s |

## 8. Površina i struktura netlista

### 8.1. Relativni odnosi

| Odnos | Xoro/LFSR | PCG/Xoro | PCG/LFSR |
|---|---:|---:|---:|
| Ukupna cell area | 4.377× | 2.929× | 12.820× |
| Ukupan broj ćelija | 5.215× | 3.019× | 15.743× |
| Kombinaciona area | 9.006× | 3.127× | 28.162× |
| Kombinacione ćelije | 7.621× | 3.122× | 23.794× |
| Sekvencijalna area | 0.729× | 1.000× | 0.729× |

### 8.2. Najvažnija strukturna paralela

xoroshiro i PCG32 imaju:

- isti 64-bitni algoritamski state register;
- isti 32-bitni izlazni registar;
- isti 1-bitni `valid_o` registar;
- tačno 97 flip-flopova;
- identičnu sekvencijalnu cell area od 2 063.2288 µm².

Ipak, PCG32 je 2.929 puta veći. Cela dodatna cena potiče iz kombinacione funkcije:

```text
xoroshiro kombinaciona area = 20 079.2576 µm²
PCG32 kombinaciona area     = 62 790.2208 µm²
```

To direktno dokazuje da širina stanja sama ne određuje veličinu generatora.

### 8.3. Dominantna logika

- LFSR64 ima 248 kombinacionih ćelija. Više od polovine njegove cell area pripada registrima i kontroli.
- xoroshiro ima 1 890 kombinacionih ćelija. U netlistu je najmanje 368 XNOR2 i 229 XOR2 ćelija; kombinaciona logika čini 90.68% površine.
- PCG32 ima 5 901 kombinacionu ćeliju, uključujući 1 244 XNOR2, 613 XOR2 i 135 eksplicitnih MUX2/MUX4 ćelija; kombinaciona logika čini 96.82% površine.

Smanjenje broja registara ne bi rešilo glavni PCG32 problem. Za smanjenje kombinacione površine prirodan kandidat je višeciklusni/iterativni množilac uz manji protok. Pipeline prvenstveno skraćuje kombinacioni put i poboljšava timing, ali dodaje registre i ne garantuje manju ukupnu površinu ili snagu.

### 8.4. Šta cell area nije

Cell area je zbir bibliotečkih površina mapiranih standardnih ćelija. Ona ne uključuje:

- whitespace i ciljnu utilization vrednost;
- tap, filler i decap ćelije;
- clock tree;
- bafere i jače ćelije dodate tokom fizičke optimizacije;
- routing resurse i blokadu vodova;
- konačnu Tiny Tapeout tile površinu.

Zato 5 058.6016, 22 142.4864 i 64 853.4496 µm² nisu konačne fizičke površine makroa.

## 9. Setup analiza u tri PVT ugla

| PVT ugao | LFSR setup slack [ns] | Xoro setup slack [ns] | PCG setup slack [ns] |
|---|---:|---:|---:|
| TT, +25 °C, 1.80 V | +10.7809 | +10.8851 | +10.5383 |
| SS, +100 °C, 1.60 V | **+9.9935** | **+1.9491** | **+0.571877** |
| FF, −40 °C, 1.95 V | +11.0809 | +11.1573 | +11.2332 |

Sva tri jezgra imaju setup TNS 0 ns i nemaju negativne `AREA 0` setup putanje.

SS ugao pokazuje najveću razliku:

- LFSR ostaje veoma komforan;
- xoroshiro zadržava oko 1.95 ns rezerve;
- PCG32 zadržava samo 0.572 ns, odnosno 2.86% periode.

Velike aritmetičke mreže xoroshiro i PCG jezgra mnogo su osetljivije na usporenje standardnih ćelija u SS uglu nego plitka LFSR struktura.

## 10. Kritični setup putevi

| Jezgro | Najgori ugao | Funkcionalni put | Kombinaciona dubina | Slack | Tumačenje |
|---|---|---|---:|---:|---|
| LFSR64 | SS | `rst_ni -> AND2B -> ready_o` | 1 ćelija na najgorem I/O putu | +9.993491 ns | I/O kontrolni put, nije LFSR feedback |
| xoroshiro64ss | SS | `s0` registar -> `**` scrambler -> `random_o` registar | 31 ćelija | +1.949115 ns | izlazni scrambler je setup usko grlo |
| PCG32 | SS | `state_reg[0]` -> LCG multiply-add -> `_11896_/D` (Q mreža `rotation_wire[4]`, RTL alias `state_reg[63]`) | 27 ćelija | +0.571877 ns | 64-bitno ažuriranje stanja je setup usko grlo |

### 10.1. LFSR64

Najgori globalni put je:

```text
rst_ni -> ready_o
```

On uključuje generičko ulazno i izlazno kašnjenje i ne prolazi kroz algoritamsku povratnu logiku. Zbog toga se iz `20 ns − 9.993491 ns` ne sme računati LFSR `Fmax`.

### 10.2. xoroshiro64ss

Najgori put ide od `s0_wire[2]` kroz konstantno množenje, rotaciju i završno množenje sa pet do `random_o[25]`.

```text
data arrival  = 17.544800 ns
data required = 19.493914 ns
slack         = +1.949115 ns
```

Gruba pre-layout indikacija je:

```text
Tmin,approx = 20 - 1.949115 = 18.050885 ns
Fmax,approx = 55.40 MHz
```

### 10.3. PCG32

Najgori put ide od `state_reg[0]` kroz LCG mrežu do `_11896_/D`. Q mreža tog
registra zove se `rotation_wire[4]`, što je optimizovani alias RTL bita
`state_reg[63]`.

```text
data arrival  = 18.924706 ns
data required = 19.496582 ns
slack         = +0.571877 ns
```

Gruba pre-layout indikacija je:

```text
Tmin,approx = 20 - 0.571877 = 19.428123 ns
Fmax,approx = 51.47 MHz
```

Ove dve `Fmax` vrednosti nisu signoff rezultati. Potreban je clock-period sweep i post-route STA, jer druga perioda može promeniti mapiranje i kritični put.

## 11. Hold analiza

| PVT ugao | LFSR hold slack [ns] | Xoro hold slack [ns] | PCG hold slack [ns] |
|---|---:|---:|---:|
| TT, +25 °C, 1.80 V | +0.2107 | +0.3025 | +0.3501 |
| SS, +100 °C, 1.60 V | +0.6981 | +0.8973 | +0.8968 |
| FF, −40 °C, 1.95 V | **+0.045761** | **+0.097219** | **+0.142826** |

Sva tri jezgra imaju hold TNS 0 ns. Najgore hold putanje su kratke lokalne povratne ili shift putanje:

| Jezgro | Najgori hold put | Kombinaciona logika | Hold slack |
|---|---|---|---:|
| LFSR64 | `state_reg[1]` do sledećeg state registra | jedna mala `A21O` struktura | +45.761 ps |
| xoroshiro64ss | `s1_wire[28]` nazad do istog funkcionalnog registra | jedna `o211a_2` ćelija | +97.219 ps |
| PCG32 | `random_o[17]` nazad do istog registra | `a21oi_2` + `nor2_2` | +142.826 ps |

PCG ima najveću pre-layout hold rezervu, ali to nije pokazatelj veće maksimalne frekvencije. Hold rezultat je veoma osetljiv na clock skew, CTS i fizičko rutiranje.

## 12. Električni prekršaji

Brojevi u sledećoj tabeli predstavljaju:

```text
max-slew / max-fanout / max-capacitance broj prekršaja
```

| Ugao | LFSR64 | xoroshiro64ss | PCG32 |
|---|---:|---:|---:|
| SS | `347 / 6 / 2` | `441 / 33 / 1` | `1 962 / 81 / 1` |
| TT | `307 / 6 / 1` | `169 / 33 / 1` | `362 / 81 / 0` |
| FF | `98 / 6 / 1` | `101 / 33 / 1` | `0 / 81 / 0` |

LFSR `area0_sta_state.json` potvrđuje šest max-fanout prekršaja u svakom uglu. Pojedinačni fanout-i reset mreže ipak su veliki, pa mali broj violating mreža ne znači da problem nije značajan.

### 12.1. Broj prekršaja nije isto što i težina najgoreg prekršaja

| Jezgro | Najveći dokumentovani fanout | Najgori dokumentovani slew |
|---|---:|---:|
| LFSR64 | `rst_ni`: oko 104; izvedeni reset: oko 97 | oko 3.998 ns |
| xoroshiro64ss | `next_i`: 100; `rst_ni`: 67 | 2.027454 ns |
| PCG32 | interna mreža: 68; `rst_ni`: 60 | 1.487774 ns |

PCG32 ima daleko najveći broj violating tačaka, ali nema najveći pojedinačni fanout niti najsporiju pojedinačnu ivicu. Zato broj prekršaja treba koristiti kao meru rasprostranjenosti problema, ne kao jedinu meru težine.

### 12.2. Capacitance

- xoroshiro jedini cap prekršaj pripada `next_i`; u SS uglu kapacitivnost je 0.284430 naspram limita 0.200000.
- PCG jedini SS cap prekršaj je mali: 0.081330 naspram limita 0.080576.
- LFSR ima do dva cap prekršaja, dominantno povezana sa reset mrežom.

Isti broj cap prekršaja zato ne znači jednaku veličinu prekoračenja.

### 12.3. Ograničenje slew-a od 0.75 ns

U poređenju je primenjen zajednički `MAX_TRANSITION_CONSTRAINT = 0.75 ns` iz LibreLane/Open-PDKs konfiguracije. To je stroži implementacioni cilj, a ne posebno Tiny Tapeout pravilo.

Bibliotečka granica iznosi 1.5 ns. Zbog toga:

- PCG najgori slew 1.487774 ns krši stroži cilj od 0.75 ns, ali je neposredno ispod bibliotečke granice 1.5 ns;
- najgori dokumentovani xoroshiro i LFSR slew prelaze i 1.5 ns;
- za fer baseline zadržan je isti cilj od 0.75 ns za sva tri jezgra;
- eventualna ponovna analiza sa 1.5 ns bila bi poseban eksperiment, a ne zamena postojećeg baseline-a.

### 12.4. Zašto timing može da prolazi dok electrical checks ne prolaze

Setup i hold ispituju da li podatak stiže u vremenski prozor. Slew, fanout i capacitance ispituju da li mreže rade u zadatom električnom režimu.

PnR može da popravi probleme:

- umetanjem bafera;
- izborom ćelija veće pogonske jačine;
- replikacijom kontrolne logike;
- izgradnjom fanout stabala;
- fizičkim placement-om i rutiranjem.

Cena može biti veća površina i potrošnja, kao i promena setup/hold slack-a. Zato nijedan trenutni netlist nije electrical ili signoff-clean.

## 13. Preliminarna TT vectorless snaga

Sva tri power izveštaja koriste `AREA 0`, TT/25 °C/1.80 V i 50 MHz.

| Metrika | LFSR64 | xoroshiro64ss | PCG32 |
|---|---:|---:|---:|
| Internal power | 0.3076771 mW | 24.4280100 mW | 311.9218 mW |
| Switching power | 0.02038748 mW | 19.9141100 mW | 267.1326 mW |
| Leakage | 2.014717 nW | 9.0725 nW | 27.08155 nW |
| Sekvencijalna snaga | 0.2901391 mW | 0.4701502 mW | 1.774729 mW |
| Kombinaciona snaga | 0.03792761 mW | 43.8719500 mW | 577.2794 mW |
| **Ukupna snaga** | **0.3280666 mW** | **44.3421200 mW** | **579.0544 mW** |
| Udeo kombinacione snage | 11.56% | 98.94% | 99.69% |

### 13.1. Relativni odnosi snage

| Odnos | Rezultat |
|---|---:|
| xoroshiro / LFSR | 135.162× |
| PCG / xoroshiro | 13.059× |
| PCG / LFSR | 1 765.051× |

PCG je površinski 2.929 puta veći od xoroshiro jezgra, ali mu je vectorless snaga 13.059 puta veća. To pokazuje da power procena ne zavisi samo od broja ćelija, već i od mapiranih tipova ćelija, njihovih kapacitivnosti i statistički propagirane aktivnosti. Mogući doprinos glitch prelaza treba potvrditi simulacionom VCD/SAIF analizom; vectorless izveštaj ga ne izdvaja posebno.

Sličan oprez važi za odnos xoroshiro/LFSR: površina je 4.377 puta veća, a vectorless snaga 135.162 puta veća. Vectorless model očigledno veoma različito aktivira malu LFSR mrežu i široke kombinacione datapath-ove.

### 13.2. Šta vectorless procena pretpostavlja

U ovom toku nije učitana stvarna VCD/SAIF aktivnost. OpenSTA polazi od generičke početne aktivnosti ulaza, približno 0.1 promena po ciklusu i duty cycle 0.5, a zatim statistički propagira aktivnost kroz netlist.

Zato prijavljene vrednosti predstavljaju:

- ozbiljan relativni indikator kombinacione složenosti pod istim statističkim modelom aktivnosti;
- konzistentan preliminarni eksperiment pod istom metodom;
- ne i izmerenu ili signoff potrošnju fizičkog čipa.

`Clock = 0` ne znači da fizički takt ne troši energiju. Clock tree još nije izgrađen, pa njegovi baferi, mreže i kapacitivnosti nisu modelovani.

## 14. Izvedeni power/throughput pokazatelji po ciklusu i 32-bitnoj reči

Važi:

```text
E_ciklus = P / f
E_reč    = P / broj_reči_u_sekundi
```

| Izvedena metrika | LFSR64 | xoroshiro64ss | PCG32 |
|---|---:|---:|---:|
| Energija po ciklusu | 6.561332 pJ | 0.8868424 nJ | 11.581088 nJ |
| Ciklusa po reči | 32 | 1 | 1 |
| Vectorless power/throughput proxy po 32-bitnoj reči | 0.2099626 nJ | 0.8868424 nJ | 11.581088 nJ |

Relativni odnosi izvedenog vectorless power/throughput proxy-ja su:

| Odnos | Rezultat |
|---|---:|
| xoroshiro / LFSR | 4.224× |
| PCG / xoroshiro | 13.059× |
| PCG / LFSR | 55.158× |

Normalizacija maksimalnim protokom je korisnija od poređenja samo ukupne snage, jer LFSR proizvodi jednu reč na 32 ciklusa. Ipak, vectorless power nije izračunat iz simulacije tog zasićenog `next_i/ready_o/valid_o` workload-a. Zato brojevi predstavljaju samo power/throughput proxy uz pretpostavku kontinuiranog maksimalnog protoka, a ne potvrđenu energiju po reči.

Za xoroshiro i PCG energija po ciklusu može se izjednačiti sa energijom po izlazu samo ako se prihvati jedan zahtev u svakom taktu. Za konačnu energiju potrebno je podeliti stvarno utrošenu energiju brojem stvarno prihvaćenih validnih izlaza u zajedničkom VCD/SAIF scenariju.

## 15. Latencija, protok i površinska efikasnost

| Metrika na 50 MHz | LFSR64 | xoroshiro64ss | PCG32 |
|---|---:|---:|---:|
| Latencija kompletne reči | 32 takta | 1 takt | 1 takt |
| Nominalno vreme po reči | 640 ns | 20 ns | 20 ns |
| Održivi protok | 1.5625 Mword/s | 50 Mword/s | 50 Mword/s |
| Bitni protok | 50 Mbit/s | 1.6 Gbit/s | 1.6 Gbit/s |
| Protok po cell area | 308.880 Mword/s/mm² | **2 258.102 Mword/s/mm²** | 770.969 Mword/s/mm² |
| Cell area po Mword/s | 3 237.505 µm² | **442.850 µm²** | 1 297.069 µm² |

Redosled prema protoku po cell area je:

1. xoroshiro64ss;
2. PCG32;
3. LFSR64.

To ne protivreči činjenici da je LFSR apsolutno najmanji. Njegova konkretna mikroarhitektura koristi malu kombinacionu mrežu, ali sklapa reč serijski tokom 32 takta.

Relativno:

- xoroshiro daje 32 puta veći protok uz 4.377 puta veću cell area, pa ima 7.311 puta bolji protok po površini od LFSR-a;
- PCG daje 32 puta veći protok uz 12.820 puta veću cell area, pa ima samo 2.496 puta bolji protok po površini od LFSR-a;
- xoroshiro i PCG imaju isti protok, ali xoroshiro ima 2.929 puta bolji protok po površini.

## 16. Matrica odluke

| Kriterijum | Najpovoljniji rezultat | Obrazloženje |
|---|---|---|
| Najmanja cell area | LFSR64 | 5 058.6016 µm² |
| Najmanji broj ćelija | LFSR64 | 381 |
| Najmanja kombinaciona složenost | LFSR64 | 248 kombinacionih ćelija |
| Najmanji broj flip-flopova | xoroshiro i PCG | oba imaju 97 |
| Najveća globalna setup rezerva na 50 MHz | LFSR64 | +9.993491 ns, ali kritični put je I/O kontrolni put |
| Najveća pre-layout hold rezerva | PCG32 | +0.142826 ns; nije mera brzine |
| Najmanje SS slew prekršaja | LFSR64 | 347, ali i dalje nije electrical-clean |
| Najmanje cap prekršaja | xoroshiro i PCG | po 1; broj ne meri veličinu prekoračenja |
| Najkraća latencija | xoroshiro i PCG | jedna reč po taktu |
| Najveći apsolutni protok | xoroshiro i PCG | 50 Mword/s |
| Najveći protok po cell area | xoroshiro | 2 258.102 Mword/s/mm² |
| Najmanja vectorless snaga | LFSR64 | 0.3280666 mW |
| Najmanji vectorless power/throughput proxy | LFSR64 | 0.2099626 nJ/reč uz pretpostavljeni maksimalni protok |
| Najveća robustnost strategija na 50 MHz | LFSR i PCG | svih 9 strategija prolazi |
| Najbolji hardverski kompromis za 1 reč/takt | xoroshiro | isti protok kao PCG uz mnogo manju area, power i veću setup rezervu |
| Najveći implementacioni rizik | PCG32 | najmanja setup rezerva, najviše prekršaja i najveća kombinaciona mreža |

Ne postoji jedna univerzalna zbirna ocena. Pobednik zavisi od toga da li je prioritet najmanji generator, najveći protok, površinska efikasnost ili osobine pseudoslučajne sekvence koje sinteza ne meri.

## 17. Šta rezultat znači za svaki generator

### 17.1. `lfsr64_core`

Prednosti potvrđene sintezom:

- najmanja apsolutna površina i broj ćelija;
- plitka kombinaciona mreža;
- velika setup rezerva na 50 MHz;
- najmanja preliminarna snaga i najmanji izvedeni power/throughput proxy;
- jednostavan kandidat za fizičku realizaciju.

Nedostaci i ograničenja:

- jedna 32-bitna reč zahteva 32 takta;
- linearan je i predvidiv;
- registri i serijsko sklapanje reči čine više od polovine cell area;
- kratka shift putanja ostavlja samo 45.761 ps pre-layout hold rezerve;
- reset mreža ima visok fanout i velike slew prekršaje.

LFSR je najpovoljniji kada su prioritet minimalna cena i najmanja prijavljena vectorless snaga, a protok od 1.5625 Mword/s je dovoljan.

### 17.2. `xoroshiro64ss_core`

Prednosti potvrđene sintezom:

- jedna reč po taktu;
- najbolji protok po cell area;
- 2.929 puta manja površina od PCG-a pri istom protoku;
- oko 13.06 puta manja vectorless snaga i manji izvedeni power/throughput proxy od PCG-a;
- veća setup rezerva od PCG-a;
- srednja hardverska cena između LFSR-a i PCG-a.

Nedostaci i ograničenja:

- 4.377 puta je veći od LFSR-a;
- `**` scrambler čini dubok algoritamski kritični put;
- dve najmanje AREA strategije ne prolaze 50 MHz;
- `next_i` i `rst_ni` imaju visoke fanout i slew vrednosti;
- preliminarna snaga dominantno pripada kombinacionoj mreži.

Ako je potreban visok word-parallel protok, xoroshiro predstavlja najpovoljniji hardverski kompromis među ove tri konkretne implementacije.

### 17.3. `pcg32_oneseq_core`

Prednosti potvrđene sintezom:

- jedna 32-bitna reč po taktu;
- samo 64 bita algoritamskog stanja;
- svih devet strategija prolazi pre-layout setup cilj od 50 MHz;
- nema memorija, latch-eva ni prijavljenih Yosys strukturnih problema.

Nedostaci i ograničenja:

- najveća cell area i broj ćelija;
- 96.82% površine pripada kombinacionoj logici;
- najmanja setup rezerva, samo 0.571877 ns u SS uglu;
- 1 962 SS slew i 81 fanout prekršaj;
- 99.69% preliminarne snage pripada kombinacionoj logici;
- ista propusnost kao xoroshiro, ali znatno nepovoljniji area/power/timing rezultat.

Ovo nije dokaz da je PCG32 algoritam generalno nepogodan za hardver. Zaključak se odnosi na konkretnu jedno-ciklusnu mikroarhitekturu. Višeciklusni shift-add množilac može smanjiti kombinacionu površinu uz pad protoka, dok pipeline prvenstveno može povećati timing rezervu uz dodatne registre. Obe varijante menjaju latenciju i fer osnovu poređenja i moraju se voditi kao novi eksperimenti.

## 18. Najvažnije međusobne paralele

### 18.1. LFSR naspram xoroshiro

xoroshiro je 4.377 puta veći, ali daje 32 puta veći protok. Zato ima 7.311 puta bolji protok po cell area. LFSR ostaje bolji prema apsolutnoj površini, prijavljenoj vectorless snazi i izvedenom power/throughput proxy-ju.

### 18.2. xoroshiro naspram PCG32

Oba jezgra:

- imaju 97 flip-flopova;
- imaju istu sekvencijalnu cell area;
- proizvode jednu 32-bitnu reč po taktu;
- imaju isti idealni protok od 50 Mword/s.

xoroshiro ipak ima:

- 2.929 puta manju ukupnu cell area;
- 3.127 puta manju kombinacionu cell area;
- približno 13.06 puta manju vectorless snagu i manji izvedeni power/throughput proxy;
- 3.41 puta veći setup slack u zajedničkom `AREA 0` baseline-u;
- 4.45 puta manje SS slew violating tačaka.

PCG ima veću pre-layout hold rezervu, ali to ne nadoknađuje glavne area, setup, power i electrical razlike.

### 18.3. LFSR naspram PCG32

PCG daje 32 puta veći protok, ali je 12.820 puta veći i ima oko 1 765 puta veću vectorless snagu. Posle normalizacije pretpostavljenim maksimalnim protokom njegov izvedeni power/throughput proxy ostaje 55.158 puta veći.

Zbog serijske LFSR arhitekture PCG ipak daje 2.496 puta veći protok po cell area. To pokazuje da apsolutna cena i normalizovana propusnost odgovaraju na različita pitanja.

## 19. Šta se pouzdano može tvrditi

Na osnovu arhiviranih izveštaja može se tvrditi:

1. sva tri RTL modula uspešno su sintetizovana u mrežu `sky130_fd_sc_hd` ćelija;
2. nema inferovanih memorija, latch-eva niti Yosys `CHECK` problema;
3. sva tri zajednička `AREA 0` netlista prolaze pre-layout setup i hold na 50 MHz u analiziranim uglovima;
4. LFSR64 ima 381 ćeliju i cell area 5 058.6016 µm²;
5. xoroshiro64ss ima 1 987 ćelija i cell area 22 142.4864 µm²;
6. PCG32 ima 5 998 ćelija i cell area 64 853.4496 µm²;
7. xoroshiro i PCG imaju istih 97 flip-flopova, ali PCG ima 3.127 puta veću kombinacionu area;
8. LFSR kritični globalni put je I/O kontrolni put, xoroshiro kritični put prolazi kroz `**` scrambler, a PCG kritični put kroz LCG state update;
9. sva tri netlista imaju električne prekršaje koje fizički tok mora ponovo da rešava;
10. xoroshiro i PCG daju jednu reč po taktu, dok LFSR daje jednu reč na 32 takta;
11. xoroshiro daje najveći protok po cell area;
12. zajednička vectorless procena prijavljuje 0.3280666, 44.34212 i 579.0544 mW;
13. prema hardverskim sinteznim metrikama LFSR ima najmanji apsolutni trošak, xoroshiro predstavlja srednji kompromis, a jedno-ciklusni PCG najveći trošak.

## 20. Šta se još ne može tvrditi

Iz ove faze se ne može tvrditi:

- da cell area predstavlja konačnu fizičku površinu ili broj Tiny Tapeout tile-ova;
- da pozitivan pre-layout slack garantuje 50 MHz posle placement-a i routinga;
- da su 55.40 i 51.47 MHz konačne `Fmax` vrednosti;
- da će hold slack ostati pozitivan nakon CTS-a;
- da je bilo koji netlist electrical/signoff-clean;
- da su 0.328, 44.342 i 579.054 mW stvarne silikonske potrošnje;
- da će vectorless odnosi snage ostati isti uz realnu aktivnost;
- da su izvedene energije po reči konačne fizičke energije;
- da `Clock = 0` znači nultu potrošnju clock mreže;
- da su PVT naponi preporučeni naponi pločice;
- da sinteza dokazuje funkcionalnu ekvivalenciju gate-level netlista;
- da sinteza pokazuje koji generator ima najbolji statistički kvalitet;
- da je bilo koji od ova tri generatora kriptografski bezbedan;
- da je PCG32 algoritam generalno loš za hardver, nezavisno od mikroarhitekture.

## 21. Sledljivost i arhivirani baseline-i

Zajednički RTL tag `prng-core-baseline-v1` je anotirani tag. Njegov tag-object hash počinje sa `b7b493a`, dok je stvarni commit na koji pokazuje `edbc39c`. Za identifikaciju RTL sadržaja treba koristiti peeled commit, odnosno `prng-core-baseline-v1^{commit}`.

| Jezgro | Run tag | Rezultatski commit | Anotirani synthesis tag |
|---|---|---|---|
| LFSR64 | `lfsr64_core_50mhz` | `058f8ce` | `lfsr64-synthesis-area0-v1` |
| xoroshiro64ss | `xoroshiro64ss_core_50mhz` | `b650590` | `xoroshiro64ss-synthesis-area0-v1` |
| PCG32 | `pcg32_oneseq_core_50mhz` | `e29933e` | `pcg32-synthesis-area0-v1` |

Svaki rezultatni direktorijum sadrži 13 uporedivih tipova artefakata:

- manifest;
- razrešenu konfiguraciju;
- exploration tabelu;
- `AREA 0` gate-level netlist;
- tekstualnu i JSON statistiku;
- synthesis i STA state;
- multi-corner STA sažetak;
- detaljni SS setup izveštaj;
- detaljni FF hold izveštaj;
- zaglavlje SS electrical violator izveštaja; pojedinačne tačke nisu izlistane,
  pa se zbirni brojevi uzimaju iz STA state/summary artefakata;
- TT preliminarni power izveštaj.

Putanje su:

```text
synthesis/results/lfsr64_core/
synthesis/results/xoroshiro64ss_core/
synthesis/results/pcg32_oneseq_core/
```

### 21.1. Mala dokumentaciona napomena za PCG paket

U stvarno tagovanom PCG commit-u manifest je slučajno sačuvan kao `README .md`,
sa razmakom pre ekstenzije, iako njegov sadržaj i namera koriste naziv
`README.md`. To ne menja nijedan synthesis rezultat. U završnom
dokumentacionom commit-u fajl se preimenuje u `README.md`, dok postojeći
`pcg32-synthesis-area0-v1` tag ostaje na originalnom synthesis baseline-u.

## 22. Preporučeni sledeći korak

Sledeća metodološki opravdana faza je jednak full PnR tok za sva tri `AREA 0` baseline-a:

1. koristiti isti floorplan kriterijum i uporedivu utilization vrednost;
2. uraditi placement i proveriti routability;
3. izgraditi clock tree;
4. uraditi detaljan routing i ekstrakciju RC parazita;
5. ponoviti setup i hold u istim uglovima;
6. proveriti koliko je bafera i jačih ćelija dodato radi slew/fanout/cap popravki;
7. odrediti konačnu core area i broj potrebnih Tiny Tapeout tile-ova;
8. proveriti DRC/LVS i ostale signoff izveštaje dostupne u toku;
9. generisati isti reprezentativni VCD/SAIF stimulus za sva tri jezgra;
10. koristiti isti broj prihvaćenih izlaznih reči i isti active/idle obrazac;
11. izračunati post-route snagu i energiju po stvarno validnoj reči;
12. tek zatim spojiti fizičke rezultate sa ranije urađenim statističkim testovima i izabrati konačni ASIC kandidat.

Ako PCG32 ne prođe zajednički fizički cilj, pipelined verzija radi povećanja timing margine ili višeciklusna/iterativna realizacija radi smanjenja kombinacione površine treba da bude novi, posebno označen baseline. Obe promene menjaju latenciju, protok i fer osnovu poređenja, dok pipeline može povećati broj registara i ne garantuje manju ukupnu površinu ili snagu.

## 23. Završna ocena

RTL sinteza je pokazala tri različite hardverske filozofije.

`lfsr64_core` je mali, registarski dominantan i timing-komforan dizajn. Njegova glavna prednost je minimalan apsolutni trošak, dok je cena serijska izgradnja reči tokom 32 takta.

`xoroshiro64ss_core` koristi mnogo više kombinacione logike, ali tu dodatnu površinu pretvara u jednu kompletnu reč po taktu. U odnosu na LFSR ima 4.377 puta veću cell area, ali 32 puta veći protok i 7.311 puta bolji protok po površini. Kritični put jasno pripada `**` scrambleru.

`pcg32_oneseq_core` ima isti broj registara i isti protok kao xoroshiro, ali njegova 64-bitna jedno-ciklusna LCG mreža uzrokuje 2.929 puta veću cell area, približno 13.06 puta veću vectorless snagu i mnogo više električnih violating tačaka. Njegova setup rezerva od 0.571877 ns upozorava da 50 MHz može postati teško ostvarivo posle fizičke realizacije.

Prema tome:

- **LFSR64** je najbolji kada su prioritet minimalna površina, jednostavnost i najmanja prijavljena vectorless snaga;
- **xoroshiro64ss** je najbolji hardverski kompromis kada je potreban protok od jedne 32-bitne reči po taktu;
- **jedno-ciklusni PCG32** ima najveći implementacioni trošak i zahteva najoprezniju fizičku proveru ili novu mikroarhitekturu.

Ovo nije rangiranje statističkog kvaliteta generatora. Konačna odluka za Tiny Tapeout mora da spoji funkcionalne i statističke rezultate sa jednakim post-route area, timing i activity-aware power poređenjem.

## 24. Sažeti tekst pogodan za diplomski rad

> RTL sinteza generatora `lfsr64_core`, `xoroshiro64ss_core` i `pcg32_oneseq_core` izvršena je pod istim uslovima korišćenjem LibreLane 2.4.2 `SynthesisExploration` toka, SKY130A PDK-a, biblioteke `sky130_fd_sc_hd` i ciljne periode takta od 20 ns. Kao zajednički baseline usvojena je strategija `AREA 0`. LFSR netlist sadrži 381 standardnu ćeliju i ima cell area 5 058.6016 µm², xoroshiro netlist 1 987 ćelija i 22 142.4864 µm², a PCG32 netlist 5 998 ćelija i 64 853.4496 µm². Kombinaciona logika čini 44.08%, 90.68% i 96.82% njihove površine. Sva tri rezultata prolaze pre-layout setup i hold proveru na 50 MHz, ali je najgori setup slack +9.993491 ns za LFSR, +1.949115 ns za xoroshiro i samo +0.571877 ns za PCG32. LFSR kritični globalni put predstavlja I/O reset putanju, xoroshiro kritični put prolazi kroz `**` izlazni scrambler, dok PCG kritični put pripada 64-bitnom LCG ažuriranju stanja. LFSR proizvodi jednu 32-bitnu reč na 32 takta, dok xoroshiro i PCG daju po jednu reč svakog takta. Zbog toga xoroshiro ostvaruje najveći protok po cell area: približno 2 258 Mword/s/mm², naspram 309 za LFSR i 771 za PCG32. Preliminarna TT vectorless analiza prijavljuje 0.3280666 mW, 44.34212 mW i 579.0544 mW, ali te vrednosti nisu konačna potrošnja jer ne uključuju stvarnu VCD/SAIF aktivnost, clock tree, routing ni ekstrahovane parazite. Rezultati pokazuju da LFSR daje najmanji apsolutni hardverski trošak, xoroshiro najbolji kompromis za visok protok, a jedno-ciklusni PCG32 najveću kombinacionu cenu. Konačan izbor zahteva jednak post-route tok i activity-aware power analizu sva tri jezgra.

## 25. Konačni status

| Stavka | LFSR64 | xoroshiro64ss | PCG32 |
|---|---|---|---|
| RTL sintetizovan | da | da | da |
| Svih 9 strategija analizirano | da | da | da |
| `AREA 0` arhiviran i tagovan | da | da | da |
| `AREA 0` setup na 50 MHz | prolazi | prolazi | prolazi |
| `AREA 0` hold pre-layout | prolazi | prolazi | prolazi |
| Setup/hold TNS | 0 / 0 | 0 / 0 | 0 / 0 |
| Bez memorija/latch-eva | da | da | da |
| Electrical-clean | ne | ne | ne |
| Full PnR | nije urađen | nije urađen | nije urađen |
| Activity-aware power | nije urađen | nije urađen | nije urađen |
| Pogodan kao synthesis baseline | da | da | da |

**Konačni sintezni zaključak:** hardverski trošak raste od LFSR64 preko xoroshiro64ss do jedno-ciklusnog PCG32. LFSR je najjeftiniji, xoroshiro najbolje koristi površinu za visok protok, a PCG32 zahteva najveću kombinacionu mrežu i ima najmanju setup rezervu. Sva tri rezultata su reproduktivni pre-layout baseline-i; konačne ASIC tvrdnje zahtevaju jednak fizički tok.
