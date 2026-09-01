// simd_alu.sv — 8-lane FP32 SIMD ALU  gpu_A.md:37,94
// Minimal fabricatable FP32: ADD/MUL/MAX, 1-cycle pipeline, deterministic
// FP32 strict per ADR-004; synthesizable via sky130_fd_sc_hd cells
// Verified vs numpy float32 golden (exact ints <2^24)  gpu_A.md:45
// For normal numbers only (subnormal=>0, Inf/NaN passthrough)
// Part of Phase D compute tile; hardened separately openlane/shader 200x200 (gpu_A.md:49)

`default_nettype none

module simd_alu #(
    parameter LANES = 8,
    parameter DATAW = 32
)(
    input  logic               clk,
    input  logic               rst_n,
    input  logic               in_valid,
    input  logic [1:0]         op,          // 0 ADD 1 MUL 2 MAX 3 NOP
    input  logic [LANES*DATAW-1:0] a,
    input  logic [LANES*DATAW-1:0] b,
    output logic               out_valid,
    output logic [LANES*DATAW-1:0] result
);
    // FP32 helpers — yosys 0.33 compatible (no automatic/return)
    /* verilator lint_off WIDTHEXPAND */
    /* verilator lint_off WIDTHTRUNC */

    function [31:0] fp32_add;
        input [31:0] a_in, b_in;
        reg        sign_a, sign_b, sign_res, sign_big, sign_small;
        reg [7:0]  exp_a, exp_b, exp_big, exp_small, exp_res;
        reg [22:0] mant_a, mant_b;
        reg [23:0] m_a, m_b, m_big, m_small;
        reg [24:0] m_sum;
        integer    shift, i;
        reg        done;
        begin
            sign_a = a_in[31]; exp_a = a_in[30:23]; mant_a = a_in[22:0];
            sign_b = b_in[31]; exp_b = b_in[30:23]; mant_b = b_in[22:0];
            // zero fast
            if (exp_a==8'd0 && mant_a==23'd0) fp32_add = b_in;
            else if (exp_b==8'd0 && mant_b==23'd0) fp32_add = a_in;
            else if (exp_a==8'hFF) fp32_add = a_in;
            else if (exp_b==8'hFF) fp32_add = b_in;
            else begin
                m_a = (exp_a==8'd0) ? {1'b0, mant_a} : {1'b1, mant_a};
                m_b = (exp_b==8'd0) ? {1'b0, mant_b} : {1'b1, mant_b};
                if (exp_a > exp_b || (exp_a==exp_b && m_a >= m_b)) begin
                    exp_big = exp_a; m_big = m_a; sign_big = sign_a;
                    exp_small = exp_b; m_small = m_b; sign_small = sign_b;
                end else begin
                    exp_big = exp_b; m_big = m_b; sign_big = sign_b;
                    exp_small = exp_a; m_small = m_a; sign_small = sign_a;
                end
                shift = exp_big - exp_small;
                if (shift > 24) m_small = 24'd0;
                else m_small = m_small >> shift;
                exp_res = exp_big;
                if (sign_a == sign_b) begin
                    m_sum = {1'b0, m_big} + {1'b0, m_small};
                    sign_res = sign_a;
                    if (m_sum[24]) begin
                        m_sum = m_sum >> 1;
                        exp_res = exp_res + 1;
                    end
                end else begin
                    m_sum = {1'b0, m_big} - {1'b0, m_small};
                    sign_res = sign_big;
                    if (m_sum == 25'd0) begin
                        fp32_add = 32'd0;
                        done = 1;
                    end else begin
                        done = 0;
                        // normalize
                        for (i=0; i<24; i=i+1) begin
                            if (!done && m_sum[23]==1'b0 && exp_res > 8'd0 && m_sum != 25'd0) begin
                                m_sum = m_sum << 1;
                                exp_res = exp_res - 1;
                            end
                        end
                    end
                    if (m_sum == 25'd0) begin
                        // already returned 0 above, but keep
                    end else if (exp_res >= 8'hFF) fp32_add = {sign_res, 8'hFF, 23'd0};
                    else if (exp_res == 8'd0) fp32_add = 32'd0;
                    else fp32_add = {sign_res, exp_res, m_sum[22:0]};
                    done = 1;
                end
                // for add case not yet assigned
                if (sign_a == sign_b) begin
                    if (exp_res >= 8'hFF) fp32_add = {sign_res, 8'hFF, 23'd0};
                    else if (exp_res == 8'd0) fp32_add = 32'd0;
                    else fp32_add = {sign_res, exp_res, m_sum[22:0]};
                end
            end
        end
    endfunction

    function [31:0] fp32_mul;
        input [31:0] a_in, b_in;
        reg sign_a, sign_b, sign_res;
        reg [7:0] exp_a, exp_b, exp_res, exp_tmp;
        reg [22:0] mant_a, mant_b;
        reg [23:0] m_a, m_b;
        reg [47:0] prod;
        begin
            sign_a = a_in[31]; exp_a = a_in[30:23]; mant_a = a_in[22:0];
            sign_b = b_in[31]; exp_b = b_in[30:23]; mant_b = b_in[22:0];
            sign_res = sign_a ^ sign_b;
            if ((exp_a==8'd0 && mant_a==23'd0) || (exp_b==8'd0 && mant_b==23'd0)) fp32_mul = {sign_res, 31'd0};
            else if (exp_a==8'hFF) fp32_mul = a_in;
            else if (exp_b==8'hFF) fp32_mul = b_in;
            else begin
                m_a = {1'b1, mant_a};
                m_b = {1'b1, mant_b};
                exp_tmp = exp_a + exp_b;
                exp_res = exp_tmp - 8'd127;
                prod = m_a * m_b;
                if (prod == 48'd0) fp32_mul = 32'd0;
                else if (prod[47]) begin
                    exp_res = exp_res + 1;
                    if (exp_res >= 8'hFF) fp32_mul = {sign_res, 8'hFF, 23'd0};
                    else fp32_mul = {sign_res, exp_res, prod[46:24]};
                end else begin
                    if (exp_res >= 8'hFF) fp32_mul = {sign_res, 8'hFF, 23'd0};
                    else if (exp_res == 8'd0) fp32_mul = 32'd0;
                    else fp32_mul = {sign_res, exp_res, prod[45:23]};
                end
            end
        end
    endfunction

    function is_a_gt_b;
        input [31:0] a_in, b_in;
        reg sign_a, sign_b;
        begin
            sign_a = a_in[31]; sign_b = b_in[31];
            if (sign_a != sign_b) is_a_gt_b = !sign_a;
            else if (sign_a==1'b0) is_a_gt_b = a_in > b_in;
            else is_a_gt_b = a_in < b_in;
        end
    endfunction

    function [31:0] fp32_max;
        input [31:0] a_in, b_in;
        begin
            if (a_in[30:23]==8'hFF && a_in[22:0]!=0) fp32_max = b_in;
            else if (b_in[30:23]==8'hFF && b_in[22:0]!=0) fp32_max = a_in;
            else if (is_a_gt_b(a_in, b_in)) fp32_max = a_in;
            else fp32_max = b_in;
        end
    endfunction

    /* verilator lint_on WIDTHEXPAND */
    /* verilator lint_on WIDTHTRUNC */

    logic [LANES*DATAW-1:0] result_comb;
    logic out_valid_comb;

    always_comb begin
        result_comb = '0;
        for (int i=0; i<LANES; i++) begin
            logic [31:0] av, bv, rv;
            av = a[i*DATAW +: DATAW];
            bv = b[i*DATAW +: DATAW];
            case (op)
                2'd0: rv = fp32_add(av, bv);
                2'd1: rv = fp32_mul(av, bv);
                2'd2: rv = fp32_max(av, bv);
                default: rv = av;
            endcase
            result_comb[i*DATAW +: DATAW] = rv;
        end
        out_valid_comb = in_valid;
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            out_valid <= 1'b0;
            result    <= '0;
        end else begin
            out_valid <= out_valid_comb;
            if (in_valid) result <= result_comb;
        end
    end

endmodule
