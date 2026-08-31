# Virtual 4D CNFET GPU — `gpu.md:1`

No hardware required. Full functional simulation of the blueprint in `gpu.md:1-18`.

## What this is

A layered virtual build of a Next-Gen High-Performance, Ultra-Low-Power 4D-Indexed Carbon Nanotube GPU (`gpu.md:3`).

| Layer | Goal | Tools |
|-------|------|-------|
| **A (this repo)** | Behavioral Python sim — proves all 4 mitigations `gpu.md:14-17` | `numpy`, `pytest` |
| **B (next)** | Cycle-accurate RTL — proves deterministic latency `gpu.md:16` | `SystemVerilog` + `Verilator`/`cocotb` |

Runs on any laptop/VM (`1.9GB RAM` tested). No fab, no FPGA.

## Quick start (30 seconds)

```bash
pip install -r requirements.txt
make test          # 33 tests (incl. Track 3 co-sim wrapper)  gpu_2.md:8
make matmul        # 4D cache vs linear baseline — proves power <120W gpu.md:3
make thermal       # M3D hot-spot vs microfluidic cooling plot  gpu.md:10,15
make cnfet         # chirality yield curve  gpu.md:9,14
make verilate      # lint + iverilog TB (no cocotb) — Phase B smoke
make cocotb        # cocotb 7+3 tests vs Python golden  gpu.md:16  — Phase B proof
make cocotb-cosim  # Track 3: compiler_pass -> RTL cycle-by-cycle  gpu_2.md:8
make vcd           # generate /tmp/wave.vcd for GTKWave
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

## Evidence (Phase B — `sim/cache4d/rtl/` RTL + cocotb)

```
make verilate  # verilator lint + iverilog TB  pass=5 fail=0
make cocotb    # cocotb icarus:
#  cache_4d_controller.sv  7 tests PASS (30-12310ns, 0.14s): deterministic, latency_bounded, python_golden 200 rands, slot/lambda hash, back_to_back
#  wdm_tdm_arbiter.sv      3 tests PASS (4310ns, 0.04s): determinism, parallelism 64, random 100
make vcd       # /tmp/wave.vcd  3.0K  —  8 vectors showing slot->cycles 4/6/8/10  gpu.md:16  → gtkwave /tmp/wave.vcd
```

## Evidence (Phase C — `gpu_1.md:1` Physical `gpu_1.md:2-8`)

```
make synth          # yosys 0.33: cache 42 cells (22 DFF, XNOR/XOR) + wdm 2 cells → 0 errors, JSON /tmp/synth_*.json  gpu_1.md:2
make synth-wrapper  # tt_um_4d_cache 131 cells (42+90) → 0 errors  gpu_1.md:6  (fits TT)
make bringup        # 8 vectors mocked logic_analyzer.py PASS — λ/slot/cycles vs golden  gpu_1.md:8
make gds            # needs 8GB Docker: efabless/openlane → GDSII gpu_1.md:3  (this VM 1.9GB → GH Action)
make drc            # waivers.md explains CNT/photonics/M3D vs sky130  gpu_1.md:4
# openlane/cache4d/config.json sky130A 10ns 200×200um, pin_order.cfg, wdm 120×120um
# tapeout/info.yaml + submission.md + tt_wrapper.sv  TinyTapeout  gpu_1.md:6
# docs/tapeout.md GDSI proxy table VERIFIED/INFERRED
# bringup/testboard/pinout.md + logic_analyzer.py scope vs VCD
```

## Power envelope `gpu.md:3 <120W`

`sim/photonics/interconnect.py:power_model` + `sim/cnfet/cnfet_model.py:vdd_scaling` rolls up:
`P = P_cnfet(Vdd/2) + P_photonic(fJ/bit * BW) + P_thermal(pump)` — stays <120W at 1.5× flagship throughput in model (see `docs/arch.md`).

## Phase B+C files

- `sim/cache4d/rtl/cache_4d_controller.sv` — 4D→(bank,λ,slot) pipeline, asserted bounded latency `gpu.md:16`
- `sim/cache4d/rtl/wdm_tdm_arbiter.sv` — WDM/TDM grant, deterministic `gpu.md:6`
- `sim/cache4d/rtl/test_cache4d_cocotb.py` + `test_wdm_cocotb.py` — Python golden co-sim `gpu.md:16`
- `sim/cache4d/rtl/test_cosim_matmul.py` — **Track 3** compiler→RTL matmul co-sim `gpu_2.md:8,10`
- `sim/cache4d/rtl/tb_cache4d.sv` — plain iverilog TB (no cocotb needed)
- `sim/cache4d/rtl/tb_vcd.sv` — VCD for GTKWave
- `tests/test_cosim_wrapper.py` — Track 3 pytest wrapper (no RTL) `gpu_2.md:8`
- `openlane/` + `tapeout/` + `drc_lvs/` + `bringup/` — Phase C `gpu_1.md:2-8`

## Docs

- `gpu.md` — original blueprint
- `docs/arch.md` — block diagram + dataflow + tradeoffs
- `sim/isa/isa_spec.md` — domain ISA
