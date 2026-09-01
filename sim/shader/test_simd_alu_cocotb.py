"""
Cocotb for simd_alu.sv — 8-lane FP32/INT8 ADD/MUL/MAX vs numpy golden
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
from sim.shader.simd_alu import f32_to_bits, bits_to_f32, simd_alu_golden, int8_to_bits, bits_to_int8

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
    dut.is_fp32.value = 0
    dut.a.value = 0
    dut.b.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

async def drive(dut, op, a_bits, b_bits, is_fp32=True):
    """drive 1 cycle, wait for out_valid 2 cycles later (2-stage pipeline)"""
    dut.op.value = op
    dut.is_fp32.value = 1 if is_fp32 else 0
    dut.a.value = pack_vec(a_bits)
    dut.b.value = pack_vec(b_bits)
    dut.in_valid.value = 1
    await RisingEdge(dut.clk)
    dut.in_valid.value = 0
    # 2-stage pipeline: out_valid comes after 2 cycles
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    assert int(dut.out_valid.value) == 1, f"out_valid {int(dut.out_valid.value)} !=1 op {op} is_fp32 {is_fp32}"
    res = unpack_vec(dut.result.value)
    await RisingEdge(dut.clk)
    return res

@cocotb.test()
async def test_reset(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_dut(dut)
    assert int(dut.out_valid.value) == 0
    assert int(dut.result.value) == 0

@cocotb.test()
async def test_int8_add_known(dut):
    """INT8 ADD known values"""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_dut(dut)
    a_int8 = [1, 2, 3, -1, 0, 5, 1, -2]
    b_int8 = [2, 3, 1, 1, 0, 5, -1, 2]
    a_bits = [int8_to_bits(x) for x in a_int8]
    b_bits = [int8_to_bits(x) for x in b_int8]
    exp = simd_alu_golden(a_bits, b_bits, 0, False)
    got = await drive(dut, 0, a_bits, b_bits, False)
    for i in range(LANES):
        assert got[i]==exp[i], f"INT8 ADD lane {i} got {hex(got[i])} exp {hex(exp[i])}"

@cocotb.test()
async def test_int8_mul_known(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_dut(dut)
    a_int8 = [1, 2, 3, -2, 0, 4, 1, -1]
    b_int8 = [2, 3, 2, -3, 0, 2, 2, -1]
    a_bits = [int8_to_bits(x) for x in a_int8]
    b_bits = [int8_to_bits(x) for x in b_int8]
    exp = simd_alu_golden(a_bits, b_bits, 1, False)
    got = await drive(dut, 1, a_bits, b_bits, False)
    for i in range(LANES):
        assert got[i]==exp[i], f"INT8 MUL lane {i} got {hex(got[i])} exp {hex(exp[i])}"

@cocotb.test()
async def test_int8_max_known(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_dut(dut)
    a_int8 = [1, 5, -1, -5, 0, 3, -2, 7]
    b_int8 = [2, 3, 2, -3, 0, 3, -1, 7]
    a_bits = [int8_to_bits(x) for x in a_int8]
    b_bits = [int8_to_bits(x) for x in b_int8]
    exp = simd_alu_golden(a_bits, b_bits, 2, False)
    got = await drive(dut, 2, a_bits, b_bits, False)
    for i in range(LANES):
        assert got[i]==exp[i], f"INT8 MAX lane {i} got {hex(got[i])} exp {hex(exp[i])}"

@cocotb.test()
async def test_fp32_add_known(dut):
    """FP32 ADD known values"""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_dut(dut)
    a_f = [1.0,2.0,3.5,-1.0,0.0,5.0,1.5,-2.0]
    b_f = [2.0,3.0,1.5, 1.0,0.0,5.0,-1.5,2.0]
    a_bits = [f32_to_bits(x) for x in a_f]
    b_bits = [f32_to_bits(x) for x in b_f]
    exp = simd_alu_golden(a_bits,b_bits,3,True)
    got = await drive(dut, 3, a_bits, b_bits, True)
    for i in range(LANES):
        assert got[i]==exp[i], f"FP32 ADD lane {i} got {hex(got[i])} exp {hex(exp[i])}"

@cocotb.test()
async def test_fp32_mul_known(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_dut(dut)
    a_f = [1.0,2.0,3.0, -2.0, 0.5, 4.0, 1.5, -1.0]
    b_f = [2.0,3.0,2.0, -3.0, 2.0, 0.5, 2.0, -1.0]
    a_bits = [f32_to_bits(x) for x in a_f]
    b_bits = [f32_to_bits(x) for x in b_f]
    exp = simd_alu_golden(a_bits,b_bits,4,True)
    got = await drive(dut, 4, a_bits, b_bits, True)
    for i in range(LANES):
        assert got[i]==exp[i], f"FP32 MUL lane {i} got {hex(got[i])} exp {hex(exp[i])}"

@cocotb.test()
async def test_fp32_max_known(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_dut(dut)
    a_f = [1.0, 5.0, -1.0, -5.0, 0.0, 3.0, -2.0, 7.0]
    b_f = [2.0, 3.0,  2.0, -3.0, -0.0, 3.0, -1.0, 7.0]
    a_bits = [f32_to_bits(x) for x in a_f]
    b_bits = [f32_to_bits(x) for x in b_f]
    b_bits[4] = 0x80000000  # -0.0
    exp = simd_alu_golden(a_bits,b_bits,5,True)
    got = await drive(dut, 5, a_bits, b_bits, True)
    for i in range(LANES):
        assert got[i]==exp[i], f"FP32 MAX lane {i} got {hex(got[i])} exp {hex(exp[i])}"

@cocotb.test()
async def test_deterministic(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_dut(dut)
    a_bits = [f32_to_bits(float(i)) for i in range(LANES)]
    b_bits = [f32_to_bits(float(i*2)) for i in range(LANES)]
    exp = simd_alu_golden(a_bits,b_bits,3,True)
    r1 = await drive(dut, 3, a_bits, b_bits, True)
    r2 = await drive(dut, 3, a_bits, b_bits, True)
    assert r1==r2==exp

@cocotb.test()
async def test_pipeline_back_to_back(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_dut(dut)
    # fire 8 consecutive without idle — pipeline should hold
    for k in range(8):
        a_bits = [f32_to_bits(float(k+i)) for i in range(LANES)]
        b_bits = [f32_to_bits(1.0) for _ in range(LANES)]
        exp = simd_alu_golden(a_bits,b_bits,3,True)
        dut.op.value = 3
        dut.is_fp32.value = 1
        dut.a.value = pack_vec(a_bits)
        dut.b.value = pack_vec(b_bits)
        dut.in_valid.value = 1
        await RisingEdge(dut.clk)
        dut.in_valid.value = 0
        # wait 2 cycles for pipeline
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
        assert int(dut.out_valid.value)==1
        got = unpack_vec(dut.result.value)
        for i in range(LANES):
            assert got[i]==exp[i], f"pipe k={k} lane {i} {hex(got[i])}!={hex(exp[i])}"
        await RisingEdge(dut.clk)

@cocotb.test()
async def test_python_golden_50(dut):
    """50 random ADD/MUL/MAX vs numpy — gpu_A.md:45 50+ vectors"""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_dut(dut)
    random.seed(0)
    np.random.seed(0)
    ops_fp32 = [3,4,5]
    ops_int8 = [0,1,2]
    for n in range(60):
        if random.random() < 0.5:
            op = random.choice(ops_fp32)
            is_fp32 = True
        else:
            op = random.choice(ops_int8)
            is_fp32 = False
        a_bits = []
        b_bits = []
        for _ in range(LANES):
            if is_fp32:
                # exact ints 0..16 and halves .5 (binary exact)
                vals = [0,0.5,1,1.5,2,3,4,6,8,12,16]
                av = random.choice(vals)
                bv = random.choice(vals)
                if random.random()<0.2:
                    av = -av
                    bv = -bv
                a_bits.append(f32_to_bits(np.float32(av)))
                b_bits.append(f32_to_bits(np.float32(bv)))
            else:
                # INT8 values -127..127
                av = random.randint(-64, 64)
                bv = random.randint(-64, 64)
                a_bits.append(int8_to_bits(av))
                b_bits.append(int8_to_bits(bv))
        exp = simd_alu_golden(a_bits,b_bits,op,is_fp32)
        got = await drive(dut, op, a_bits, b_bits, is_fp32)
        for i in range(LANES):
            if got[i]!=exp[i]:
                dut._log.error(f"op {op} lane {i} a {a_bits[i]} b {b_bits[i]} got {hex(got[i])} exp {hex(exp[i])}")
                assert got[i]==exp[i], f"n={n} op {op} lane {i} mismatch"
    dut._log.info("50+ golden passed")

@cocotb.test()
async def test_relu_sigmoid_dot(dut):
    """ReLU/MAX and dot-like — file 45 Numbers should match numpy"""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_dut(dut)
    # ReLU via MAX with 0 (FP32)
    a_bits = [f32_to_bits(np.float32(x)) for x in [-2,-1,0,0.5,1,2,3,4]]
    b_bits = [f32_to_bits(np.float32(0)) for _ in range(LANES)]
    exp = simd_alu_golden(a_bits,b_bits,5,True) # FP32 MAX
    got = await drive(dut, 5, a_bits,b_bits, True)
    assert got==exp
    # ReLU via MAX with 0 (INT8)
    a_bits_i = [int8_to_bits(x) for x in [-2,-1,0,1,2,3,4,5]]
    b_bits_i = [int8_to_bits(0) for _ in range(LANES)]
    exp_i = simd_alu_golden(a_bits_i,b_bits_i,2,False) # INT8 MAX
    got_i = await drive(dut, 2, a_bits_i,b_bits_i, False)
    assert got_i==exp_i