"""
Cocotb for sram_4k.sv — 4KB 1024×32
"""
import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

import sys
sys.path.insert(0, "/home/ubuntu/gpu_chip")
from sim.sram.sram_model import SRAM4K

@cocotb.test()
async def test_write_read(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.cen.value = 1
    dut.wen.value = 0
    dut.addr.value = 0
    dut.wdata.value = 0
    await ClockCycles(dut.clk, 2)
    # write
    dut.addr.value = 5
    dut.wdata.value = 0xDEADBEEF
    dut.wen.value = 1
    await RisingEdge(dut.clk)
    dut.wen.value = 0
    await RisingEdge(dut.clk)
    # read same
    dut.addr.value = 5
    await RisingEdge(dut.clk)
    assert int(dut.rdata.value) == 0xDEADBEEF, f"got {hex(int(dut.rdata.value))}"

@cocotb.test()
async def test_random_100(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    golden = SRAM4K()
    dut.cen.value = 1
    dut.wen.value = 0
    await ClockCycles(dut.clk, 1)
    random.seed(1)
    vals = {}
    for i in range(100):
        addr = random.randint(0, 1023)
        data = random.getrandbits(32)
        dut.addr.value = addr
        dut.wdata.value = data
        dut.wen.value = 1
        golden.write(addr, data)
        await RisingEdge(dut.clk)
        vals[addr] = data
    dut.wen.value = 0
    await RisingEdge(dut.clk)
    for addr, data in random.sample(list(vals.items()), 20):
        dut.addr.value = addr
        await RisingEdge(dut.clk)
        got = int(dut.rdata.value)
        exp = golden.read(addr)
        assert got == exp, f"addr {addr} got {hex(got)} exp {hex(exp)}"

@cocotb.test()
async def test_burst(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.cen.value = 1
    for addr in range(10):
        dut.addr.value = addr
        dut.wdata.value = addr * 0x11111111
        dut.wen.value = 1
        await RisingEdge(dut.clk)
    dut.wen.value = 0
    for addr in range(10):
        dut.addr.value = addr
        await RisingEdge(dut.clk)
        assert int(dut.rdata.value) == (addr * 0x11111111) & 0xFFFFFFFF
