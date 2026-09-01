// warp_scheduler.sv — GTO + Round-Robin warp scheduler  gpu_A.md:84
// Yosys 0.33 compatible: use int inside for per simd_alu pattern

`default_nettype none

module warp_scheduler #(
    parameter int NUM_WARPS = 8,
    parameter int NUM_THREADS = 32,
    parameter int AGEW = 8
)(
    input  logic                         clk,
    input  logic                         rst_n,
    input  logic [NUM_WARPS-1:0]         warp_ready,
    input  logic [NUM_WARPS-1:0]         warp_valid,
    output logic [NUM_WARPS-1:0]         warp_issue,
    output logic [$clog2(NUM_WARPS)-1:0] warp_id,
    output logic                         issue_valid
);
    logic [$clog2(NUM_WARPS)-1:0] last_issued;
    logic [AGEW-1:0] age [0:NUM_WARPS-1];

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (int i=0; i<NUM_WARPS; i=i+1) age[i] <= '0;
            last_issued <= '0;
        end else begin
            for (int i=0; i<NUM_WARPS; i=i+1) begin
                if (warp_issue[i]) age[i] <= '0;
                else if (warp_ready[i] && warp_valid[i]) age[i] <= age[i] + 1'b1;
            end
            if (issue_valid) last_issued <= warp_id;
        end
    end

    logic [$clog2(NUM_WARPS)-1:0] gto_id;
    logic [AGEW-1:0] max_age;
    logic found;

    always_comb begin
        warp_issue = '0;
        warp_id = '0;
        issue_valid = 1'b0;
        gto_id = '0;
        max_age = '0;
        found = 1'b0;
        if (warp_valid[last_issued] && warp_ready[last_issued]) begin
            warp_issue[last_issued] = 1'b1;
            warp_id = last_issued;
            issue_valid = 1'b1;
        end else begin
            for (int j=0; j<NUM_WARPS; j=j+1) begin
                if (warp_valid[j] && warp_ready[j]) begin
                    if (!found || age[j] > max_age) begin
                        max_age = age[j];
                        gto_id = j[ $clog2(NUM_WARPS)-1:0 ];
                        found = 1'b1;
                    end
                end
            end
            if (found) begin
                warp_issue[gto_id] = 1'b1;
                warp_id = gto_id;
                issue_valid = 1'b1;
            end
        end
    end

endmodule

module warp_scheduler_rr #(
    parameter int NUM_WARPS = 8
)(
    input  logic clk, rst_n,
    input  logic [NUM_WARPS-1:0] warp_ready,
    input  logic [NUM_WARPS-1:0] warp_valid,
    output logic [NUM_WARPS-1:0] warp_issue,
    output logic [$clog2(NUM_WARPS)-1:0] warp_id,
    output logic issue_valid
);
    logic [$clog2(NUM_WARPS)-1:0] ptr;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) ptr <= '0;
        else if (issue_valid) ptr <= ptr + 1'b1;
    end
    logic found;
    always_comb begin
        warp_issue='0; warp_id='0; issue_valid=1'b0; found=1'b0;
        for (int i=0; i<NUM_WARPS; i=i+1) begin
            int idx;
            idx = (ptr + i) % NUM_WARPS;
            if (!found && warp_valid[idx] && warp_ready[idx]) begin
                warp_issue[idx]=1'b1; warp_id=idx[$clog2(NUM_WARPS)-1:0]; issue_valid=1'b1; found=1'b1;
            end
        end
    end
endmodule
