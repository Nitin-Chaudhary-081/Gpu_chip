# gpu_top cocotb — parallel host_req_* + dummy systolic + WDM
# Approve spec: tt_um_4d_cache top, macro hardening, 8x8 BRAM, host_req parallel lean
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

W=8; T=4; BASE=4; SLOTC=2

async def reset(dut):
    dut.rst_n.value=0; dut.clk.value=0
    dut.host_req_valid.value=0; dut.host_matmul_start.value=0
    for _ in range(3): await RisingEdge(dut.clk)
    dut.rst_n.value=1; await RisingEdge(dut.clk)

@cocotb.test()
async def test_gpu_top_parallel(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    for x,y,z,t in [(5,7,3,9),(0,0,0,0),(63,63,31,15),(10,20,7,5)]:
        dut.host_req_x.value=x; dut.host_req_y.value=y; dut.host_req_z.value=z; dut.host_req_t.value=t
        dut.host_req_valid.value=1; dut.host_req_is_store.value=0
        await RisingEdge(dut.clk)
        dut.host_req_valid.value=0
        await RisingEdge(dut.clk)
        # resp valid 1 cycle after req
        assert int(dut.host_resp_valid.value)==1, f"resp_valid x={x} y={y} z={z} t={t} got {int(dut.host_resp_valid.value)}"
        exp_lam=t%W; exp_slot=(z%4 + t%4)%T; exp_cycles=BASE+exp_slot*SLOTC
        assert int(dut.host_resp_lambda.value)==exp_lam, f"lam {int(dut.host_resp_lambda.value)}!={exp_lam}"
        assert int(dut.host_resp_slot.value)==exp_slot
        assert int(dut.host_resp_cycles.value)==exp_cycles
        assert int(dut.host_wdm_valid.value)==1
        await RisingEdge(dut.clk)

@cocotb.test()
async def test_gpu_top_matmul(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    dut.host_matmul_start.value=1; await RisingEdge(dut.clk); dut.host_matmul_start.value=0
    await RisingEdge(dut.clk)
    assert int(dut.host_compute_busy.value)==1, "busy"
    # Poll for done up to 10 cycles
    done=False
    for _ in range(10):
        await RisingEdge(dut.clk)
        if int(dut.host_compute_done.value)==1:
            done=True; break
    assert done, "done not asserted within 10 cycles"
    await RisingEdge(dut.clk)
    assert int(dut.host_compute_busy.value)==0
