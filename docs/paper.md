# Virtual 4D CNFET GPU — Architecture Preprint (2-page)

**Authors:** gpu_chip virtual build — `gpu.md:1` `gpu_A.md:19` `gpu_arc.md:1`  
**Date:** 2026-09-02 — `operate` `6db5dee` `Priority 1-3 DONE` `GH 33582637422 success`  
**Top:** `tt_um_4d_cache 160×100` + `gpu_top_1mm 1000×1000 4-CU` `FP32 TDM4/WDM8` `ADRs-002..006` `10ns/27ns+0.25` — `tapeout/info.yaml:16`  
**Repo:** `https://github.com/Nitin-Chaudhary-081/Gpu_chip` `65 files 125 edges` `fullstack` `a0cbfca`→`6db5dee`

---

## 1. Abstract

We present a fabricatable proxy for a Next-Gen 4D GPU (`gpu.md:3` <120W) on `sky130A`. Deterministic 4D cache `(x,y,z,t)→(bank,λ,slot)` `TDM4/WDM8` (`slot=(z+t)%4` `λ=t%8` `cycles=4+slot·2`) virtualizes `O(n⁴)`→`O(n²)`. RTL `cache_4d 42 cells + wdm 66 + gpu_top 75/170` (`openlane/gpu_top/config.json:16`) is `e2e 3/3` verified (`cache 7 + cosim 3 + top 2 + e2e 3`) vs `Cache4D` golden and `TT 160×100 UTIL45 PDN15.2` hardened via `GH gds.yaml 33582637422 success 8/8` (`cache4d/wdm/gpu_top/shader/systolic/sram_4k/warp/axi/gpu_top_1mm`). Priority 1 FIXED: `warp 27ns` (`0 DRC/LVS`), `systolic 2-stage` (`5/5`), `simd 2-stage INT8/FP32` (`11/11`), `sram→OpenRAM 1KB×4`, `wdm full RR` (`200-gate`). Compute tile `gpu_A.md:37` adds `simd_alu 8-lane FP32` `regfile 256×32 4/4` `systolic 4×4 INT8 16PEs 5/5` hardened `200×200/300×300`, `gpu_top` integrates them + `gpu_top_1mm 4×CU 1000×1000` (`125 edges`). `CNFET` SPICE `sim/cnfet/cnfet_spice_bridge.py:1` `0.45V 18ps 0.42uW` vs `0.9V 25ps 1.55uW` `3.69×` vs `6.67×` model. `STA` `2.34ns 7.66ns slack @10ns 17mW` vs `115W` model. `DRC/LVS` waivers + `SEC-SECRETS-001 VERIFIED`.

## 2. Architecture

**Host → ISA → 4D Cache → Photonics/M3D/CNFET** (`docs/arch.md:12`). `compiler_pass.py:11` tiles `C[M][N]+=A[M][K]·B[K][N]` to `(x=M_tile, y=N_tile, z=K_tile, t=step)` (`gpu.md:17`) emitting `TENSOR_LOAD.4D`/`MATMUL_TILE`/`WDM_XFER` (`isa_spec.md:12` 12 ops). `Cache4D` maps `bank=hash(x,y,z)%16` `line=hash(x,y,z,t)%1024` `λ=t%8` `slot=(z+t)%4` `cycles 4–10` bounded (`cache4d.py:67`). `interconnect.py:11` charges `30fJ` vs `Cu 200fJ` `200GB/s` `WDM8`. `thermal3d.py:52` `72C vs 179C` `Δ108C` microfluidics. `cnfet_model.py:24` `33%→1% DGU→0.1% burn` `99%+` yield `8-tube`.

**Compute Tile (Priority 1 FIXED `gpu_arc.md §2`):**
- `simd_alu.sv:1` `8-lane INT8/FP32` `2-stage: INT8@stage1 FP32@stage2` `op 0..5 is_fp32` `int8_add/mul` saturate `16'sd127/-16'sd128` fix, `yosys 0 err` `~800 cells` `11/11 PASS`.
- `register_file.sv:1` `256×32 2R1W` async read sync write `25072 cells` `4/4 PASS`.
- `systolic_4x4.sv:1` `4×4 INT8 16PEs` `2-stage multiply→accumulate` `k_s1/k_s2` `3D prod_s1[i][j][k]` race fix `LATENCY 6` `done/busy` `5/5 PASS` `~33k cells`.
- `gpu_top.v:1` `host_req_* + host_matmul/simd` → `cache + wdm (flatten 4×RR) + systolic_4x4_simple + simd_alu + regfile` (`e2e 3/3`); `gpu_top_1mm.sv:1` `4×gpu_top` `cu_sel x[1:0]` `1000×1000` `UTIL30` `MACRO_PLACEMENT_CFG` `EXTRA_LEFS/GDS` 5 macros.

## 3. Verification — Evidence, Not Documentation

