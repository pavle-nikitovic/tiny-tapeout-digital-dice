# LFSR64 Core — Synthesis Baseline

This directory contains the preserved AREA 0 synthesis and static timing
analysis results for `lfsr64_core`.

## Reproducibility

- RTL source: `src/lfsr64_core.v`
- Frozen RTL tag: `prng-core-baseline-v1`
- Frozen RTL commit: `edbc39c`
- Synthesis configuration: `synthesis/lfsr64_core/config.json`
- LibreLane version: `2.4.2`
- Flow: `SynthesisExploration`
- Run tag: `lfsr64_core_50mhz`
- PDK: `sky130A`
- Standard-cell library: `sky130_fd_sc_hd`
- Clock port: `clk_i`
- Clock period: `20.0 ns`
- Target frequency: `50 MHz`
- Preserved strategy: `AREA 0`

The run was started with:

```bash
python -m librelane --pdk-root "$PDK_ROOT" \
  --docker-no-tty --dockerized -j 1 \
  --flow SynthesisExploration \
  --run-tag lfsr64_core_50mhz \
  synthesis/lfsr64_core/config.json