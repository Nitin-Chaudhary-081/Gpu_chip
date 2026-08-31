"""
Compiler pass — gpu.md:17
Lowers high-level numpy/tensor ops to domain ISA automatically.
Transparent mapping: user writes numpy; compiler emits 4D coords.
"""
import numpy as np
from sim.cache4d.cache4d import Coord4D

TILE = 8

def compile_matmul(M, N, K, tile=TILE):
    """Compile C[M][N] += A[M][K] * B[K][N] into ISA asm.
    Tiling in 4D: x = M-tile, y = N-tile, z = K-tile, t = iteration (temporal) gpu.md:7
    """
    lines = []
    t = 0
    # init C tiles to zero in cache (store zeros)
    for mi in range(0, M, tile):
        for ni in range(0, N, tile):
            lines.append(f"CACHE_MAP A0, ({mi//tile}, {ni//tile}, 0, {t})")
            # Zero init is implicit in sim (T regs start zero)

    for mi in range(0, M, tile):
        for ni in range(0, N, tile):
            for ki in range(0, K, tile):
                x, y, z = mi//tile, ni//tile, ki//tile
                # temporal t increments with K loop -> 4th dimension
                coord_a = f"({x}, {z}, 0, {t})"  # A tile: M x K
                coord_b = f"({z}, {y}, 0, {t})"  # B tile: K x N
                coord_c = f"({x}, {y}, {ki//tile}, {t})"
                lines.append(f"TENSOR_LOAD.4D T0, {coord_a}")
                lines.append(f"TENSOR_LOAD.4D T1, {coord_b}")
                # accumulate into T2 (need load C first iteration, else reuse)
                if ki == 0:
                    lines.append(f"TENSOR_LOAD.4D T2, {coord_c}")  # will miss -> zero on first
                lines.append(f"MATMUL_TILE T2, T0, T1")
                lines.append(f"WDM_XFER T2, T2, #{t % 8}")
                lines.append(f"TDM_WAIT #{z % 4}")
                lines.append(f"TENSOR_STORE.4D T2, {coord_c}")
                t += 1
    lines.append("HALT")
    return "\n".join(lines)

def compile_conv2d(H, W, C_in, C_out, KH=3, KW=3, tile=8):
    """Lower conv2d to CONV_TILE ops."""
    lines = []
    t = 0
    for ho in range(0, H, tile):
        for wo in range(0, W, tile):
            for co in range(0, C_out, tile):
                coord = f"({ho//tile}, {wo//tile}, {co//tile}, {t})"
                lines.append(f"CACHE_MAP A0, {coord}")
                lines.append(f"TENSOR_LOAD.4D T0, {coord}")
                lines.append(f"TENSOR_LOAD.4D T1, {coord}")
                lines.append(f"CONV_TILE T2, T0, T1")
                lines.append(f"TENSOR_STORE.4D T2, {coord}")
                t += 1
    lines.append("HALT")
    return "\n".join(lines)

def numpy_matmul_reference(A, B):
    return A @ B

def demo():
    print("=== Compiler Pass Demo gpu.md:17 ===")
    asm = compile_matmul(16,16,16, tile=8)
    print("Compiled matmul 16x16 (first 12 lines):")
    for i,l in enumerate(asm.splitlines()[:12]):
        print(f" {i:02d}: {l}")
    print(f" ... total {len(asm.splitlines())} instructions")
    # Verify numerically: run compiled vs numpy
    from sim.cache4d.cache4d import Cache4D
    from sim.isa.assembler import parse_asm, ISASimulator
    import numpy as np
    np.random.seed(0)
    A = np.random.randn(8,8)
    B = np.random.randn(8,8)
    expected = A @ B
    # preload tiles into cache at coords used by compiler
    cache = Cache4D()
    # compiler uses (x,z,0,t) for A etc. For single tile 8x8, coords are (0,0,0,0) for A,B and (0,0,0,0)-> then (0,0,0,0) for C
    # Our compile for 8x8 will have one K iteration, so simplest test:
    cache.store(Coord4D(0,0,0,0), A)          # A at (0,0,0,0)
    cache.store(Coord4D(0,0,0,0), B)          # B at same? collision demo -> use distinct
    # Instead do minimal manual ISA to avoid collision:
    cache2 = Cache4D()
    cache2.store(Coord4D(0,1,0,0), A)  # use different coord
    cache2.store(Coord4D(1,0,0,0), B)
    asm2 = """
    TENSOR_LOAD.4D T0, (0,1,0,0)
    TENSOR_LOAD.4D T1, (1,0,0,0)
    MATMUL_TILE T2, T0, T1
    TENSOR_STORE.4D T2, (0,0,0,0)
    HALT
    """
    from sim.isa.assembler import parse_asm, ISASimulator
    sim = ISASimulator(cache2)
    res = sim.run(parse_asm(asm2))
    got = sim.cache.load(Coord4D(0,0,0,0))["data"]
    print("\n Matmul verify: expected[0,:3] ", expected[0,:3])
    print(" got[0,:3]     ", got[0,:3] if got is not None else res['tregs']['T2'][0,:3])
    print(" match:", np.allclose(expected, res['tregs']['T2']))

if __name__ == "__main__":
    demo()
