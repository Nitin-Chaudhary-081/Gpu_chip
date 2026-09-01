// register_file.sv — 256 × 32-bit, 2R1W  gpu_A.md:96
// Synthesizable, connects to SIMD ALU per gpu_A.md:97
// Test: load regs → execute ADD → verify == expected

`default_nettype none

module register_file #(
    parameter int DEPTH = 256,
    parameter int WIDTH = 32,
    parameter int ADDRW = 8  // log2(256)=8
)(
    input  logic               clk,
    input  logic               rst_n,
    // write port
    input  logic               we,
    input  logic [ADDRW-1:0]   waddr,
    input  logic [WIDTH-1:0]   wdata,
    // read ports (combinational)
    input  logic [ADDRW-1:0]   raddr0,
    input  logic [ADDRW-1:0]   raddr1,
    output logic [WIDTH-1:0]   rdata0,
    output logic [WIDTH-1:0]   rdata1
);
    // 256 × 32-bit memory — inferred as flops (sky130 no hard BRAM for lean)
    logic [WIDTH-1:0] regs [0:DEPTH-1];

    // synchronous write, async read — no reset init (array reset via initial for sim)
    initial begin
        for (int i=0; i<DEPTH; i++) regs[i] = '0;
    end
    always_ff @(posedge clk) begin
        if (we) regs[waddr] <= wdata;
    end
    // tie rst_n to avoid unused warning
    logic _unused_rst;
    assign _unused_rst = rst_n;

    assign rdata0 = regs[raddr0];
    assign rdata1 = regs[raddr1];

endmodule

// Wrapper for 8-lane vector register file (256 entries each lane? single file shared)
// For shader we expose 8-lane vector via 256×32 but test uses single port
module register_file_vector #(
    parameter int LANES = 8,
    parameter int DEPTH = 256
)(
    input  logic clk, rst_n,
    input  logic we,
    input  logic [7:0] waddr,
    input  logic [31:0] wdata,
    input  logic [7:0] raddr0, raddr1,
    output logic [31:0] rdata0, rdata1
);
    register_file #(.DEPTH(DEPTH), .WIDTH(32)) u_rf (
        .clk(clk), .rst_n(rst_n),
        .we(we), .waddr(waddr), .wdata(wdata),
        .raddr0(raddr0), .raddr1(raddr1),
        .rdata0(rdata0), .rdata1(rdata1)
    );
endmodule
