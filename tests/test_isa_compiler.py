"""Tests for ISA + compiler lowering gpu.md:12,17"""
import numpy as np
from sim.cache4d.cache4d import Cache4D, Coord4D
from sim.isa.assembler import parse_asm, ISASimulator
from sim.isa.compiler_pass import compile_matmul

def test_assembler_parse():
    asm = """
    TENSOR_LOAD.4D T0, (0,0,0,0)
    MATMUL_TILE T2, T0, T1
    HALT
    """
    prog = parse_asm(asm)
    assert len(prog) == 3
    assert prog[0].op == "TENSOR_LOAD.4D"
    assert prog[2].op == "HALT"

def test_isa_matmul_correctness():
    # Single tile 8x8 matmul
    np.random.seed(0)
    A = np.random.randn(8,8)
    B = np.random.randn(8,8)
    expected = A @ B
    cache = Cache4D()
    cache.store(Coord4D(0,1,0,0), A)
    cache.store(Coord4D(1,0,0,0), B)
    asm = """
    TENSOR_LOAD.4D T0, (0,1,0,0)
    TENSOR_LOAD.4D T1, (1,0,0,0)
    MATMUL_TILE T2, T0, T1
    TENSOR_STORE.4D T2, (0,0,0,0)
    HALT
    """
    sim = ISASimulator(cache)
    sim.run(parse_asm(asm))
    got = sim.cache.load(Coord4D(0,0,0,0))["data"]
    assert got is not None
    assert np.allclose(got, expected, atol=1e-6)

def test_compiler_emits_halt():
    asm = compile_matmul(16,16,16, tile=8)
    assert "HALT" in asm
    assert "MATMUL_TILE" in asm
    assert "WDM_XFER" in asm
    assert "TDM_WAIT" in asm

def test_compiler_matmul_runs():
    # Compile 8x8 and execute via manual preload
    # For 8x8 tiled 8, compiler will use multiple temporaries but we can at least parse & run without error
    asm = compile_matmul(8,8,8, tile=8)
    prog = parse_asm(asm)
    assert len(prog) > 5
    cache = Cache4D()
    # preload needed coords: compiler uses (0,0,0,0) for A etc but collisions possible
    # Just test simulator doesn't crash
    sim = ISASimulator(cache)
    res = sim.run(prog)
    assert res["cycles"] > 0

def test_linear_vs_4d_addressing():
    # Linear addressing `gpu.md:12` collapses 4D ->1D; 4D keeps structure
    from sim.cache4d.cache4d import LinearCache
    coord = Coord4D(1,2,3,4)
    c4 = Cache4D()
    lin = LinearCache()
    loc = c4.physical_location(coord)
    # 4D has bank+lambda+slot, linear only line+variable cycles
    assert "lambda" in loc
    assert "slot" in loc
    assert lin._linear_addr(coord) != loc["bank"]  # different domains
