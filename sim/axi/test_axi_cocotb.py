import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

@cocotb.test()
async def test_axi_write_read(dut):
    cocotb.start_soon(Clock(dut.aclk, 10, unit="ns").start())
    dut.aresetn.value = 0
    dut.awaddr.value = 0
    dut.awvalid.value = 0
    dut.wdata.value = 0
    dut.wstrb.value = 0xF
    dut.wvalid.value = 0
    dut.bready.value = 1
    dut.araddr.value = 0
    dut.arvalid.value = 0
    dut.rready.value = 1
    dut.host_req_ready.value = 1
    dut.host_resp_valid.value = 0
    dut.host_resp_bank.value = 0
    await ClockCycles(dut.aclk, 2)
    dut.aresetn.value = 1
    await RisingEdge(dut.aclk)
    # write reg_req at 0x00 with host_req_valid=1 + x=5 y=7 z=3 t=9
    # reg_req bits: 31=valid, 22:17 x, 16:11 y, 10:6 z, 5:2 t
    x=5; y=7; z=3; t=9
    wdata = (1<<31) | (x<<17) | (y<<11) | (z<<6) | (t<<2)
    dut.awaddr.value = 0x00
    dut.wdata.value = wdata
    dut.awvalid.value = 1
    dut.wvalid.value = 1
    await RisingEdge(dut.aclk)
    dut.awvalid.value = 0
    dut.wvalid.value = 0
    await RisingEdge(dut.aclk)
    assert int(dut.host_req_valid.value) == 1
    assert int(dut.host_req_x.value) == x
    assert int(dut.host_req_y.value) == y
    assert int(dut.host_req_z.value) == z
    assert int(dut.host_req_t.value) == t
    # read status at 0x04
    dut.araddr.value = 0x04
    dut.arvalid.value = 1
    await RisingEdge(dut.aclk)
    assert int(dut.rvalid.value) == 1
    dut.arvalid.value = 0

@cocotb.test()
async def test_axi_no_hang(dut):
    cocotb.start_soon(Clock(dut.aclk, 10, unit="ns").start())
    dut.aresetn.value = 0
    await ClockCycles(dut.aclk, 2)
    dut.aresetn.value = 1
    for i in range(10):
        dut.awaddr.value = (i%4)*4
        dut.wdata.value = i
        dut.awvalid.value = 1
        dut.wvalid.value = 1
        await RisingEdge(dut.aclk)
        assert int(dut.bvalid.value) == 1
        dut.awvalid.value = 0
        dut.wvalid.value = 0
        await RisingEdge(dut.aclk)
