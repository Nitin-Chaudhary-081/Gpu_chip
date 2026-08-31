# Domain-Specific ISA — gpu.md:17

Maps high-level tensors to 4D cache coords transparently `gpu.md:17`.

## Registers

- `T0..T7` tensor tile registers (4D coords attached)
- `A0..A3` address/coordinate registers `(x,y,z,t)`
- `C0` control / predicate

## Instructions (12 ops)

| Op | Format | Cycles | Desc |
|----|--------|--------|------|
| `TENSOR_LOAD.4D Tdst, (x,y,z,t), #tile` | `T, Coord` | 4-10 (slot) | Load tile from 4D cache `gpu.md:7` |
| `TENSOR_STORE.4D Tsrc, (x,y,z,t)` | `T, Coord` | 4-10 | Store tile |
| `MATMUL_TILE Tdst, TsrcA, TsrcB` | `T,T,T` | 8 | `Tdst += TsrcA * TsrcB` (systolic) |
| `CONV_TILE` | `T,T,T` | 12 | 2D conv tile |
| `VEC_ADD/SUB/MUL` | `T,T,T` | 4 | Vector ops on tile |
| `WDM_XFER Rd, Rs, #λ` | `R,R,imm` | 2+slot | Photonic wavelength xfer `gpu.md:6` |
| `TDM_WAIT #slot` | `imm` | slot*2 | Deterministic wait `gpu.md:16` |
| `CACHE_MAP A0, (x,y,z,t)` | `R,Coord` | 1 | Virt→phys mapping, sets λ/slot |
| `BARRIER` | — | — | Tier sync for M3D |
| `HALT` | — | — | End kernel |

Encoding: 32-bit, `[op:6][dst:4][src1:4][src2:4][coord/lambda:14]`

## Example: Matmul M=64 tiled 8

```asm
; compiler_pass emits this from numpy matmul
CACHE_MAP A0, (0,0,0,0)
TENSOR_LOAD.4D T0, (0,0,0,0), #8   ; A tile
TENSOR_LOAD.4D T1, (0,0,0,0), #8   ; B tile
MATMUL_TILE T2, T0, T1
WDM_XFER T2, T2, #λ2               ; photonic move to next bank
TDM_WAIT #1
TENSOR_STORE.4D T2, (0,0,0,1)
HALT
```

Compiler (`compiler_pass.py`) lowers `torch.einsum` / `numpy` → this ISA automatically. Linear CUDA addr `base+offset` `gpu.md:12` never exposed.
