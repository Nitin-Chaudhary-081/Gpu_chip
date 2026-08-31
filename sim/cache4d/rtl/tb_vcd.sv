// VCD waveform generator for GTKWave — Phase B
// Produces /tmp/wave.vcd showing 4D cache timing determinism gpu.md:16
module tb_vcd;
    logic clk, rst_n;
    logic req_valid;
    logic [5:0] req_x, req_y;
    logic [4:0] req_z;
    logic [3:0] req_t;
    logic req_is_store;
    logic resp_valid;
    logic [3:0] resp_bank;
    logic [9:0] resp_line;
    logic [2:0] resp_lambda;
    logic [1:0] resp_slot;
    logic [3:0] resp_cycles;

    cache_4d_controller dut (
        .clk(clk), .rst_n(rst_n),
        .req_valid(req_valid),
        .req_x(req_x), .req_y(req_y), .req_z(req_z), .req_t(req_t),
        .req_is_store(req_is_store),
        .resp_valid(resp_valid),
        .resp_bank(resp_bank), .resp_line(resp_line),
        .resp_lambda(resp_lambda), .resp_slot(resp_slot),
        .resp_cycles(resp_cycles),
        .resp_hit()
    );

    initial clk = 0;
    always #5 clk = ~clk; // 10ns period = 100MHz

    initial begin
        $dumpfile("/tmp/wave.vcd");
        $dumpvars(0, tb_vcd);
        $display("=== VCD Waveform: 4D Cache Determinism gpu.md:16 ===");

        rst_n=0; req_valid=0; #20; rst_n=1; #10;

        // Sequence: 8 diverse coords showing slot->cycles mapping
        // slot = (z+t)%4, cycles=4+slot*2 -> 4,6,8,10
        req_x=5; req_y=7; req_z=0; req_t=0; req_valid=1; #10; // slot 0 -> 4 cycles
        req_x=5; req_y=7; req_z=0; req_t=1; #10; // slot 1 -> 6
        req_x=5; req_y=7; req_z=0; req_t=2; #10; // slot 2 -> 8
        req_x=5; req_y=7; req_z=0; req_t=3; #10; // slot 3 ->10
        req_x=1; req_y=2; req_z=3; req_t=4; #10; // slot (3+4)%4=3 ->10
        req_x=10; req_y=20; req_z=7; req_t=2; #10; // slot 1 ->6
        req_x=0; req_y=0; req_z=0; req_t=0; #10;
        req_x=63; req_y=63; req_z=31; req_t=15; #10;

        req_valid=0; #30;
        $display("VCD done: /tmp/wave.vcd");
        $display("Open locally: gtkwave /tmp/wave.vcd  (signals: clk, req_*, resp_*)");
        $finish;
    end
endmodule
