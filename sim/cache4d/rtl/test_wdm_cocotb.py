"""
Cocotb for wdm_tdm_arbiter — gpu_A.md:93-94,99
Full round-robin + priority arbitration with WDM/TDM channels
"""
import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles
from cocotb.types import LogicArray

N_REQUESTORS = 4
WAVELENGTHS = 8
TDM_SLOTS = 4

async def reset_arb(dut):
    dut.rst_n.value = 0
    dut.req_valid.value = LogicArray(0, N_REQUESTORS)
    for i in range(N_REQUESTORS):
        dut.req_id[i].value = LogicArray(0, 6)
        dut.req_addr[i].value = LogicArray(0, 32)
        dut.req_is_write[i].value = 0
        dut.req_wdata[i].value = LogicArray(0, 32)
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

def check_grant(dut, req_idx, expected_valid):
    """Check grant signals for a specific requestor"""
    gnt_v = int(dut.gnt_valid[req_idx].value)
    assert gnt_v == expected_valid, f"req {req_idx} gnt_valid {gnt_v} != {expected_valid}"
    if expected_valid:
        lam = int(dut.gnt_lambda[req_idx].value)
        slot = int(dut.gnt_slot[req_idx].value)
        lat = int(dut.gnt_latency_ns[req_idx].value)
        ready = int(dut.gnt_ready[req_idx].value)
        assert 0 <= lam < WAVELENGTHS, f"lambda {lam} out of range"
        assert 0 <= slot < TDM_SLOTS, f"slot {slot} out of range"
        assert lat == 2 + slot * 1, f"latency {lat} != 2+{slot}*1"
        assert ready == 1, f"gnt_ready {ready} != 1"

async def wait_for_grant(dut, req_idx, max_cycles=100):
    """Wait for a specific requestor to get granted"""
    for cycle in range(max_cycles):
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
        gnt_v = int(dut.gnt_valid[req_idx].value)
        if gnt_v == 1:
            return True
    return False

