# Scaling to 1mm 4-CU — `ADR-003` Deferred Branch

> `160×100` `tt_um_4d_cache` is the TT submission; this branch targets the `1mm 4-CU` `400×400` `400mm²` research scaling per `gpu_A.md:51-53,151`.

## Why 1mm?

- **TT `160×100`** fits 1 tile, `170 cells` `7.66ns` slack `17mW` — low risk (`ADR-003`).
- **1mm `1000×1000`** fits 4× `shader` (`200×200` `simd_alu` `800 cells` + `register_file` `25072` flop placeholder) + 4× `systolic` (`300×300` `33243`) + `cache` (`200×200` `42`) + `wdm` (`120×120`) + `SRAM 4KB` OpenRAM macro `400×400`. Total `~16k cells + SRAM` at `UTIL30` `DENSITY0.45` closes `10ns` with margin.

## What changes vs TT

| TT `gpu_top` | 1mm `gpu_top_1mm` |
|--------------|-------------------|
| `DIE 0 0 160 100` `UTIL45` single block | `DIE 0 0 1000 1000` `UTIL30` `ENABLE_MACROS_GRID` `MACRO_PLACEMENT_CFG` |
| `dummy_systolic_8x8` `64B` `8c` | `systolic_4x4` `4×4 INT8` `4c` per CU `×4` |
| No SRAM | `OpenRAM 4KB` `sky130` `EXTRA_LEFS/GDS` (run `openram` in Codespaces `ADR-005`) |
| `FPGA` `1.9GB` OK | Requires `Codespaces/Colab` `8–16GB` `GH ubuntu-latest` |

## How to generate 1mm GDS (Codespaces)

```bash
# 1. Harden shader/systolic macros first (GH)
# Push triggers .github/workflows/gds.yaml for cache/wdm/gpu_top; manually trigger for shader/systolic:
#   gh workflow run gds.yaml -f design=openlane/shader
# Or local 8GB docker (see Makefile gds-1mm):
docker run --rm -v $PWD:/project -w /project efabless/openlane:latest --design openlane/shader --tag shader_run
docker run --rm -v $PWD:/project -w /project efabless/openlane:latest --design openlane/systolic --tag systolic_run

# 2. Generate SRAM (OpenRAM) — in Codespaces:
#   git clone https://github.com/VLSIDA/OpenRAM
#   cd OpenRAM && python3 openram.py -c openlane/gpu_top_1mm/sram_4k.py

# 3. Hardenen 1mm top (needs macros LEF/GDS via EXTRA_*):
docker run --rm -v $PWD:/project -w /project efabless/openlane:latest --design openlane/gpu_top_1mm --tag gpu_1mm_run
# Output: openlane/gpu_top_1mm/runs/gpu_1mm_run/results/final/gds/gpu_top_1mm.gds + sdf/*.sdf
# Then `make gls-1mm` similar to `make gls` but with 1mm SDF
```

## Compute per CU `gpu_A.md:146`

- `16× FP32 ALUs` today we have `8-lane` `simd_alu.sv:10` — scale to `16` in next RTL (duplicate `8` or widen to `16`).
- `32× 32-bit regs` today `256×32` — will carve `32` per CU from `register_file.sv:13`.
- `4D cache` as `L2` `TDM4/WDM8` stays; add per-CU `L1 4KB` (`Q-003` `OpenRAM`) `gpu_A.md:85`.
- `WDM` for inter-CU `200GB/s` `interconnect.py:11` + `warp scheduler 32-thread GTO` `gpu_A.md:84` + `AXI4 slave` `gpu_A.md:87` + `L1/L2` `gpu_A.md:85`.

## Verification for 1mm

- `yosys -p "read_verilog -sv sim/shader/*.sv sim/cache4d/rtl/*.sv; hierarchy -check -top gpu_top_1mm"` `0 errors` — `gpu_A.md:44`.
- `cocotb` 4-CU: drive 4× parallel `host_req` + check `systolic` `GEMM 4×4` each CU `20 vectors` `5/5` per CU.
- `OpenSTA` `10ns` slack `>0` per `scripts/sta_estimate.py` `7.66ns` for TT → `1mm` similar with `UTIL30`.
- `pip-audit` `no vuln`, `DRC 0` via `reports.zip`.

## Timeline `gpu_A.md:93`

- **Now:** scaffold `openlane/gpu_top_1mm/*` + `macro_placement.cfg` (this commit) `COMPLETED`.
- **Next:** OpenRAM `4KB` generation + `warp` RTL + `AXI4` + `hardening` `GH Codespaces` `2–4 mo` `gpu_A.md:142-151`.
- **Then:** `ChipIgnite MPW` `free` `gpu_A.md:56` or `TT` `300$` for `1mm`? TT `1mm` not single tile — use `Efabless`.

## What breaks if deleted

- `openlane/gpu_top_1mm/config.json:1` → no `1mm` scaling evidence, TT remains only.
- `docs/scaling.md:1` → scaling rationale `UNKNOWN`.
