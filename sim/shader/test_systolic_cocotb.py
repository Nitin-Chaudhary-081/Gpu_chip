"""
Cocotb for systolic_4x4 — 4x4 GEMM vs numpy
gpu_A.md:39-40,130
"""
import random
import numpy as np
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

import sys
sys.path.insert(0, "/home/ubuntu/gpu_chip")
from sim.shader.systolic_golden import systolic_4x4_golden, pack_a_b, unpack_c

SIZE=4

def pack_vec_bytes(arr):
    # arr 4x4 int8 -> 128-bit int
    flat = np.array(arr, dtype=np.int8).reshape(16)
    v=0
    for i, b in enumerate(flat):
        v |= (int(b) & 0xFF) << (i*8)
    return v

def pack_vec_c(arr):
    # not needed
    pass

async def reset(dut):
    dut.rst_n.value=0
    dut.start.value=0
    dut.a_flat.value=0
    dut.b_flat.value=0
    await ClockCycles(dut.clk,3)
    dut.rst_n.value=1
    await RisingEdge(dut.clk)

async def drive_gemm(dut, A, B):
    a_flat = pack_vec_bytes(A)
    b_flat = pack_vec_bytes(B)
    dut.a_flat.value = a_flat
    dut.b_flat.value = b_flat
    dut.start.value=1
    await RisingEdge(dut.clk)
    dut.start.value=0
    # busy should assert
    await RisingEdge(dut.clk)
    assert int(dut.busy.value)==1, f"busy {int(dut.busy.value)}"
    # wait LATENCY-1 more cycles
    for _ in range(3):
        await RisingEdge(dut.clk)
    # done pulse
    await RisingEdge(dut.clk)
    # need to check done is 1 at this cycle? Our design: done 1 after LATENCY cycles from start, held 1 cycle.
    # We started busy at start, cnt=LATENCY, after 4 cycles done.
    # The above waited 1 (busy check) +3 +1 =5 cycles? Let's just poll
    # Simpler: wait until done
    for _ in range(10):
        if int(dut.done.value)==1:
            break
        await RisingEdge(dut.clk)
    assert int(dut.done.value)==1, "done not asserted"
    c_flat = int(dut.c_flat.value)
    C = unpack_c(c_flat)
    exp = systolic_4x4_golden(A,B)
    # compare
    for i in range(4):
        for j in range(4):
            assert C[i,j]==exp[i,j], f"C[{i}][{j}] {C[i,j]} != exp {exp[i,j]} A*B\nA={A}\nB={B}\nC={C}\nexp={exp}"
    await RisingEdge(dut.clk)
    assert int(dut.busy.value)==0

@cocotb.test()
async def test_reset(dut):
    cocotb.start_soon(Clock(dut.clk,10,unit="ns").start())
    await reset(dut)
    assert int(dut.busy.value)==0
    assert int(dut.done.value)==0

@cocotb.test()
async def test_identity(dut):
    cocotb.start_soon(Clock(dut.clk,10,unit="ns").start())
    await reset(dut)
    A = np.array([[1,2,3,4],[5,6,7,8],[9,10,11,12],[13,14,15,16]], dtype=np.int8)
    B = np.eye(4, dtype=np.int8)
    await drive_gemm(dut, A, B)
    # A*I = A
    # second: all 2* all 3 -> 24
    A2 = np.full((4,4),2, dtype=np.int8)
    B2 = np.full((4,4),3, dtype=np.int8)
    await drive_gemm(dut, A2,B2)

@cocotb.test()
async def test_random_20(dut):
    cocotb.start_soon(Clock(dut.clk,10,unit="ns").start())
    await reset(dut)
    random.seed(0)
    np.random.seed(0)
    for n in range(20):
        A = np.random.randint(-8,8,size=(4,4),dtype=np.int8)
        B = np.random.randint(-8,8,size=(4,4),dtype=np.int8)
        await drive_gemm(dut, A,B)

@cocotb.test()
async def test_simple_matmul(dut):
    cocotb.start_soon(Clock(dut.clk,10,unit="ns").start())
    await reset(dut)
    # Example from workloads: 2x2 inside 4x4
    A = np.zeros((4,4),dtype=np.int8)
    B = np.zeros((4,4),dtype=np.int8)
    A[0,0]=1; A[0,1]=2; A[1,0]=3; A[1,1]=4
    B[0,0]=5; B[0,1]=6; B[1,0]=7; B[1,1]=8
    # Expected [[19,22],[43,50]] in top-left
    await drive_gemm(dut, A,B)

@cocotb.test()
async def test_simple_init(dut):
    # For systolic_4x4_simple drop-in dummy replacement
    pass
