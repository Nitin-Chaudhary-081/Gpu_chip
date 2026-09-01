"""
Cocotb for warp_scheduler — GTO
"""
import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

@cocotb.test()
async def test_greedy(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst_n.value = 0
    dut.warp_ready.value = 0
    dut.warp_valid.value = 0
    await ClockCycles(dut.clk, 2)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    # allocate warps 0 and 1, both ready
    dut.warp_valid.value = 0b11
    dut.warp_ready.value = 0b11
    await RisingEdge(dut.clk)
    # greedy should keep issuing last issued (0 initially) if still ready
    # first issue should be 0 (oldest, age 0 tie -> 0)
    assert int(dut.warp_id.value) == 0
    assert int(dut.issue_valid.value) == 1
    await RisingEdge(dut.clk)
    # still greedy 0
    assert int(dut.warp_id.value) == 0
    # make 0 not ready, should switch to 1 (GTO)
    dut.warp_ready.value = 0b10
    await RisingEdge(dut.clk)
    assert int(dut.warp_id.value) == 1
    # make 0 ready again with older age, should stay with 1 greedy until 1 not ready? Actually GTO oldest would be 0 after aging
    # Keep 1 ready, 0 ready, last issued is 1, greedy keeps 1
    dut.warp_ready.value = 0b11
    await RisingEdge(dut.clk)
    assert int(dut.warp_id.value) == 1

@cocotb.test()
async def test_oldest(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst_n.value = 0
    dut.warp_ready.value = 0
    dut.warp_valid.value = 0b1111
    await ClockCycles(dut.clk, 2)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    # only warp 2 ready -> should issue 2
    dut.warp_ready.value = 0b0100
    await RisingEdge(dut.clk)
    assert int(dut.warp_id.value) == 2
    # now 1 and 2 ready, last issued 2 still ready -> greedy stays 2
    dut.warp_ready.value = 0b0110
    await RisingEdge(dut.clk)
    assert int(dut.warp_id.value) == 2
    # make 2 not ready, should pick oldest among 1
    dut.warp_ready.value = 0b0010
    await RisingEdge(dut.clk)
    assert int(dut.warp_id.value) == 1

@cocotb.test()
async def test_no_ready(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst_n.value = 0
    dut.warp_ready.value = 0
    dut.warp_valid.value = 0b1111
    await ClockCycles(dut.clk, 2)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    dut.warp_ready.value = 0
    await RisingEdge(dut.clk)
    assert int(dut.issue_valid.value) == 0
    assert int(dut.warp_issue.value) == 0

@cocotb.test()
async def test_random(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.rst_n.value = 0
    dut.warp_valid.value = 0xFF
    await ClockCycles(dut.clk, 2)
    dut.rst_n.value = 1
    random.seed(0)
    for _ in range(50):
        ready = random.getrandbits(8) & 0xFF
        dut.warp_ready.value = ready
        await RisingEdge(dut.clk)
        issue = int(dut.warp_issue.value)
        valid = int(dut.issue_valid.value)
        if ready == 0:
            assert valid == 0 and issue == 0
        else:
            assert valid == 1
            # one-hot check
            assert bin(issue).count('1') == 1
            # issued warp must be ready
            wid = int(dut.warp_id.value)
            assert (ready >> wid) & 1 == 1
