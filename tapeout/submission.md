# Tape-Out Submission — `gpu_1.md:6`

## Choices `gpu_1.md:6`

| Shuttle `gpu_1.md:6` | Size | Cost | Schedule | Fit for `cache_4d_controller` |
|---|---|---|---|---|
| **TinyTapeout** (educational, `SkyWater130`) | `150×170um` tiles aggregated to `≈10×10mm` wafer | `~$300` + shipping | Quarterly, GH Action builds GDS | **Fits** — our `DIE 200×200um` `openlane/cache4d/config.json:9` is +17% over TT tile → must shrink to `160×100` or use 2 tiles |
| `MOSIS` commercial `SkyWater` MPW | Full `10mm²` | `~$9750` / `40 projects` | Biannual | Fits whole GPU slice but cost |
| `Efabless` open `MPW-8` | `10mm²` | Free via lottery | `MPW-8` closed, `MPW-9` TBD | Lottery |

**Recommended (A):** `TinyTapeout` via GH Action — this VM `1.9GB` cannot run `OpenLane` Docker (`8GB` needed).

## Checklist before `GDSII` `gpu_1.md:3` hand-off

- [ ] `yosys` synth `42 cells` `openlane/synth_cache.ys` `VERIFIED` (done on this VM)
- [ ] `verilator lint` `0 errors` `make verilate` (done)
- [ ] `cocotb` `7/7` + `3/3` `make cocotb` (done)
- [ ] `DIE_AREA` shrink to `TinyTapeout` tile (`160×100um`) if targeting 1 tile, or request 2 tiles
- [ ] Wrapper `tapeout/tt_wrapper.sv` that serializes `21-bit req` over 8 pins (`NOT_IMPLEMENTED` — see below)
- [ ] Real `OpenLane` Docker run on `8GB` host or GH Action → `gds` in `tapeout/gds/` (requires large host)
- [ ] `DRC 0` + `LVS 0` per `drc_lvs/waivers.md` (photonics/M3D waived)
- [ ] `docs/datasheet.md` + `tests` vector dump for foundry

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
