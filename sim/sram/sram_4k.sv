// sram_4k.sv — 4KB SRAM 1024×32 1R1W using OpenRAM macro  gpu_A.md:51
// Uses 4× sky130_sram_1kbyte_1rw1r_32x256_8 macros for 4KB total
// For 1mm scaling, will be replaced by OpenRAM generated macro sky130_sram_1kbyte_1rw1r_32x1024_8

`default_nettype none

// Blackbox for OpenRAM sky130_sram_1kbyte_1rw1r_32x256_8 (1KB = 256×32)
module sky130_sram_1kbyte_1rw1r_32x256_8 (
    input  logic        clk0,
    input  logic        csb0,
    input  logic        web0,
    input  logic [7:0]  addr0,
    input  logic [31:0] din0,
    output logic [31:0] dout0
);
endmodule

// 4KB SRAM using 4× 1KB OpenRAM macros
module sram_4k #(
    parameter int DEPTH = 1024,
    parameter int WIDTH = 32,
    parameter int ADDRW = 10
)(
    input  logic               clk,
    input  logic               cen,      // chip enable (active high)
    input  logic               wen,      // write enable
    input  logic [ADDRW-1:0]   addr,
    input  logic [WIDTH-1:0]   wdata,
    output logic [WIDTH-1:0]   rdata
);

    // Each macro is 256×32 (1KB), we need 4 for 4KB = 1024×32
    // Address mapping: addr[9:8] selects macro, addr[7:0] is macro address
    logic [1:0] macro_sel;
    logic [7:0] macro_addr;
    assign macro_sel = addr[9:8];
    assign macro_addr = addr[7:0];

    logic [31:0] dout [0:3];
    logic [3:0]  csb, web;

    // Active-low chip select and write enable for OpenRAM
    always_comb begin
        csb = 4'hF;
        web = 4'hF;
        if (cen) begin
            csb[macro_sel] = 1'b0;
            web[macro_sel] = ~wen;
        end
    end

    // Instantiate 4× 1KB macros
    genvar m;
    generate
        for (m=0; m<4; m++) begin : GEN_SRAM
            sky130_sram_1kbyte_1rw1r_32x256_8 u_sram (
                .clk0(clk),
                .csb0(csb[m]),
                .web0(web[m]),
                .addr0(macro_addr),
                .din0(wdata),
                .dout0(dout[m])
            );
        end
    endgenerate

    // Output mux
    always_comb begin
        rdata = dout[macro_sel];
    end

    // For hardening: GDS LEF will be via EXTRA_* in openlane/gpu_top_1mm/config.json
    // synopsys translate_off
    // pragma translate_off
    logic _unused;
    assign _unused = ^dout[0];
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