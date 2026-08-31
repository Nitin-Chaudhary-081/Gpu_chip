# Bring-Up Pinout & Test Plan — `gpu_1.md:8`

## From `VCD` to silicon probe

Sim stimulus `sim/cache4d/rtl/tb_vcd.sv:28` drives 8 vectors with `slot->cycles` mapping:

| Vector | (x,y,z,t) | slot `(z+t)%4` | cycles `4+slot*2` | `λ t%8` |
|---|---|---|---|---|
| 1 | 5,7,0,0 | 0 | 4 | 0 |
| 2 | 5,7,0,1 | 1 | 6 | 1 |
| 3 | 5,7,0,2 | 2 | 8 | 2 |
| 4 | 5,7,0,3 | 3 |10 | 3 |
| 5 | 1,2,3,4 | 3 |10 | 4 |
| 6 |10,20,7,2 | 1 | 6 | 2 |

Silicon must reproduce identical `resp_*` on `logic analyzer` `gpu_1.md:8`.

## TinyTapeout wrapper pins `tapeout/tt_wrapper.sv:11`

- `ui_in[7]` = packet strobe (high = start 3-byte req)
- `ui_in[6:0]` + next 2 bytes serialize `24-bit` req `{valid,is_store,x6,y6,z5,t4}`
- `uo_out[7:0]` serializes `16-bit` resp over 2 cycles: `{valid,hit,bank4,lambda3,slot2,cycles4}`
- `clk` = `10ns` (100MHz) per `openlane/cache4d/config.json:5`, matches `tb_vcd.sv:13`
- `rst_n` active low, `ena` tied high

## Hookup `gpu_1.md:8`

- Die → ceramic `QFN`/`WSB` carrier → `PCB` breakout → `Digilent Analog Discovery` or `Saleae Logic 8` + `Rigol DS1054Z` scope.
- Drive `clk` from FPGA (`25MHz` safe for `sky130`) or external osc; probe `resp_valid`/`resp_cycles`.
- Script `bringup/testboard/logic_analyzer.py` (to add) replays `tb_vcd` vectors and asserts `resp_cycles == 4+slot*2`.

## Power `gpu_1.md:3 <120W` vs silicon

- Model: `sim/cnfet/cnfet_model.py:87` `Vdd 0.45V` + `sim/photonics/interconnect.py:power_at_BW` → `3.2W` demo, `~115W` full GPU (see `docs/arch.md:5`).
- Silicon `sky130` proxy will measure higher (`Vdd 1.8V` core). Do not claim `CNFET` power on probe; note `INFERRED` delta `6.6×` from `yosys` gate count proxy.
- Thermal `microfluidics` `gpu.md:15` cannot be probed on `sky130` tile; compare `sim/thermal/thermal3d.py:71C` vs board `thermistor`.

## Pass criteria `gpu_1.md:8`

- `resp_valid` asserts 1 cycle after `req_valid` (pipeline).
- `resp_cycles` matches Python `sim/cache4d/cache4d.py:67` for all 8 vectors.
- `resp_lambda == t%8`, `resp_slot == (z+t)%4`.
- No `DRC`-induced shorts (`waivers.md`).