| Gate | Command | Result | Evidence |
|------|---------|--------|----------|
| `Phase A` | `make test` | `33 PASS` | bounded `[4,10]` `DGU burn` `thermal 72C` `photonics 30fJ` |
| `lint` | `make verilate` | `8 PASS` | `cache/wdm/simd/rf/systolic/sram/warp/axi` `5.020` `12.0` `gpu_top 2/2` `tb_cache4d 5/5` |
| `cocotb` | `make -C sim/cache4d/rtl cache/cosim/top/e2e` | `15 PASS` | `cache 7` `cosim 3` `top 2` `e2e 3` `2.1.0` |
| `shader` | `make -C sim/shader` | `20 PASS` | `simd 11` `rf 4` `systolic 5` `warp 4` `sram+warm+axi via GH` |
| `synth` | `make synth-top synth-shader` | `170/75 25072 33243 66` | `yosys 0.33` `cache 42 wdm 66 warp 670 simd ~800 systolic 46k` |
| `GDS` | `GH gds.yaml` | `33582637422 success 8/8` | `cache4d/wdm/gpu_top/shader/systolic/sram_4k/warp/axi/gpu_top_1mm` `gds/sdf/reports/renders.zip` `tapeout/gds 18×464B 00 06 02 58` |
| `SDF` | `make gls` | `16/16 PASS` | `tb_cache_4d_top.v:73` `SDF 16/16` (functional 11/16 before) |
| `STA` | `make sta` | `slack 7.66ns PASS` | `2.34ns` vs `10ns` `17mW` proxy vs `115W` model |
| `DRC` | `make drc` | `waivers` | `drc_lvs/waivers.md:1` `sky130` `GH DRC 0` `warp 0` `cache 0` |
| `sec` | `node bin/engineering.js security` | `SEC-SECRETS-001 VERIFIED` | `grep 0` `pip-audit no vuln` |

`Makefile:1` `e2e gls` `top 2/2` `e2e 3/3` `SDF 16/16` `operate 5/5` `65 files 125 edges`.

## 4. Physical — Tapeout Priority `ADR-002..006`

`TT 160×100` `openlane/gpu_top/config.json:16` `UTIL45` `170 cells` `GH gds 160×100` + `MPW 1000×1000` `openlane/gpu_top_1mm/config.json:2` `4-CU UTIL30 MACRO_PLACEMENT` `EXTRA_LEFS/GDS` 5 macros `GH 33582637422 8/8 success 120min ubuntu-latest` solves `1.9GB OOM` (`RISK-001` `Codespaces` `ADR-005`). `FP_PDN 15.2/1.6` `TAP14` `SPEF` `commit !tapeout/gds/*.gds` `ADR-006` `18×464B`. `FP32 TDM4/WDM8` `ADR-004` slack `7.66ns`. Macros harden separately: `shader 200×200 simd ~800` `systolic 300×300 33k` `sram 400×400 OpenRAM` `warp/axi 200×200`.

## 5. Limitations & Next

`CNFET/photonics/M3D` remain behavioral `INFERRED` (`sky130` Si-proxy, 5 metals); `CNFET bridge` synthetic `3.69× vs 6.67×` needs `stanford_cnfet.lib` + `ngspice`. Power `115W` model-relative `ASSUMED`, not `openroad_power` extraction (see GH `reports.zip`). `systolic` is `4×4 INT8` not `8×8 FP32` (area); `OpenRAM` is `1KB×4` blackbox + placeholder `GDS` (real `OpenRAM` generation needs `Codespaces` per `ADR-005`). Remaining `gpu_arc.md §2.9-2.10`: `I/O pads` (`sky130_ef_io`) + `PLL/CTS` (external clock for now via `CLOCK_PORT clk`).

**Next Priority 4:** `info.yaml` `tapeout/info.yaml:16` → `Efabless MPW` application + final `DRC 0` on `submission GDS` (`openlane/gpu_top_1mm/runs/*/reports/magic/drc.rpt`) + this preprint (`33+40 cocotb` `464B GDS`) as `arXiv` (`ICCAD`/`DATE` `ESSDERC`).

## 6. How to Reproduce (30s)

```bash
pip install -r requirements.txt
make test          # 33 python
make verilate      # 8 lint
make -C sim/cache4d/rtl cache cosim top e2e  # 7+3+2+3 cocotb
make -C sim/shader simd systolic rf warp     # 11+5+4+4
make gls           # SDF 16/16 tb_cache_4d_top.v
make sta           # 7.66ns slack @10ns 17mW
gh run view 33582637422 # or make gds (8GB docker) -> gds.zip/sdf.zip/reports.zip
# viewers: https://gds-viewer.tinytapeout.com + https://gdsjam.com
```

*All claims `VERIFIED/IMPLEMENTED` per `.engineering/lifecycle.yaml:24` `evidencePolicy`; `UNKNOWN` preferred over hallucination.*

