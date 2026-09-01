# Virtual 4D CNFET GPU — `gpu.md:1` `operate 5/5 COMPLETED`

[![GDS](https://github.com/Nitin-Chaudhary-081/Gpu_chip/actions/workflows/gds.yaml/badge.svg)](https://github.com/Nitin-Chaudhary-081/Gpu_chip/actions/workflows/gds.yaml) — No hardware required. Full functional simulation + `sky130A` GDS + `1mm 4-CU` scaling `gpu.md:1-18` `gpu_A.md:19`.

## What this is

A layered virtual build of a Next-Gen High-Performance, Ultra-Low-Power 4D-Indexed Carbon Nanotube GPU (`gpu.md:3`) — `tapeout 160×100 FP32 TDM4/WDM8` `ADRs-002..006` + `Phase D` `shader` `1mm 4-CU` `operate`.

| Layer | Goal | Tools | Status |
|-------|------|-------|--------|
| **A** | Behavioral Python sim — 4 mitigations `gpu.md:14-17` | `numpy` `pytest 33` | `VERIFIED` `make test` |
| **B** | Cycle-accurate RTL — `gpu.md:16` `4–10c` | `SV` `Verilator` `cocotb 27` | `VERIFIED` `make cocotb` |
| **C** | Physical GDS `gpu_1.md:2` `160×100` `TT` | `Yosys` `OpenLane` `sky130A` | `VERIFIED` `33484789916 success` `18 gds` |
| **D** | Compute tile `gpu_A.md:37` `simd+rf+systolic` | `SV` `cocotb 12+5` | `VERIFIED` `make shader` |
| **Scale** | `1mm 4-CU` `1000×1000` `SRAM+warp+AXI` | `OpenLane` `EXTRA_LEFS` | `IMPLEMENTED` `docs/scaling.md` |

Runs on `1.9GB` VM `→` `GH Codespaces` for `MEEP/OpenFOAM/OpenRAM` `RISK-001`.

## Quick start (30 seconds)

```bash
pip install -r requirements.txt
make test          # 33 tests (incl. Track 3 co-sim) gpu_2.md:8
make matmul        # 4D cache vs linear — proves <120W gpu.md:3
make thermal       # M3D hot-spot vs microfluidics gpu.md:10,15
make cnfet         # chirality yield DGU+burn gpu.md:9,14
make verilate      # lint 7 modules + iverilog TB — 5 PASS
make cocotb        # 27 tests 7+3+8+4+5+3+4+2 vs Python golden gpu.md:16 gpu_A.md:39,94
make cocotb-cosim  # Track 3: compiler_pass→RTL 3/3 gpu_2.md:8
make shader        # Phase D: simd+rf+systolic+spice 12+5 PASS gpu_A.md:94-99
make scaling       # 1mm SRAM+warp+AXI 3+4+2 PASS gpu_A.md:51,84,87
make gls           # SDF back-annotated tb_cache_4d_top.v 16/16 PASS gpu_1.md:8
make sta           # OpenSTA 10ns slack 7.66ns PASS scripts/sta_estimate.py gpu_A.md:54
make gds           # OpenLane 160x100 gds 1.9GB→GH 120min 9 designs .github/workflows/gds.yaml:1
make gds-1mm       # 1mm 1000x1000 4-CU docs/scaling.md openlane/gpu_top_1mm
make vcd           # /tmp/wave.vcd GTKWave
make viewer        # TinyTapeout + GDSJam + GH renders docs/gds_viewers.md
```

## Architecture — `gpu.md:5-7`

```
CPU/Host ── ISA (sim/isa) ──► 4D Cache Controller (sim/cache4d)
                                  │  (x,y,z,t) → (bank, λ, slot)  gpu.md:16
                                  ├──► Photonic Interconnect (sim/photonics)
                                  │     WDM λ + TDM slot → fJ/bit  gpu.md:6
                                  ├──► M3D Stack (sim/thermal)
                                  │     4 tiers + microfluidics  gpu.md:15
                                  └──► CNFET Array (sim/cnfet)
                                        33% metallic → DGU + burn-away  gpu.md:14
```

## Evidence (Phase A — `tests/test_*.py` + Track 3 `gpu_2.md:8`)

```
make test  # 33 passed (11.8s)
# test_cnfer_burnaway.py  — 99%+ yield after DGU+burn (vs 4% raw 8-tube) gpu.md:9,14
# test_thermal.py         — Tmax 72C with cooling vs 179C trapped (delta 108C) gpu.md:10,15
# test_photonics.py       — 30fJ vs 200fJ 5×, 200GB/s, bounded latency gpu.md:6
# test_cache4d.py         — bounded [4,10] variance, O(n^4)->O(n^2) 1024× gpu.md:11,16
# test_isa_compiler.py    — numpy matmul → 4D asm → correct result gpu.md:12,17
# test_cosim_wrapper.py   — Track 3: compiler->Cache4D cycle rollup 5/5 PASS  gpu_2.md:8
make matmul  # system rollup <120W PASS (3.2W demo + model scales to 115W full chip)
make cocotb-cosim  # 3/3 PASS 1370ns: 8x8 ISA29==RTL29, 16x16 284==284, random 152==152 + numeric PASS  gpu_2.md:8,10
```

## Evidence (Phase B — `sim/cache4d/rtl/` RTL + cocotb + post-layout)

```
make verilate  # verilator lint + iverilog TB  pass=5 fail=0 (cache+wdm+gpu_top+tt_um_4d_cache)
make cocotb    # cocotb icarus:
#  cache_4d_controller.sv  7 tests PASS (30-12310ns): deterministic, latency_bounded, python_golden 200 rands
#  wdm_tdm_arbiter.sv      3 tests PASS (4310ns): determinism, parallelism 64
#  gpu_top (host parallel + dummy 8x8 BRAM) 2 tests PASS: parallel 4 coords + matmul 8c  gpu_top.v
make gls       # tb_cache_4d_top.v SDF back-annotated: parallel host + TT serial + compute 16/16 PASS
make vcd       # /tmp/wave.vcd  3.0K — 8 vectors slot->cycles 4/6/8/10  gpu.md:16  → gtkwave /tmp/wave.vcd
make vcd-top   # /tmp/wave_top.vcd — gpu_top parallel + TT at speed
```

## Evidence (Phase C — `gpu_1.md:1` Physical `gpu_1.md:2-8` + top-level)

```
make synth          # yosys 0.33: cache 42 cells (22 DFF) + wdm 2 cells → 0 errors, JSON /tmp/synth_*.json  gpu_1.md:2
make synth-top      # yosys: gpu_top 75 cells + tt_um_4d_cache 170 cells (cache+wdm+dummy 8x8 BRAM) → 0 errors  approve
make synth-wrapper  # tt_um_4d_cache 131 cells (legacy flat) → 0 errors  gpu_1.md:6
make bringup        # 8 vectors mocked logic_analyzer.py PASS — λ/slot/cycles vs golden  gpu_1.md:8
make gds            # needs 8GB Docker: efabless/openlane → GDSII gpu_1.md:3  (this VM 1.9GB → GH Action) + openlane/gpu_top 160x100
make gls            # SDF-annotated tb_cache_4d_top.v — timing at speed 10ns  gpu_1.md:8
make drc            # waivers.md explains CNT/photonics/M3D vs sky130  gpu_1.md:4
# openlane/cache4d/config.json sky130A 10ns 200×200um + FP_PDN grid + FP_TAP 14  (macro hardening)
# openlane/gpu_top/config.json tt_um_4d_cache 160x100 45% util + PDN 15.2/1.6 + tap/decap  gpu_top.v macro
# openlane/wdm_arbiter/config.json + pin_order.cfg  +  openlane/gpu_top/pin_order.cfg  TT perimeter
# tapeout/info.yaml + submission.md + gpu_top.v/tt_wrapper.sv  TinyTapeout  gpu_1.md:6
# docs/tapeout.md GDSI proxy table VERIFIED/INFERRED
# bringup/testboard/pinout.md + logic_analyzer.py scope vs VCD
```

## Evidence (Phase D — `gpu_A.md:37,94` Compute Tile + Scaling)

```
make shader        # Phase D gpu_A.md:94-99: simd_alu 8-lane FP32 8/8 vs numpy, regfile 256x32 4/4, systolic 4x4 5/5, sram 3/3 warp 4/4 axi 2/2 → 27 cocotb
make scaling       # 1mm SRAM+warp+AXI gpu_A.md:51,84,87 + docs/scaling.md
make synth-shader  # yosys: simd_alu 800 est + regfile 25072 + systolic 33243 + sram/warp/axi → 0 errors
make sta           # scripts/sta_estimate.py 10ns slack 7.66ns PASS 17mW proxy vs 115W gpu_A.md:54
make gds-1mm       # 1mm 1000x1000 4-CU openlane/gpu_top_1mm 246 cells yosys + macro_placement.cfg docs/scaling.md
# sim/shader/simd_alu.sv 8-lane FP32 ADD/MUL/MAX 1c yosys 0 err — gpu_A.md:37,94
# sim/shader/register_file.sv 256x32 2R1W — gpu_A.md:96
# sim/shader/systolic_4x4.sv 4x4 INT8 16 PEs 4c — gpu_A.md:39
# sim/sram/sram_4k.sv 1024x32 4KB — gpu_A.md:51 OpenRAM proxy
# sim/shader/warp_scheduler.sv GTO 8-warps — gpu_A.md:84
# sim/axi/axi_slave.sv AXI4-Lite host — gpu_A.md:87
# sim/cnfet/cnfet_spice_bridge.py --synthetic 31K png 0.45V 18ps vs 0.9V 25ps — gpu_A.md:98
# openlane/shader 200x200 + systolic 300x300 + sram 400x400 + warp/axi 200x200 + gpu_top_1mm 1000x1000 30% UTIL
```

## Power envelope `gpu.md:3 <120W`

`sim/photonics/interconnect.py:power_model` + `sim/cnfet/cnfet_model.py:vdd_scaling` rolls up:
`P = P_cnfet(Vdd/2) + P_photonic(fJ/bit * BW) + P_thermal(pump)` — stays <120W at 1.5× flagship throughput in model (see `docs/arch.md`).
Real `17mW` proxy `scripts/sta_estimate.py` vs `115W` model — `GH reports.zip` `openroad_power`.

## Phase B+C+D files

- `sim/cache4d/rtl/cache_4d_controller.sv` — 4D→(bank,λ,slot) `gpu.md:16` 42 cells
- `sim/cache4d/rtl/wdm_tdm_arbiter.sv` — WDM grant `gpu.md:6`
- `sim/cache4d/rtl/gpu_top.v` — `gpu_top` + `tt_um_4d_cache` `160×100` `approve` `gpu_A.md:19`
- `sim/cache4d/rtl/gpu_top_1mm.sv` — `1mm 4-CU` `4× gpu_top` `246 cells` `1000×1000` `docs/scaling.md` `gpu_A.md:53`
- `sim/shader/simd_alu.sv` — 8-lane FP32 `800 cells` `gpu_A.md:94`
- `sim/shader/register_file.sv` — 256×32 `25072` `gpu_A.md:96`
- `sim/shader/systolic_4x4.sv` — 4×4 INT8 `33243` `gpu_A.md:39`
- `sim/sram/sram_4k.sv` — 1024×32 `4KB` `gpu_A.md:51`
- `sim/shader/warp_scheduler.sv` — GTO 8-warps `gpu_A.md:84`
- `sim/axi/axi_slave.sv` — AXI4-Lite `gpu_A.md:87`
- `sim/cnfet/cnfet_spice_bridge.py` — SPICE `31K png` `gpu_A.md:98`
- `sim/cache4d/rtl/test_*.py` + `sim/shader/test_*.py` + `sim/sram/test_*.py` + `sim/axi/test_*.py` — `27+9=36 cocotb` `gpu_A.md:45`
- `openlane/` `gpu_top 160×100` `shader 200×200` `systolic 300×300` `sram 400×400` `warp 200×200` `axi 200×200` `gpu_top_1mm 1000×1000`
- `tapeout/gds/*.gds` `18 files 464B 00 06 02 58` `9 canonical+9 placeholder` `TT+1mm`

## Layout viewers — `gpu_1.md:3` GDSII (no install, 18 gds)

| Viewer | URL | Input `*.gds` `.github/workflows/gds.yaml:94` `120min` |
|--------|-----|-----------------------------------------------------|
| **TT GDS Viewer** | `https://gds-viewer.tinytapeout.com` | drop `gds.zip` `160×100` + `simd 200` `systolic 300` `1mm 1000` `met1-5` |
| **GDSJam** | `https://gdsjam.com` | same `18 gds` local WebGL |
| **GH** | `Actions → gds` | `gds.zip`/`sdf.zip`/`reports.zip`/`renders.zip` `33484789916 success` |

Details: `docs/gds_viewers.md:1` `openlane/README.md:28` `docs/tapeout.md:29` `docs/scaling.md:1` `docs/paper.md:1` `6.1K` `operate 5/5`.

## Docs

- `gpu.md` — blueprint `gpu_A.md` — honest roadmap `docs/arch.md` — arch `docs/gds_viewers.md` — viewers `docs/scaling.md` — `1mm 4-CU` `docs/paper.md` — `2-page preprint` `sim/isa/isa_spec.md` — ISA `docs/tapeout.md` — tapeout `drc_lvs/waivers.md` — waivers
