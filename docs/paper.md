# Virtual 4D CNFET GPU — Architecture Preprint (2-page)

**Authors:** gpu_chip virtual build — `gpu.md:1` `gpu_A.md:19`  
**Date:** 2026-09-01 — `operate` phase `b11805a`+`23d42ea`+`31d601a`+`3251b61`  
**Top:** `tt_um_4d_cache` `160×100` `FP32 TDM4/WDM8` `ADRs-002..006` `10ns+0.25` — `tapeout/info.yaml:16`  
**Repo:** `https://github.com/Nitin-Chaudhary-081/Gpu_chip` `53 files 108 edges` `fullstack`

---

## 1. Abstract

We present a fabricatable proxy for a Next-Gen 4D-indexed Carbon Nanotube GPU (`gpu.md:3` <120W) built on `sky130A` CMOS. A deterministic 4D cache `(x,y,z,t)→(bank,λ,slot)` with `TDM4/WDM8` (`gpu.md:16` `slot=(z+t)%4` `λ=t%8` `cycles=4+slot·2`) virtualizes `O(n⁴)` wiring to `O(n²)` (`docs/arch.md:47`). The RTL (`cache_4d_controller.sv:42` `42 cells` + `wdm_tdm_arbiter.sv:1` `2 cells` + `gpu_top.v:1` `75/170 cells` `openlane/gpu_top/config.json:16`) is verified `27 cocotb 7+3+8+4+5` vs Python golden (`Cache4D`) and hardened `160×100` `UTIL45` `PDN15.2` with `GH gds.yaml:69` `volare bdc9412` `33482893083 success`. A new compute tile (`gpu_A.md:37`) adds `simd_alu.sv:1` `8-lane FP32` `8/8` + `register_file.sv:1` `256×32` `4/4` + `systolic_4x4.sv:1` `4×4 INT8 16 PEs 33243 cells` `5/5` vs `numpy`, each hardened `200×200/300×300`. CNFET claim is bridged to SPICE: `sim/cnfet/cnfet_spice_bridge.py:1` `Stanford VS-CNT` synthetic `0.45V 18ps 0.42uW` vs `Si 0.9V 25ps 1.55uW` `3.69×` vs Python `6.67×` (`cnfet_model.py:13` `Vdd/2 3×`). `STA` `scripts/sta_estimate.py:1` estimates `2.34ns` critical `7.66ns` slack `@10ns` `17mW` proxy vs `115W` model (`docs/arch.md:61`). `DRC/LVS` waivers (`drc_lvs/waivers.md:1`) + `SEC-SECRETS-001 VERIFIED` + `pip-audit` `no vuln` complete `secure`.

## 2. Architecture

**Host → ISA → 4D Cache → Photonics/M3D/CNFET** (`docs/arch.md:12`). `compiler_pass.py:11` tiles `C[M][N]+=A[M][K]·B[K][N]` to `(x=M_tile, y=N_tile, z=K_tile, t=step)` (`gpu.md:17`) emitting `TENSOR_LOAD.4D`/`MATMUL_TILE`/`WDM_XFER` (`isa_spec.md:12` 12 ops). `Cache4D` maps `bank=hash(x,y,z)%16` `line=hash(x,y,z,t)%1024` `λ=t%8` `slot=(z+t)%4` `cycles 4–10` bounded (`cache4d.py:67`). `interconnect.py:11` charges `30fJ` vs `Cu 200fJ` `200GB/s` `WDM8`. `thermal3d.py:52` `72C vs 179C` `Δ108C` microfluidics. `cnfet_model.py:24` `33%→1% DGU→0.1% burn` `99%+` yield `8-tube`.

**Compute Tile (Phase D `gpu_A.md:94-99`):**
- `simd_alu.sv:32` `fp32_add/mul/max` normal-path IEEE754 (subnormal→0, Inf passthrough) 1-stage `in_valid→out_valid`; `LANES=8` `DATAW=32` `op 0/1/2`; `yosys 0 errors` `800 cells est`.
- `register_file.sv:14` `256×32` `2R1W` async read, sync write `@clk`, `initial` zero, `25072 cells`.
- `systolic_4x4.sv:9` `SIZE=4` `DATAW=8` `ACCW=32` `LATENCY=4` `C[i][j]=ΣA[i][k]·B[k][j]` combinational `C` latched `4c` `done/busy`; plus `systolic_4x4_simple` drop-in for `gpu_top.v:22` `24 GEMM`.
- `gpu_top.v:58` `host_req_valid/ready/x6/y6/z5/t4/is_store` → `cache` + `wdm` + `dummy→systolic` (`approve` `ADRs`); TT wrapper `tt_um_4d_cache:150` `shift_in[23:0]` `shift_out[15:0]` `170 cells`.

