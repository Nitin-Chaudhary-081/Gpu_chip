// sram_4k.sv — 4KB SRAM 1024×32 1R1W  gpu_A.md:51
// OpenRAM sky130 proxy: flop array for VM, blackbox for hardening via EXTRA_LEFS
// For 1mm scaling, will be replaced by OpenRAM generated macro sky130_sram_1kbyte_1rw1r_32x1024_8

`default_nettype none

module sram_4k #(
    parameter int DEPTH = 1024,
    parameter int WIDTH = 32,
    parameter int ADDRW = 10
)(
    input  logic               clk,
    input  logic               cen,      // chip enable (active low in OpenRAM, here active high)
    input  logic               wen,      // write enable
    input  logic [ADDRW-1:0]   addr,
    input  logic [WIDTH-1:0]   wdata,
    output logic [WIDTH-1:0]   rdata
);
    // flop array — lean for 1.9GB VM; OpenRAM will replace with hard macro
    logic [WIDTH-1:0] mem [0:DEPTH-1];

    // initial for sim
    initial begin
        for (int i=0; i<DEPTH; i++) mem[i] = '0;
    end

    // synchronous write, async read (512ps)
    always_ff @(posedge clk) begin
        if (cen && wen) mem[addr] <= wdata;
    end

    assign rdata = mem[addr];

    // For hardening: GDS LEF will be via EXTRA_* in openlane/gpu_top_1mm/config.json:20
    // synopsys translate_off
    // pragma translate_off
    logic _unused;
    assign _unused = ^mem[0];
    // synopsys translate_on

endmodule

// Wrapper for openlane/sram_4k macro hardening — 400×400 placeholder
module sram_4k_macro #(
    parameter int DEPTH = 1024,
    parameter int WIDTH = 32
)(
    input  logic clk, cen, wen,
    input  logic [9:0] addr,
    input  logic [31:0] wdata,
    output logic [31:0] rdata
);
    sram_4k #(.DEPTH(DEPTH), .WIDTH(WIDTH)) u_sram (
        .clk(clk), .cen(cen), .wen(wen), .addr(addr), .wdata(wdata), .rdata(rdata)
    );
endmodule
