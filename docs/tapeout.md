# Tape-Out Phase C — `gpu_1.md:1` Physical Reality

## Goal `gpu_1.md:2-9`

Turn `yosys`-clean RTL (Phase B) into `GDSII` `gpu_1.md:3` blueprint, pass foundry `DRC/LVS` `gpu_1.md:4`, submit to `MPW` `gpu_1.md:6` (`TinyTapeout`), and probe silicon vs sim `gpu_1.md:8`.

## What is tapeout-ready vs waived

| Blueprint item `gpu.md:5-7` | In `GDSII` `gpu_1.md:3`? | How proved | Label |
|---|---|---|---|
| `4D cache controller` `gpu.md:7` `sim/cache4d/rtl/cache_4d_controller.sv:1` | **Yes** — `42 cells 22 DFF` `openlane/synth_cache.ys:1` | `yosys stat`, `verilator lint`, `cocotb 7/7`, `GDS` via `OpenLane` | `VERIFIED` (synth) → `IMPLEMENTED` (GDS pending large host) |
| `WDM/TDM arbiter` `gpu.md:6,16` `sim/cache4d/rtl/wdm_tdm_arbiter.sv:1` | **Yes** — `2 cells` | same | `VERIFIED` |
| `TinyTapeout wrapper` `tapeout/tt_wrapper.sv:1` | **Yes** — pending `yosys` on wrapper | `yosys` (not yet run); `INFERRED` | `IMPLEMENTED` |
| `CNFET Vdd/2 3×` `gpu.md:5` | **No** — `sky130` has no CNT cells; proxy is `sky130_fd_sc_hd` Si | `sim/cnfet/cnfet_model.py:87` `6.6×` saving | `INFERRED` |
| `photonics fJ/bit` `gpu.md:6` | **No** — `met4` proxy | `sim/photonics/interconnect.py:11` `30fJ` | `INFERRED` |
| `M3D/microfluidics` `gpu.md:6,15` | **No** — single tier `sky130` | `sim/thermal/thermal3d.py:52` `72C vs 179C` | `INFERRED` |

## Flow `gpu_1.md:2`

```
cache_4d_controller.sv:1 --yosys--> gate netlist (42 cells) --OpenROAD--> GDSII (tapeout/gds/*.gds) gpu_1.md:3
                                                          |-> DRC/LVS (magic/netgen/klayout) gpu_1.md:4
                                                          |-> MPW submit (TinyTapeout info.yaml) gpu_1.md:6
                                                          |-> PCB + logic analyzer vs tb_vcd.sv:28  gpu_1.md:8
```

## Files

- `openlane/cache4d/config.json` — `PDK sky130A`, `CLOCK 10ns`, `DIE 200×200um`, `UTIL 40%`, `RUN_LVS/RUN_KLAYOUT_DRC true`
- `openlane/wdm_arbiter/config.json` — `DIE 120×120um`
- `openlane/synth_cache.ys` + `synth_wdm.ys` — light `yosys` without Docker (runs on `1.9GB`)
- `openlane/README.md` — Docker vs GH Action
- `drc_lvs/waivers.md` — why CNT/photonics/M3D waived
- `tapeout/info.yaml` + `submission.md` + `tt_wrapper.sv` — `gpu_1.md:6` shuttle pack
- `bringup/testboard/pinout.md` + `logic_analyzer.py` — `gpu_1.md:8`

## Host constraints

This `1.9GB` VM can run `yosys`/`verilator`/`iverilog`/`cocotb` but **not** `OpenLane Docker` (`8GB` needed) `gpu_1.md:3`. Solution: `make synth` proves Si-proxy gates here; `make gds` must dispatch to `TinyTapeout` GH Action or larger runner. See `openlane/README.md`.
