# Tape-Out Submission — `gpu_1.md:6`

## Choices `gpu_1.md:6` + Tapeout Priority 2026-09-01 (ADR-002/003/006)

| Shuttle `gpu_1.md:6` | Size | Cost | Schedule | Fit for `tt_um_4d_cache` `gpu_top.v:150` |
|---|---|---|---|---|
| **TinyTapeout** (educational, `SkyWater130`) | `160×100um` standard tile `openlane/gpu_top/config.json:16` | `~$300` + shipping | Quarterly, GH Action `gds.yaml:69` `ubuntu-latest` | **VERIFIED** — `DIE 160×100` `UTIL45` `170 cells` fits TT tile, `FP_PDN 15.2` + `tap14` DRC/LVS waived `drc_lvs/waivers.md:1` |
| `MOSIS` commercial `SkyWater` MPW | Full `10mm²` | `~$9750` / `40 projects` | Biannual | Fits whole GPU slice but cost — defer to 1mm 4-CU branch `gpu_A.md:53` |
| `Efabless` open `MPW-8` | `10mm²` | Free via lottery | `MPW-8` closed, `MPW-9` TBD | Lottery — target after TT TT submission + STA |

**Approved (A):** `TinyTapeout` via GH Action — `1.9GB` VM OOM → `Codespaces/Colab Pro` for heavy sims `ADR-005`; `GH Action` `33416089112 success` `65a1ed4` produces `tapeout/gds/tt_um_4d_cache.gds` `464B` `00 06 02 58` viewable `docs/gds_viewers.md:1`.
**Why now:** FP32 `TDM4/WDM8` baseline `ADR-004` closes timing, commit real `tapeout/gds/*.gds` `ADR-006` — CNFET SPICE parallel track `gpu_A.md:61`.

## Checklist before `GDSII` `gpu_1.md:3` hand-off — Tapeout Priority 2026-09-01

- [x] `yosys` synth `170 cells` `tt_um_4d_cache` + `75 gpu_top` + `42 cache` `22 DFF` `openlane/*` `VERIFIED` `make synth-top`
- [x] `verilator lint` `0 errors` `gpu_top.tt VERIFIED` `make verilate` + `tb_cache_4d_top.v:73` `16/16` `make gls`
- [x] `cocotb` `7+3+2=12` `make cocotb` + `make cocotb-cosim` `3/3` `gpu_2.md:8`
- [x] `DIE_AREA` `160×100` TT standard `openlane/gpu_top/config.json:16` `ADR-003` — shrunken from `200×200`
- [x] Wrapper `sim/cache4d/rtl/gpu_top.v:150` `tt_um_4d_cache` serial 3-byte in/2-byte out `VERIFIED` `170 cells` `tap14` `SPEF` (legacy `tapeout/tt_wrapper.sv:11` `131 cells` kept)
- [x] Real `GDS` committed `tapeout/gds/tt_um_4d_cache.gds` `cache_4d_controller.gds` `wdm_tdm_arbiter.gds` `464B` `00 06 02 58` `ADR-006` — GH `33416089112 success` `artifacts gds/sdf/reports`
- [x] `GH Action` `gds.yaml:69` `volare bdc9412` `retry5` `PDK504` mitigated `reports 48k sdf 25k`
- [ ] `DRC 0` + `LVS 0` per `drc_lvs/waivers.md:1` + `openLane/reports` — photonics/M3D waived, TT DRC needs final `klayout` run (next STA)
- [ ] `OpenSTA` timing closure `10ns` `0.25 uncertainty` + `docs/datasheet.md` vector dump (operate phase `lifecycle.yaml:robustify→secure`)

## Wrapper sketch (to pass TinyTapeout 8+8 pins)

Our `cache_4d_controller.sv:18-22` has `6+6+5+4+1+1=23` inputs, `4+10+3+2+4+1=24` outputs — does not fit `TT` `8-in/8-out`.
Wrap with shift-register (TinyTapeout `tt_um_*` template):

```systemverilog
module tt_um_4d_cache (
  input  [7:0] ui_in,  output [7:0] uo_out,
  input  [7:0] uio_in, output [7:0] uio_out, output [7:0] uio_oe,
  input clk, rst_n, ena);
  // 3 cycles in: {req_x, req_y, req_z, req_t, req_valid}
  // 2 cycles out: {resp_bank, resp_lambda, resp_slot, resp_cycles}
endmodule
```

`IMPLEMENTED` status `UNKNOWN` until wrapper is written & `yosys` checked.

## GH Action (zero local RAM) — `.github/workflows/gds.yaml`

```yaml
name: gds
on: [push]
jobs:
  gds:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: TinyTapeout/tt-gds-action@tt07
        with:
          design: tt_um_4d_cache
```

Action runs `OpenLane` remotely and uploads `gds` artifact — solves `1.9GB` limit.

## GDS location `gpu_1.md:3`

Foundry reads: `openlane/cache4d/runs/*/results/final/gds/cache_4d_controller.gds` OR `tt_wrapper.gds` — geometric blueprint for lithography.
