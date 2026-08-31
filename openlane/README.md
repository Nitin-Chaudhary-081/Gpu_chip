# OpenLane Phase C — RTL-to-GDSII `gpu_1.md:2`

Si-proxy flow: `CNFET` `gpu.md:5` / `photonics` `gpu.md:6` / `M3D` `gpu.md:6` have no `sky130` PDK cells. We synthesize the **verified 4D controller** `sim/cache4d/rtl/cache_4d_controller.sv:1` on `sky130_fd_sc_hd` (Si MOSFETs) as a proxy. CNFET power advantage `gpu.md:5 Vdd/2 3×` is kept in `sim/cnfet/cnfet_model.py:13` (ASSUMED, not in GDS).

## Configs

- `cache4d/config.json` — `cache_4d_controller`, `sky130A`, `clk 10ns (100MHz)` matches `tb_vcd.sv:13`, `DIE 200×200um`, `UTIL 40%` — fits TinyTapeout tile `gpu_1.md:6`.
- `wdm_arbiter/config.json` — `wdm_tdm_arbiter`, `DIE 120×120um`.

Both set `RUN_LVS` + `RUN_KLAYOUT_DRC` + `RUN_MAGIC_DRC` for `gpu_1.md:4`.

## Local run (needs 8GB RAM — not this 1.9GB VM)

```bash
# pinned OpenLane2 container bundles Yosys+OpenROAD+Magic+KLayout  gpu_1.md:3
docker run --rm -v $PWD:/project -w /project efabless/openlane:latest \
  --design openlane/cache4d --tag cache4d_run
# output: openlane/cache4d/runs/cache4d_run/results/final/gds/cache_4d_controller.gds  gpu_1.md:3
```

On this VM, only `Yosys` synth (light) runs:

```bash
make synth          # yosys gate count + area via sky130 liberty (or generic)
```

## GH Action (zero local RAM) — recommended for this VM

Template `.github/workflows/gds.yaml` will call `TinyTapeout` CI which runs OpenLane remotely and uploads `gds` artifact. Configs are already `TinyTapeout` compatible (`DESIGN_IS_CORE=false`, `FP_SIZING=absolute`).

## Mapping notes

- `CNFET` → `sky130_fd_sc_hd` standard cells (proxy). Real CNFET cells would need `Stanford CNFET` PDK (no public GDS). Power delta documented in `drc_lvs/waivers.md`.
- `photonics` waveguide → `met4` routing proxy, `fJ/bit` `gpu_1.md:6` stays in `sim/photonics/interconnect.py:11` model.
- `M3D` tiers → single `sky130` tier stacking modeled in `sim/thermal/thermal3d.py:1`, not in GDS (would need 3D PDK).

Output `GDSII` `gpu_1.md:3` is the foundry blueprint `tapeout/gds/*.gds`.
