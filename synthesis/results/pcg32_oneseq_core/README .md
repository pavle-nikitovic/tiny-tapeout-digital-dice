# PCG32 oneseq core — AREA 0 synthesis baseline

This directory preserves the curated LibreLane synthesis baseline for
`pcg32_oneseq_core`. It is intended for a controlled comparison with the
equivalent `lfsr64_core` and `xoroshiro64ss_core` AREA 0 result packages.

## Experimental conditions

- RTL baseline tag: `prng-core-baseline-v1`
- RTL baseline commit: `edbc39c`
- LibreLane version: `2.4.2`
- Flow: `SynthesisExploration`
- PDK: `sky130A`
- Standard-cell library: `sky130_fd_sc_hd`
- Open-PDKs snapshot: `0fe599b2afb6708d281543108caf8310912f54af`
- Clock port: `clk_i`
- Clock period: `20.0 ns` (`50 MHz`)
- Archived strategy: `AREA 0`
- Run tag: `pcg32_oneseq_core_50mhz`
- STA corners:
  - `nom_tt_025C_1v80`
  - `nom_ss_100C_1v60`
  - `nom_ff_n40C_1v95`

All nine synthesis-exploration strategies passed the 50 MHz setup constraint.
`AREA 0` is archived because it is the common baseline strategy used for all
three PRNG cores.

## Key AREA 0 results

| Metric | Result |
|---|---:|
| Standard cells | 5,998 |
| Flip-flops | 97 |
| Combinational cells | 5,901 |
| Total cell area | 64,853.4496 um^2 |
| Sequential area | 2,063.2288 um^2 (3.18%) |
| Combinational area | 62,790.2208 um^2 (96.82%) |
| Worst setup slack | +0.571877 ns (SS, MET) |
| Setup TNS | 0 ns |
| Worst hold slack | +0.142826 ns (FF, MET) |
| Hold TNS | 0 ns |
| SS max-slew violations | 1,962 |
| SS max-fanout violations | 81 |
| SS max-capacitance violations | 1 |
| TT preliminary vectorless power | 579.0544 mW |

The critical setup path is inside the 64-bit LCG state update. The high area,
electrical-violation count, and preliminary dynamic-power estimate are
consistent with the large one-cycle combinational network used for constant
multiplication, addition, xorshift, and variable rotation.

## Preserved artifacts

| File | Description |
|---|---|
| `README.md` | Manifest, conditions, key results, and limitations |
| `resolved_config.json` | Fully resolved LibreLane run configuration |
| `exploration_summary.rpt` | Results for all nine synthesis strategies |
| `area0_netlist.v` | Technology-mapped AREA 0 gate-level netlist |
| `area0_stat.rpt` | Human-readable synthesis statistics |
| `area0_stat.json` | Machine-readable synthesis statistics |
| `area0_synthesis_state.json` | LibreLane state after AREA 0 synthesis |
| `area0_sta_summary.rpt` | Multi-corner AREA 0 STA summary |
| `area0_sta_state.json` | LibreLane state after AREA 0 STA |
| `area0_setup_ss_max.rpt` | Detailed worst setup paths in the SS corner |
| `area0_hold_ff_min.rpt` | Detailed worst hold paths in the FF corner |
| `area0_ss_violators.rpt` | SS electrical-constraint violator list |
| `area0_power_tt_preliminary.rpt` | Preliminary TT vectorless power report |

## Reproduction

From the repository root:

```bash
python -m librelane --pdk-root "$PDK_ROOT" \
  --docker-no-tty \
  --dockerized \
  -j 1 \
  --flow SynthesisExploration \
  --run-tag pcg32_oneseq_core_50mhz \
  synthesis/pcg32_oneseq_core/config.json
```

## Limitations

These are pre-layout synthesis results. They do not include placement, clock
tree synthesis, routing, extracted interconnect parasitics, IR drop, or
signoff verification.

The power result is a vectorless TT estimate based on statistical switching
activity. It is not a measured value and must not be interpreted as final chip
power or signoff energy per output. A later fair power comparison requires the
same representative VCD/SAIF stimulus and the same physical-design flow for all
three cores.
