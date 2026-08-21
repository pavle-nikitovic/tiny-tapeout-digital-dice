# Zajednička statistička platforma za PRNG generatore

Platforma primenjuje potpuno isti skup testova na konačno izabrane modele:

- `LFSR64`
- `xoroshiro64** 1.0`
- `PCG32-oneseq`

Ovo je odvojena faza od funkcionalnih core testova. Golden vektori dokazuju da
model izvršava pravi algoritam, dok ova platforma traži statistička odstupanja u
jednom generisanom uzorku.

## Raspored fajlova u Tiny Tapeout projektu

Preporučeni raspored je:

```text
test/
├── lfsr64_core.py
├── xoroshiro64ss_core.py
├── pcg32_oneseq_core.py
├── test_lfsr64_core.py
├── test_xoroshiro64ss_core.py
├── test_pcg32_oneseq_core.py
├── prng_statistical_tests.py
├── test_prng_statistical_tests.py
├── requirements_prng_statistical_tests.txt
└── README_prng_statistical_tests.md
```

Sve komande u nastavku pokreću se iz korena repozitorijuma, odnosno iz
`/workspaces/tiny-tapeout-digital-dice`. Potreban je Python 3.10 ili noviji.

Platforma radi i kada su svi navedeni Python fajlovi u korenu projekta; tada iz
komandi samo treba izostaviti prefiks `test/`. Ne treba praviti dve kopije istog
core fajla, jer platforma namerno prijavljuje grešku ako ne može jednoznačno da
utvrdi koji model testira.

## 1. Instalacija grafikona

Statistički proračuni koriste samo standardnu Python biblioteku. Za PNG
grafikone potreban je Matplotlib:

```bash
python3 -m pip install -r test/requirements_prng_statistical_tests.txt
```

Bez Matplotlib-a platforma se može pokrenuti opcijom `--no-plots`.
Ovaj poseban requirements fajl samo dopunjuje postojeći Tiny Tapeout
`test/requirements.txt` i ne treba da ga zameni.

## 2. Provera same platforme

Iz korena Tiny Tapeout repozitorijuma pokreni:

```bash
python3 test/test_prng_statistical_tests.py
```

Ovim se deterministički proveravaju:

- LSB-first pretvaranje reči u bitstream;
- poznate vrednosti formula za sva četiri testa;
- proračun hi-kvadrat p-vrednosti bez SciPy-a;
- Holm–Bonferroni korekcija;
- učitavanje core modela;
- CSV i JSON izlazi, kao i PNG izlazi ako je Matplotlib instaliran.

Potpuna instalacija u tvom Codespace-u treba da završi bez preskočenog LFSR
testa. Poruka `OK (skipped=1)` znači da `lfsr64_core.py` nije pronađen; u tom
slučaju standardno pokretanje sva tri generatora namerno prijavljuje grešku.

## 3. Standardno pokretanje sva tri generatora

```bash
python3 test/prng_statistical_tests.py
```

Podrazumevana, zvanična konfiguracija je:

| Parametar | Vrednost |
|---|---:|
| Raw početno stanje | `0x0123_4567_89AB_CDEF` |
| Warm-up koraci | 0 |
| Izlaznih reči po generatoru | 32.768 |
| Bitova po generatoru | 1.048.576 (`2^20`) |
| Redosled bitova u svakoj reči | LSB-first |
| Nivo značajnosti `alpha` | 0,01 |
| Autokorelaciona kašnjenja | 1, 2, 3, 4, 8, 16, 31, 32, 33 i 64 bita |
| Korekcija višestrukih testova | globalni Holm–Bonferroni |

LSB-first je izabran zato što `LFSR64` prvi hronološki generisan bit smešta u
bit 0 izlazne reči. Isti redosled se zatim primenjuje na sva tri generatora.
Kašnjenja 31, 32 i 33 dodatno proveravaju okolinu granice između dve 32-bitne
izlazne reči.

## 4. Šta se testira

| Test | Šta proverava | Osnovni izlaz |
|---|---|---|
| Monobit | Da li su nule i jedinice približno jednako česte | udeo jedinica i p-vrednost |
| Runs | Da li se smene nizova nula i jedinica javljaju očekivanom učestanošću | broj nizova i p-vrednost |
| Autokorelacija | Da li postoji veza između bitova razdvojenih zadatim kašnjenjem | procena `rho` i p-vrednost za svaki lag |
| Hi-kvadrat bajtova | Da li se svih 256 vrednosti bajta pojavljuju približno ravnomerno | `chi2`, 255 stepeni slobode i p-vrednost |

