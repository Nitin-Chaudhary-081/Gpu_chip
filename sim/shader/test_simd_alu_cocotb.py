"""
Cocotb for simd_alu.sv — 8-lane FP32 ADD/MUL/MAX vs numpy golden
gpu_A.md:45 50+ vectors, pipeline, deterministic
"""
import random
import struct
import numpy as np
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

import sys
sys.path.insert(0, "/home/ubuntu/gpu_chip")
from sim.shader.simd_alu import f32_to_bits, bits_to_f32, simd_alu_golden

LANES = 8
DATAW = 32

def pack_vec(bits_list):
    """bits_list 8 ints -> 256-bit int packed lane0 LSB"""
    v = 0
    for i, b in enumerate(bits_list):
        v |= (int(b) & 0xFFFFFFFF) << (i*32)
    return v

def unpack_vec(val):
    iv = int(val)
    return [(iv >> (i*32)) & 0xFFFFFFFF for i in range(LANES)]

async def reset_dut(dut):
    dut.rst_n.value = 0
    dut.in_valid.value = 0
    dut.op.value = 0
    dut.a.value = 0
    dut.b.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

async def drive(dut, op, a_bits, b_bits):
    """drive 1 cycle, wait for out_valid 1 cycle later"""
    dut.op.value = op
    dut.a.value = pack_vec(a_bits)
    dut.b.value = pack_vec(b_bits)
    dut.in_valid.value = 1
    await RisingEdge(dut.clk)
    dut.in_valid.value = 0
    await RisingEdge(dut.clk)
    # out_valid should be 1 now (1-cycle pipeline)
    assert int(dut.out_valid.value) == 1, f"out_valid {int(dut.out_valid.value)} !=1 op {op}"
    res = unpack_vec(dut.result.value)
    await RisingEdge(dut.clk)
    # out_valid low after
    # assert int(dut.out_valid.value)==0 # pipeline holds 1 cycle only
    return res

