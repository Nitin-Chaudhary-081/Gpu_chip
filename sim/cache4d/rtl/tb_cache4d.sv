// Testbench for cache_4d_controller + wdm_tdm_arbiter
// Run with iverilog: iverilog -g2012 -o tb.vvp cache_4d_controller.sv wdm_tdm_arbiter.sv tb_cache4d.sv && vvp tb.vvp
// Or verilator lint: verilator --lint-only cache_4d_controller.sv
module tb_cache4d;
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

    // Clock
    initial clk = 0;
    always #5 clk = ~clk;

    integer pass=0, fail=0;
    initial begin
        $display("=== RTL 4D Cache TB  gpu.md:16 ===");
        rst_n=0; req_valid=0; #20; rst_n=1; #10;

        // Test 1: deterministic mapping
        req_x=5; req_y=7; req_z=3; req_t=9; req_is_store=0; req_valid=1;
        #10; // one cycle
        $display("Coord (5,7,3,9) -> bank=%0d lambda=%0d slot=%0d cycles=%0d valid=%0d", resp_bank, resp_lambda, resp_slot, resp_cycles, resp_valid);
        if (resp_lambda==1 && resp_slot==0 && resp_cycles==4) begin pass++; $display("PASS lambda/slot"); end else begin fail++; $display("FAIL"); end
        // Wait one more cycle for pipeline
        #10;
        if (resp_valid) pass++; else fail++;

        // Test 2: bounded latency 4-10
        req_x=1; req_y=2; req_z=3; req_t=4; #10; #10;
        if (resp_cycles>=4 && resp_cycles<=10) begin pass++; $display("PASS bounded latency %0d", resp_cycles); end else begin fail++; $display("FAIL latency %0d", resp_cycles); end

        // Test 3: sweep check determinism: same coord -> same output (re-latch properly)
        req_x=10; req_y=20; req_z=7; req_t=2; req_valid=1; #10; #10;
        begin
            logic [3:0] b1;
            logic [2:0] l1;
            b1 = resp_bank; l1 = resp_lambda;
            $display("  capture b1=%0d l1=%0d", b1, l1);
            req_valid=0; #10;
            req_x=10; req_y=20; req_z=7; req_t=2; req_valid=1; #10; #10;
            if (resp_bank==b1 && resp_lambda==l1) begin pass++; $display("PASS deterministic re-access"); end else begin fail++; $display("FAIL deterministic got bank %0d lambda %0d exp bank %0d lambda %0d", resp_bank, resp_lambda, b1, l1); end
        end

        // Test 4: slot = (z+t)%4
        req_z=2; req_t=3; #10; #10;
        if (resp_slot == (2+3)%4) begin pass++; $display("PASS slot hash"); end else begin fail++; $display("FAIL slot %0d exp %0d", resp_slot, (2+3)%4); end

        $display("=== TB DONE pass=%0d fail=%0d ===", pass, fail);
        if (fail==0) $display("ALL PASS"); else $display("FAILURES");
        $finish;
    end
endmodule
