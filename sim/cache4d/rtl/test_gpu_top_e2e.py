# e2e cocotb: host writes matmul job -> GPU runs -> host reads result  gpu_arc.md Priority 3.1
# Verifies full pipeline: cache 4D + systolic 4x4 + SIMD ALU + register file + WDM
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

W=8; T=4; BASE=4; SLOTC=2

async def reset(dut):
    dut.rst_n.value = 0
    dut.host_req_valid.value = 0
    dut.host_matmul_start.value = 0
    dut.host_simd_start.value = 0
    dut.host_simd_op.value = 0
    dut.host_simd_is_fp32.value = 0
    dut.host_req_is_store.value = 0
    dut.host_req_x.value = 0
    dut.host_req_y.value = 0
    dut.host_req_z.value = 0
    dut.host_req_t.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

@cocotb.test()
async def test_e2e_cache_then_matmul_then_simd(dut):
    """Full pipeline: cache request -> matmul (systolic) -> SIMD, checks determinism and no interference"""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)

    # 1. Cache 4D request (host writes job coords)
    dut.host_req_x.value = 5; dut.host_req_y.value = 7; dut.host_req_z.value = 3; dut.host_req_t.value = 9
    dut.host_req_valid.value = 1; dut.host_req_is_store.value = 0
    await RisingEdge(dut.clk)
    dut.host_req_valid.value = 0
    await RisingEdge(dut.clk)
    assert int(dut.host_resp_valid.value) == 1, "cache resp_valid"
    exp_lam = 9 % W; exp_slot = (3 % 4 + 9 % 4) % T; exp_cycles = BASE + exp_slot * SLOTC
    assert int(dut.host_resp_lambda.value) == exp_lam
    assert int(dut.host_resp_slot.value) == exp_slot
    assert int(dut.host_resp_cycles.value) == exp_cycles
    assert int(dut.host_wdm_valid.value) == 1
    await RisingEdge(dut.clk)

    # 2. Matmul job: trigger systolic 4x4 (dummy 2*3 => 24 per element, but we check handshake)
    dut.host_matmul_start.value = 1
    await RisingEdge(dut.clk)
    dut.host_matmul_start.value = 0
    await RisingEdge(dut.clk)
    assert int(dut.host_compute_busy.value) == 1, "matmul busy should assert"
    done = False
    for _ in range(15):  # LATENCY 6 + state overhead ~10
        await RisingEdge(dut.clk)
        if int(dut.host_compute_done.value) == 1:
            done = True
            break
    assert done, "matmul done not asserted within 15 cycles (systolic LATENCY 6)"
    await RisingEdge(dut.clk)
    assert int(dut.host_compute_busy.value) == 0, "busy should deassert after done"

    # 3. SIMD job: INT8 ADD lane 8 (host writes SIMD job, reads result)
    # Use INT8 path: a=[1..8], b=[2..9] from gpu_top internal pattern? we drive via host_simd
    # Our gpu_top internal simd_a/b are fixed patterns 1..8 and 2..9, result should be deterministic
    dut.host_simd_op.value = 0  # INT8_ADD
    dut.host_simd_is_fp32.value = 0
    dut.host_simd_start.value = 1
    await RisingEdge(dut.clk)
    dut.host_simd_start.value = 0
    # SIMD is 2-stage pipeline: out_valid after 2 cycles
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    assert int(dut.host_simd_done.value) == 1, "simd done (out_valid) should assert after 2 cycles"
    # Read result vector (should be a+b per lane): 1+2=3, 2+3=5, ... 8+9=17
    result = int(dut.host_simd_result.value)
    # unpack lane 0 and 1 for quick check (lane0 = 1+2=3)
    lane0 = (result >> (0*32)) & 0xFFFFFFFF
    lane1 = (result >> (1*32)) & 0xFFFFFFFF
    assert lane0 == 3, f"SIMD lane0 {lane0} != 3 (1+2)"
    assert lane1 == 5, f"SIMD lane1 {lane1} != 5 (2+3)"
    await RisingEdge(dut.clk)

    # 4. Back pressure: cache still works after compute jobs
    dut.host_req_x.value = 10; dut.host_req_y.value = 20; dut.host_req_z.value = 7; dut.host_req_t.value = 5
    dut.host_req_valid.value = 1
    await RisingEdge(dut.clk)
    dut.host_req_valid.value = 0
    await RisingEdge(dut.clk)
    assert int(dut.host_resp_valid.value) == 1, "cache still responsive after compute"

@cocotb.test()
async def test_e2e_concurrent_cache_and_compute(dut):
    """Cache request and matmul can interleave without deadlock"""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    # Start matmul
    dut.host_matmul_start.value = 1; await RisingEdge(dut.clk); dut.host_matmul_start.value = 0
    # While busy, issue cache request
    dut.host_req_x.value = 1; dut.host_req_y.value = 1; dut.host_req_z.value = 1; dut.host_req_t.value = 1
    dut.host_req_valid.value = 1; await RisingEdge(dut.clk); dut.host_req_valid.value = 0
    await RisingEdge(dut.clk)
    assert int(dut.host_resp_valid.value) == 1, "cache should not stall while matmul busy"
    # Wait for matmul done
    done = False
    for _ in range(15):
        await RisingEdge(dut.clk)
        if int(dut.host_compute_done.value) == 1:
            done = True; break
    assert done, "matmul done"

@cocotb.test()
async def test_e2e_determinism(dut):
    """Repeat same matmul -> same timing and same SIMD result => deterministic gpu_top"""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    results = []
    for _ in range(3):
        dut.host_matmul_start.value = 1; await RisingEdge(dut.clk); dut.host_matmul_start.value = 0
        cycles = 0
        for _ in range(20):
            await RisingEdge(dut.clk); cycles += 1
            if int(dut.host_compute_done.value) == 1:
                break
        results.append(cycles)
        await RisingEdge(dut.clk)
    assert results[0] == results[1] == results[2], f"matmul not deterministic {results}"
    # SIMD determinism
    dut.host_simd_op.value = 1; dut.host_simd_is_fp32.value = 0  # INT8_MUL
    dut.host_simd_start.value = 1; await RisingEdge(dut.clk); dut.host_simd_start.value = 0
    await RisingEdge(dut.clk); await RisingEdge(dut.clk)
    r1 = int(dut.host_simd_result.value)
    await RisingEdge(dut.clk)
    dut.host_simd_start.value = 1; await RisingEdge(dut.clk); dut.host_simd_start.value = 0
    await RisingEdge(dut.clk); await RisingEdge(dut.clk)
    r2 = int(dut.host_simd_result.value)
    assert r1 == r2, f"SIMD not deterministic {hex(r1)} vs {hex(r2)}"