Runs test se ne računa ako njegov preduslov o približno jednakom broju nula i
jedinica nije ispunjen. U tom slučaju dobija status `N/A`, a izmerena neravnoteža
ostaje prikazana u monobit rezultatu.

Pošto se odjednom posmatra više p-vrednosti, konačni PASS/FAIL ne koristi svaku
sirovu p-vrednost nezavisno. Primenjuje se Holm–Bonferroni korekcija nad svim
primenljivim rezultatima svih izabranih generatora. U tabelama se čuvaju i
sirova i korigovana p-vrednost radi potpunog uvida.

## 5. Dobijeni fajlovi

Standardno pokretanje pravi folder `prng_results/` u trenutnom terminalskom
direktorijumu. Sa prikazanim komandama to je koren repozitorijuma, pored foldera
`test/`:

```text
prng_results/
├── detailed_results.csv
├── summary.csv
├── results.json
├── p_values.png
├── autocorrelation.png
└── byte_distribution.png
```

- `detailed_results.csv` sadrži po jedan red za svaki test i svako kašnjenje.
- `summary.csv` daje jednu sažetu vrstu po generatoru.
- `results.json` čuva konfiguraciju, putanju stvarno učitanog core-a i sve
  detalje potrebne za kasniju automatizaciju.
- `p_values.png` prikazuje sirove p-vrednosti radi dijagnostike; PASS/FAIL se i
  dalje određuje pomoću Holm-korigovanih vrednosti iz tabela.
- `autocorrelation.png` prikazuje procenjenu korelaciju `rho` po kašnjenjima.
- `byte_distribution.png` poredi izmerene brojeve pojavljivanja 256 bajtova sa
  očekivanom vrednošću.

Opcija `--no-plots` pravi samo CSV i JSON izlaze. Opcija `--save-streams`
dodatno pravi po jedan `.bin` fajl za svaki izabrani generator.

## 6. Korisne opcije

Brža probna provera:

```bash
python3 test/prng_statistical_tests.py --words 4096 --no-plots
```

Veći uzorak od `2^24` bita za kasniju završnu analizu:

```bash
python3 test/prng_statistical_tests.py --words 524288
```

Drugi unapred izabran nenulti raw seed:

```bash
python3 test/prng_statistical_tests.py --seed 0x13579BDF2468ACE0
```

Čuvanje istih analiziranih bitstreamova i kao binarnih fajlova:

```bash
python3 test/prng_statistical_tests.py --save-streams
```

Kontrolno MSB-first pokretanje može se dobiti sa `--bit-order msb`, ali rezultate
za zvanično poređenje treba uvek praviti podrazumevanim LSB-first redosledom.

Za dijagnostiku se može pokrenuti samo deo generatora:

```bash
python3 test/prng_statistical_tests.py \
  --generators xoroshiro64ss pcg32_oneseq
```

Za konačnu zajedničku tabelu treba pokrenuti sva tri generatora odjednom, jer se
Holm korekcija računa nad celom unapred definisanom familijom testova.

## 7. Ispravno tumačenje

`PASS` znači: **u ovom uzorku i ovim testovima nije pronađeno statistički
značajno odstupanje**. Ne znači da je dokazano da je generator slučajan niti da
je kriptografski bezbedan.

Generator sa većom p-vrednošću nije automatski „bolji“. P-vrednosti se ne
prosečavaju i ne koriste za rangiranje. LFSR može proći sve ove osnovne testove,
iako je njegova sekvenca linearna. Zato ćemo kasnije, ako bude potrebno za
završnu tvrdnju u radu, dodati test linearne kompleksnosti ili pokrenuti šire
pakete kao što su NIST STS i PractRand.

Platforma poredi isti broj **izlaznih bitova**, ali to ne znači isti hardverski
rad: LFSR64 pravi jednu reč kroz 32 elementarna koraka, a xoroshiro64** i PCG32
je daju u jednom prirodnom koraku. Ovaj program zato nije hardverski benchmark;
površina, maksimalna učestanost, protok i energija porediće se posle RTL
realizacije i sinteze.