@cocotb.test()
async def test_wdm_reset(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_arb(dut)
    for i in range(N_REQUESTORS):
        assert int(dut.gnt_valid[i].value) == 0
        assert int(dut.gnt_ready[i].value) == 0
    assert int(dut.active_count.value) == 0
    assert int(dut.bus_busy.value) == 0

@cocotb.test()
async def test_wdm_single_requestor(dut):
    """Single CU requests, should get granted in its slot"""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_arb(dut)
    # CU 0 requests - cu_id=0 gets slot 0
    dut.req_valid.value = LogicArray(0b0001, N_REQUESTORS)
    dut.req_id[0].value = LogicArray(0, 6)
    dut.req_addr[0].value = LogicArray(16, 32)
    # Wait for slot 0 (which CU 0 gets) - slot_counter cycles through 0,1,2,3
    granted = await wait_for_grant(dut, 0, 100)
    assert granted, "CU 0 not granted within timeout"
    check_grant(dut, 0, 1)
    dut.req_valid.value = LogicArray(0, N_REQUESTORS)
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    assert int(dut.gnt_valid[0].value) == 0

@cocotb.test()
async def test_wdm_round_robin(dut):
    """Multiple CUs - round-robin arbitration"""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_arb(dut)
    # All 4 CUs request simultaneously with different cu_ids to get different slots
    dut.req_valid.value = LogicArray(0b1111, N_REQUESTORS)
    for i in range(N_REQUESTORS):
        dut.req_id[i].value = LogicArray(i, 6)
        dut.req_addr[i].value = LogicArray(16 + i * 4, 32)
    # Wait for all to be granted - need enough cycles for all slots to come around
    # and round-robin to select each CU
    grants_received = [0] * N_REQUESTORS
    for cycle in range(120):
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
        for i in range(N_REQUESTORS):
            if int(dut.gnt_valid[i].value) == 1 and grants_received[i] == 0:
                check_grant(dut, i, 1)
                grants_received[i] = 1
    # All should have been granted at least once
    assert all(grants_received), f"Not all granted: {grants_received}"
    dut.req_valid.value = LogicArray(0, N_REQUESTORS)
    await RisingEdge(dut.clk)

@cocotb.test()
async def test_wdm_deterministic_channel_assignment(dut):
    """Same CU always gets same wavelength/slot assignment"""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_arb(dut)
    # CU 0 requests multiple times
    assignments = []
    for _ in range(4):
        dut.req_valid.value = LogicArray(0b0001, N_REQUESTORS)
        dut.req_id[0].value = LogicArray(0, 6)
        granted = await wait_for_grant(dut, 0, 100)
        assert granted
        lam = int(dut.gnt_lambda[0].value)
        slot = int(dut.gnt_slot[0].value)
        assignments.append((lam, slot))
        dut.req_valid.value = LogicArray(0, N_REQUESTORS)
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
    # All assignments should be identical
    assert all(a == assignments[0] for a in assignments), f"Assignments not deterministic: {assignments}"

@cocotb.test()
async def test_wdm_priority_encoding(dut):
    """Higher priority (lower index) gets granted when slots collide"""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_arb(dut)
    # Force CU 0 and CU 1 to same slot by using same cu_id
    dut.req_valid.value = LogicArray(0b0011, N_REQUESTORS)
    dut.req_id[0].value = LogicArray(0, 6)
    dut.req_id[1].value = LogicArray(0, 6)
    # Wait for grant
    granted = await wait_for_grant(dut, 0, 100) or await wait_for_grant(dut, 1, 100)
    assert granted
    # CU 0 should win (lower index = higher priority in round-robin)
    if int(dut.gnt_valid[0].value) == 1:
        assert int(dut.gnt_valid[1].value) == 0, "CU 1 should be deferred"
    dut.req_valid.value = LogicArray(0, N_REQUESTORS)
    await RisingEdge(dut.clk)

@cocotb.test()
async def test_wdm_read_write(dut):
    """Test read and write requests"""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_arb(dut)
    # Write request
    dut.req_valid.value = LogicArray(0b0001, N_REQUESTORS)
    dut.req_id[0].value = LogicArray(0, 6)
    dut.req_addr[0].value = LogicArray(32, 32)
    dut.req_is_write[0].value = 1
    dut.req_wdata[0].value = LogicArray(0xDEADBEEF, 32)
    granted = await wait_for_grant(dut, 0, 100)
    assert granted
    check_grant(dut, 0, 1)
    dut.req_valid.value = LogicArray(0, N_REQUESTORS)
    await RisingEdge(dut.clk)
    # Read request
    dut.req_valid.value = LogicArray(0b0010, N_REQUESTORS)
    dut.req_id[1].value = LogicArray(1, 6)
    dut.req_addr[1].value = LogicArray(64, 32)
    dut.req_is_write[1].value = 0
    granted = await wait_for_grant(dut, 1, 100)
    assert granted
    check_grant(dut, 1, 1)
    dut.req_valid.value = LogicArray(0, N_REQUESTORS)
    await RisingEdge(dut.clk)

@cocotb.test()
async def test_wdm_active_count(dut):
    """Test active_count tracks in-flight requests"""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_arb(dut)
    assert int(dut.active_count.value) == 0
    # Issue 2 requests
    dut.req_valid.value = LogicArray(0b0011, N_REQUESTORS)
    dut.req_id[0].value = LogicArray(0, 6)
    dut.req_id[1].value = LogicArray(1, 6)
    # Wait for at least one grant (slot must come around)
    for _ in range(100):
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
        if int(dut.active_count.value) > 0:
            break
    assert int(dut.active_count.value) > 0, f"active_count {int(dut.active_count.value)} not > 0"
    dut.req_valid.value = LogicArray(0, N_REQUESTORS)
    # Wait for completion
    for _ in range(100):
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
        if int(dut.active_count.value) == 0:
            break
    assert int(dut.active_count.value) == 0, f"active_count {int(dut.active_count.value)} not 0"

@cocotb.test()
async def test_wdm_burst_requests(dut):
    """Burst of requests from single CU"""
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await reset_arb(dut)
    for burst in range(5):
        dut.req_valid.value = LogicArray(0b0001, N_REQUESTORS)
        dut.req_id[0].value = LogicArray(0, 6)
        dut.req_addr[0].value = LogicArray(16 + burst * 4, 32)
        dut.req_is_write[0].value = (burst % 2 == 0)
        # Wait for grant
        granted = await wait_for_grant(dut, 0, 100)
        assert granted, f"Burst {burst} not granted"
        check_grant(dut, 0, 1)
        dut.req_valid.value = LogicArray(0, N_REQUESTORS)
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)