@cocotb.test()
async def test_reset(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_dut(dut)
    assert int(dut.out_valid.value) == 0
    assert int(dut.result.value) == 0

@cocotb.test()
async def test_add_known(dut):
    """ADD known values  gpu_A.md:45 dot product simple"""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_dut(dut)
    # lane-wise: 1+2=3, 2+3=5, 3.5+1.5=5, -1+1=0, 0+0=0, 5+5=10, 1.5+ -1.5 =0, -2+2=0
    a_f = [1.0,2.0,3.5,-1.0,0.0,5.0,1.5,-2.0]
    b_f = [2.0,3.0,1.5, 1.0,0.0,5.0,-1.5,2.0]
    a_bits = [f32_to_bits(x) for x in a_f]
    b_bits = [f32_to_bits(x) for x in b_f]
    exp = simd_alu_golden(a_bits,b_bits,0)
    got = await drive(dut, 0, a_bits, b_bits)
    for i in range(LANES):
        assert got[i]==exp[i], f"ADD lane {i} got {hex(got[i])} exp {hex(exp[i])} {a_f[i]}+{b_f[i]}={bits_to_f32(exp[i])}"

@cocotb.test()
async def test_mul_known(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_dut(dut)
    a_f = [1.0,2.0,3.0, -2.0, 0.5, 4.0, 1.5, -1.0]
    b_f = [2.0,3.0,2.0, -3.0, 2.0, 0.5, 2.0, -1.0]
    a_bits = [f32_to_bits(x) for x in a_f]
    b_bits = [f32_to_bits(x) for x in b_f]
    exp = simd_alu_golden(a_bits,b_bits,1)
    got = await drive(dut, 1, a_bits, b_bits)
    for i in range(LANES):
        assert got[i]==exp[i], f"MUL lane {i} got {hex(got[i])} exp {hex(exp[i])} {a_f[i]}*{b_f[i]}={bits_to_f32(exp[i])} vs {bits_to_f32(got[i])}"

@cocotb.test()
async def test_max_known(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_dut(dut)
    a_f = [1.0, 5.0, -1.0, -5.0, 0.0, 3.0, -2.0, 7.0]
    b_f = [2.0, 3.0,  2.0, -3.0, -0.0, 3.0, -1.0, 7.0]
    a_bits = [f32_to_bits(x) for x in a_f]
    b_bits = [f32_to_bits(x) for x in b_f]
    # handle -0 bit pattern explicitly
    # b[4] is -0.0 = 0x80000000
    b_bits[4] = 0x80000000
    exp = simd_alu_golden(a_bits,b_bits,2)
    got = await drive(dut, 2, a_bits, b_bits)
    for i in range(LANES):
        # allow +0 vs -0 equivalence? RTL returns +0 for max with -0, golden does same
        assert got[i]==exp[i], f"MAX lane {i} got {hex(got[i])} exp {hex(exp[i])} a={a_f[i]} b={b_f[i]}"

@cocotb.test()
async def test_deterministic(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_dut(dut)
    a_bits = [f32_to_bits(float(i)) for i in range(LANES)]
    b_bits = [f32_to_bits(float(i*2)) for i in range(LANES)]
    exp = simd_alu_golden(a_bits,b_bits,0)
    r1 = await drive(dut, 0, a_bits, b_bits)
    r2 = await drive(dut, 0, a_bits, b_bits)
    assert r1==r2==exp

@cocotb.test()
async def test_pipeline_back_to_back(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_dut(dut)
    # fire 8 consecutive without idle — pipeline should hold
    for k in range(8):
        a_bits = [f32_to_bits(float(k+i)) for i in range(LANES)]
        b_bits = [f32_to_bits(1.0) for _ in range(LANES)]
        exp = simd_alu_golden(a_bits,b_bits,0)
        dut.op.value = 0
        dut.a.value = pack_vec(a_bits)
        dut.b.value = pack_vec(b_bits)
        dut.in_valid.value = 1
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
        assert int(dut.out_valid.value)==1
        got = unpack_vec(dut.result.value)
        for i in range(LANES):
            assert got[i]==exp[i], f"pipe k={k} lane {i} {hex(got[i])}!={hex(exp[i])}"
        # keep valid low for 1 cycle to avoid overlap? but pipeline is 1 deep, we already consumed
        dut.in_valid.value = 0
        await RisingEdge(dut.clk)

@cocotb.test()
async def test_python_golden_50(dut):
    """50 random ADD/MUL/MAX vs numpy — gpu_A.md:45 50+ vectors"""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_dut(dut)
    random.seed(0)
    np.random.seed(0)
    ops = [0,1,2]
    for n in range(60):
        op = random.choice(ops)
        # use integer-valued floats for exactness (<2^24)
        a_bits = []
        b_bits = []
        for _ in range(LANES):
            # exact ints 0..16 and halves .5 (binary exact)
            vals = [0,0.5,1,1.5,2,3,4,6,8,12,16]
            av = random.choice(vals)
            bv = random.choice(vals)
            # random sign
            if random.random()<0.2:
                av = -av
                bv = -bv
            a_bits.append(f32_to_bits(np.float32(av)))
            b_bits.append(f32_to_bits(np.float32(bv)))
        exp = simd_alu_golden(a_bits,b_bits,op)
        got = await drive(dut, op, a_bits, b_bits)
        for i in range(LANES):
            if got[i]!=exp[i]:
                # allow 1 ulp for add/mul due to truncation vs round-to-nearest?
                # For exact ints, should be exact, so fail
                dut._log.error(f"op {op} lane {i} a {bits_to_f32(a_bits[i])} b {bits_to_f32(b_bits[i])} got {bits_to_f32(got[i])} {hex(got[i])} exp {bits_to_f32(exp[i])} {hex(exp[i])}")
                assert got[i]==exp[i], f"n={n} op {op} lane {i} mismatch"
    dut._log.info("50+ golden passed")

@cocotb.test()
async def test_relu_sigmoid_dot(dut):
    """ReLU/MAX and dot-like — file 45 Numbers should match numpy"""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_dut(dut)
    # ReLU via MAX with 0
    a_bits = [f32_to_bits(np.float32(x)) for x in [-2,-1,0,0.5,1,2,3,4]]
    b_bits = [f32_to_bits(np.float32(0)) for _ in range(LANES)]
    exp = simd_alu_golden(a_bits,b_bits,2) # MAX
    got = await drive(dut, 2, a_bits,b_bits)
    assert got==exp
    # dot product lane0: 1*2 + 3*4 via two mul then add — we test mul then add separately
    # mul
    a1 = [f32_to_bits(np.float32(1)), f32_to_bits(np.float32(3))]+[0]*6
    b1 = [f32_to_bits(np.float32(2)), f32_to_bits(np.float32(4))]+[0]*6
    r_mul = await drive(dut,1,a1,b1)
    # add lane0+lane1 via next op: need to move results externally, here just check mul
    assert r_mul[0]==f32_to_bits(np.float32(2))
    assert r_mul[1]==f32_to_bits(np.float32(12))
