"""
Track 3 — Co-Sim wrapper (no RTL needed)  gpu_2.md:8
Feeds compiler_pass.py:compile_matmul  -> assembler ISASimulator -> Cache4D
Proves compiler->hardware loop is correct before cocotb RTL.
Runs via pytest (no icarus), same logic as cocotb test_cosim_matmul.py.
"""
import numpy as np
import pytest
from sim.cache4d.cache4d import Cache4D, Coord4D
from sim.isa.compiler_pass import compile_matmul, compile_conv2d
from sim.isa.assembler import parse_asm, ISASimulator, parse_coord


def check_matmul_via_isa(M, N, K, tile=8):
    asm = compile_matmul(M, N, K, tile=tile)
    prog = parse_asm(asm)
    # ISA golden should parse without error
    assert any(i.op == "MATMUL_TILE" for i in prog), "no MATMUL_TILE emitted"
    assert prog[-1].op == "HALT"
    # Verify each memory op's cycles match Cache4D golden
    golden = Cache4D()
    for instr in prog:
        if instr.op in ("TENSOR_LOAD.4D", "TENSOR_STORE.4D"):
            coord = parse_coord(instr.args[1])
            expected = golden.physical_location(coord)["cycles"]
            # also show slot/lambda derivation gpu.md:16
            lam = coord.t % 8
            slot = (coord.z + coord.t) % 4
            cycles = 4 + slot * 2
            assert expected == cycles, f"golden cycles {expected} != spec {cycles} for {coord}"
            assert golden.physical_location(coord)["lambda"] == lam
            assert golden.physical_location(coord)["slot"] == slot

def test_cosim_wrapper_matmul_8():
    """8x8 tiled 8 — minimal path, also tests ISA simulator correctness."""
    # Drive ISA simulator with random data and check numeric result
    np.random.seed(0)
    A = np.random.randn(8, 8)
    B = np.random.randn(8, 8)
    expected = A @ B

    cache = Cache4D()
    # distinct coords to avoid alias as in compiler_pass demo
    cache.store(Coord4D(0, 1, 0, 0), A)
    cache.store(Coord4D(1, 0, 0, 0), B)

    asm = """
    TENSOR_LOAD.4D T0, (0,1,0,0)
    TENSOR_LOAD.4D T1, (1,0,0,0)
    MATMUL_TILE T2, T0, T1
    TENSOR_STORE.4D T2, (0,0,0,0)
    HALT
    """
    sim = ISASimulator(cache)
    res = sim.run(parse_asm(asm))
    got = sim.cache.load(Coord4D(0, 0, 0, 0))["data"]
    assert got is not None
    assert np.allclose(got, expected, atol=1e-6)
    # determinism: same coords same cycles
    check_matmul_via_isa(8, 8, 8, tile=8)

def test_cosim_wrapper_matmul_16():
    check_matmul_via_isa(16, 16, 16, tile=8)

def test_cosim_wrapper_matmul_32():
    check_matmul_via_isa(32, 32, 32, tile=8)

def test_cosim_wrapper_conv():
    asm = compile_conv2d(16, 16, 8, 8, tile=8)
    prog = parse_asm(asm)
    assert any(i.op == "CONV_TILE" for i in prog)
    assert prog[-1].op == "HALT"
    # every coords cycles bounded [4,10]
    golden = Cache4D()
    for instr in prog:
        if instr.op in ("TENSOR_LOAD.4D", "TENSOR_STORE.4D"):
            coord = parse_coord(instr.args[1])
            c = golden.physical_location(coord)["cycles"]
            assert 4 <= c <= 10

def test_cosim_wrapper_cycle_rollup():
    """End-to-end cycle rollup vs RTL spec: sum per-op cycles equals ISA total."""
    # Use ISA simulator's cycle counting as golden for RTL to match
    cache = Cache4D()
    asm = compile_matmul(16, 16, 16, tile=8)
    prog = parse_asm(asm)
    sim = ISASimulator(cache)
    res = sim.run(prog)
    # Recompute expected from per-op specs
    recomputed = 0
    tmp_cache = Cache4D()
    for instr in prog:
        if instr.op in ("TENSOR_LOAD.4D", "TENSOR_STORE.4D"):
            coord = parse_coord(instr.args[1])
            recomputed += tmp_cache.physical_location(coord)["cycles"]
            # do dummy store/load to keep cache parity
            tmp_cache.store(coord, np.zeros((8, 8)))
        elif instr.op == "MATMUL_TILE":
            recomputed += 8
        elif instr.op == "WDM_XFER":
            recomputed += 2
        elif instr.op == "TDM_WAIT":
            slot = int(instr.args[0].replace("#", "")) if instr.args else 1
            recomputed += slot * 2
        elif instr.op == "CACHE_MAP":
            recomputed += 1
        elif instr.op == "HALT":
            pass
    assert res["cycles"] == recomputed, f"ISA cycles {res['cycles']} != recomputed {recomputed}"
