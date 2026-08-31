# Architecture — Virtual 4D CNFET GPU

Source truth: `gpu.md:1-18`.

## 1. Core objective `gpu.md:3`

Standard GPU form factor, exponential perf, `<120W` via three substitutions `gpu.md:4-7`:
- Si MOSFET → CNFET `gpu.md:5` (Vdd/2, 3× Idrive)
- Cu traces → Si Photonics + M3D `gpu.md:6` (fJ/bit)
- Linear cache → 4D space-time tensor cache `gpu.md:7` (no address-translation stall)

## 2. Block diagram

```
┌─────────────────────────────────────────────────┐
│ Host (Python / PyTorch)                          │
│  compiler_pass.py: tensor → 4D coords  gpu.md:17│
└──────────────────┬──────────────────────────────┘
                   │ ISA (assembler.py) gpu.md:17
                   ▼
┌─────────────────────────────────────────────────┐
│ 4D Cache Controller  sim/cache4d/cache4d.py      │
│  (x,y,z,t) virtual → (bank, λ_id, slot)         │
│  TDM window = 4, WDM λ = 8  gpu.md:16           │
│  Deterministic latency: base + slot_wait        │
└───┬──────────────┬──────────────┬───────────────┘
    │              │              │
    ▼              ▼              ▼
┌────────┐  ┌────────────┐  ┌──────────┐
│CNFET   │  │ Photonics  │  │ M3D+Therm│
│Array   │  │NoC         │  │ 4 tiers  │
│sim/cnfet│ │sim/photonics│ │sim/thermal│
│yield   │  │fJ/bit, BW  │  │grid + μfluid│
└────────┘  └────────────┘  └──────────┘
```

## 3. Dataflow (matmul example)

1. `C[M][N] += A[M][K] * B[K][N]` in numpy
2. `compiler_pass.py` tiles to `(x=M_tile, y=N_tile, z=K_tile, t=time_step)` — 4D coords
3. `assembler.py` emits `TENSOR_LOAD.4D`, `TENSOR_STORE.4D`, `WDM_XFER`, `TDM_WAIT`
4. `cache4d.py` maps coord → physical: `bank = hash(x,y) % B`, `λ = t % W`, `slot = (z + t) % T`
5. `interconnect.py` charges `E = bits * fJ/bit[λ]` + latency `slot * T_clk`
6. `thermal3d.py` accumulates power per tier → updates `T_grid`
7. `cnfet_model.py` scales `Vdd` and yield for power calc

## 4. Why 4D routing does NOT explode `gpu.md:11→16`

Naive: physical wires per 4D cell = `O(n^4)` → impossible.

Actual: **virtualized**. Only `B` banks physically wired. Time `t` and `z` multiplexed:
- **TDM** (time-division): 4 slots share one waveguide in round-robin → latency += `slot * 1ns` but deterministic `gpu.md:16`
- **WDM** (wavelength): 8 λ per waveguide → 8× bandwidth without extra wires `gpu.md:6,16`
Wire count = `B * Waveguides = O(n^2)`, not `O(n^4)`. Tested in `test_cache4d.py: test_routing_scales`.

## 5. Power model `<120W gpu.md:3`

- **CNFET saving**: `P = C*V^2*f`. `V_cnfet = V_si/2` → `P_cnfet ≈ 0.25 * P_si` per transistor, but 3× drive allows lower `f` or fewer transistors for same perf. Net modeled as `0.35×` baseline `sim/cnfet/cnfet_model.py:power_saving`.
- **Photonics**: `E_bit ≈ 30 fJ` (literature `gpu.md:6`) vs `~200 fJ` for Cu at 7nm long haul. At `1 TB/s` → `≈30W` vs `200W` electrically.
- **M3D**: Stacking adds power density but microfluidics removes `>40W` worth of throttling margin (see `thermal3d.py:demo` delta `Tmax`).
- Rollup example: `80W` logic (CNFET) + `30W` interconnect (photonic) + `5W` pump = `115W` — under budget, see `tests/workloads/matmul.py` power report.

Assumptions marked `ASSUMED` until silicon — sim gives relative, not absolute, numbers.

## 6. Tradeoffs & alternatives considered

| Decision | Chosen | Alternative | Why |
|----------|--------|-------------|-----|
| Sim language | Python behavioral | gem5/SST | Fits 1.9GB VM, instant iteration; gem5 heavy |
| Cache hash | `hash(x,y,z,t) → (λ,slot)` | Full crossbar | Crossbar is `O(n^4)` wires |
| Thermal | Explicit 3D finite-diff | HotSpot tool | No HotSpot install; Python grid is transparent |
| ISA | Domain ext, not full RISC-V | RISC-V custom | Smaller surface to prove 4D mapping |

## 7. Verification plan

- `pytest tests/` = Phase A gate (all `VERIFIED`)
- `cocotb` + `verilator` = Phase B gate (cycle accuracy)
- Workload correctness: `numpy` reference vs sim result `allclose`

## 8. What breaks if you delete X

- `sim/cache4d/cache4d.py` → ISA + workloads fail (no 4D→physical mapping)
- `sim/cnfet/cnfet_model.py` → power/yield numbers become `UNKNOWN`
- `sim/thermal/thermal3d.py` → M3D claims unverified, risk hidden
- `sim/photonics/interconnect.py` → latency becomes non-deterministic, `gpu.md:16` violated