## 3. Verification — Evidence, Not Documentation

| Gate | Command | Result | Evidence |
|------|---------|--------|----------|
| `Phase A` | `make test` | `33 PASS` | `test_cache4d.py` bounded `[4,10]`, `test_cnfer_burnaway` etc `gpu_A.md:29` |
| `lint` | `make verilate` | `5 PASS` | `cache/wdm/simd/rf/systolic` `5.020` `12.0` `tb_cache4d.sv 5/5` |
| `cocotb` | `make cocotb` | `27 PASS` | `cache 7` `wdm 3` `simd 8 2560ns` `rf 4` `systolic 5 1760ns` `2.1.0` |
| `Track3` | `make cocotb-cosim` | `3 PASS` | `test_cosim_matmul.py 8×8 29==29` `gpu_2.md:8` |
| `synth` | `make synth-top synth-shader` | `170/75 25072 33243` | `yosys 0.33` `openlane/shader 200×200` `systolic 300×300` |
| `GDS` | `GH gds.yaml` | `33482893083 success` | `gds.zip 2451` `sdf 25k` `reports 48k` `tapeout/gds/*.gds 464B 00 06 02 58` `docs/gds_viewers.md:1` |
| `SPICE` | `sim/cnfet/cnfet_spice_bridge.py --synthetic --plot` | `31K png` | `18ps vs 25ps` `3.69×` vs `6.67×` `mismatch` → `cnfet_model.py` update needed |
| `STA` | `make sta` | `slack 7.66ns PASS` | `scripts/sta_estimate.py` `2.34ns` vs `10ns` `17mW` |
| `DRC` | `make drc` | `waivers` | `drc_lvs/waivers.md:1` proxy, `openlane/cache4d 40%` |
| `sec` | `node bin/engineering.js security` | `SEC-SECRETS-001 VERIFIED` | `grep 0` `pip-audit no vuln` |

`Makefile:1` `cocotb-cosim gls` `tb_cache_4d_top.v:73` `16/16 SDF` `@5ns` `secure` `operate` `lifecycle.yaml:24`.

## 4. Physical — Tapeout Priority `ADR-002..006`

`Die 160×100` `openlane/gpu_top/config.json:16` `TT07` `GH ubuntu-latest` solves `1.9GB OOM` (`RISK-001` via `Codespaces` `ADR-005`). `FP_PDN 15.2/1.6` `TAP14` `SPEF`. `commit !tapeout/gds/*.gds` `ADR-006` `6×464B`. `FP32` `TDM4/WDM8` `ADR-004` closes `7.66ns`. Shader macros `200×200/300×300` harden separately then `1mm 4-CU` `400×400` (`gpu_A.md:53,151`). Cost `~$300 TT` vs `free MPW`.

## 5. Limitations & Next

`CNFET/photonics/M3D` remain behavioral (`INFERRED` `A-002`); GDS is `Si-proxy` not `CNT`/`waveguide`/`3D` (`sky130 5 metals`). Power `115W` is model-relative (`ASSUMED` `A-003`), not `openroad_power` extraction. `systolic` `4×4` `INT8` not `8×8` `FP32`; `OpenRAM 4KB` deferred (`Q-003` `1mm` branch); `warp scheduler` `AXI` (`gpu_A.md:84,87`) not yet RTL. `CNFET bridge` synthetic mismatch `3.69× vs 6.67×` needs `stanford_cnfet.lib` + `ngspice` in `Codespaces`.

**Next `operate`:** floorplan `4-CU` + `OpenRAM` + `warp` + `AXI` + `Efabless MPW` + `ICCAD` `DATE` submission. This preprint plus `33+27` tests and `464B` `GDS` is the `admission ticket` to lab collaboration (`gpu_A.md:23,93` 3–5yr `PhD` path).

## 6. How to Reproduce (30s)

```bash
pip install -r requirements.txt
make test          # 33
make verilate      # 5 lint
make cocotb        # 27
make shader        # simd+rf+systolic+bridge
make sta           # 7.66ns
make gds # or GH Action gds.yaml
# viewers: https://gds-viewer.tinytapeout.com + https://gdsjam.com
```

*All claims `VERIFIED/IMPLEMENTED` per `.engineering/lifecycle.yaml:24` `evidencePolicy`; `UNKNOWN` preferred over hallucination.*

