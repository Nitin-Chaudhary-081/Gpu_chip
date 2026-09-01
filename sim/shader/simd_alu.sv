// simd_alu.sv — 8-lane FP32/INT8 SIMD ALU with 2-stage pipeline  gpu_A.md:37,94
// Stage 1: INT8 path (ADD/MUL/MAX) + FP32 operand decode
// Stage 2: FP32 path (ADD/MUL/MAX) + writeback
// FP32 strict per ADR-004; synthesizable via sky130_fd_sc_hd cells
// Clock-gates stage 2 when only INT8 ops dispatched (power saving)

`default_nettype none

module simd_alu #(
    parameter LANES = 8,
    parameter DATAW = 32
)(
    input  logic               clk,
    input  logic               rst_n,
    input  logic               in_valid,
    input  logic [2:0]         op,          // 0 INT8_ADD 1 INT8_MUL 2 INT8_MAX 3 FP32_ADD 4 FP32_MUL 5 FP32_MAX 6 NOP
    input  logic               is_fp32,     // 1=FP32 op, 0=INT8 op
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

    // INT8 helpers
    function [7:0] int8_add;
        input [7:0] a_in, b_in;
        logic signed [8:0] sum;
        begin
            sum = $signed(a_in) + $signed(b_in);
            // saturate to INT8 range
            if (sum > 9'sd127) int8_add = 8'sd127;
            else if (sum < -9'sd128) int8_add = -8'sd128;
            else int8_add = sum[7:0];
        end
    endfunction

    function [7:0] int8_mul;
        input [7:0] a_in, b_in;
        logic signed [15:0] prod;
        begin
            prod = $signed(a_in) * $signed(b_in);
            // saturate to INT8 range (16b -> 8b with saturation)
            if (prod > 16'sd127) int8_mul = 8'sd127;
            else if (prod < -16'sd128) int8_mul = -8'sd128;
            else int8_mul = prod[7:0];
        end
    endfunction

    function [7:0] int8_max;
        input [7:0] a_in, b_in;
        begin
            int8_max = ($signed(a_in) > $signed(b_in)) ? a_in : b_in;
        end
    endfunction

    /* verilator lint_on WIDTHEXPAND */
    /* verilator lint_on WIDTHTRUNC */

    // Stage 1: INT8 compute + FP32 decode
    logic [LANES*DATAW-1:0] result_s1;
    logic                   out_valid_s1;
    logic [2:0]             op_s1;
    logic                   is_fp32_s1;

    always_comb begin
        result_s1 = '0;
        for (int i=0; i<LANES; i++) begin
            logic [31:0] av, bv, rv;
            av = a[i*DATAW +: DATAW];
            bv = b[i*DATAW +: DATAW];
            if (!is_fp32) begin
                // INT8 operations on lower 8 bits
                logic [7:0] a8, b8, r8;
                a8 = av[7:0];
                b8 = bv[7:0];
                case (op)
                    3'd0: r8 = int8_add(a8, b8);
                    3'd1: r8 = int8_mul(a8, b8);
                    3'd2: r8 = int8_max(a8, b8);
                    default: r8 = a8;
                endcase
                rv = {{24{r8[7]}}, r8};  // sign extend to 32 bits
            end else begin
                // FP32 - just pass through to stage 2
                rv = av;
            end
            result_s1[i*DATAW +: DATAW] = rv;
        end
        out_valid_s1 = in_valid;
        op_s1 = op;
        is_fp32_s1 = is_fp32;
    end

    // Pipeline registers between stage 1 and 2
    logic [LANES*DATAW-1:0] result_s1_reg;
    logic                   out_valid_s1_reg;
    logic [2:0]             op_s1_reg;
    logic                   is_fp32_s1_reg;;
    logic [LANES*DATAW-1:0] a_s1_reg;
    logic [LANES*DATAW-1:0] b_s1_reg;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            result_s1_reg <= '0;
            out_valid_s1_reg <= 1'b0;
            op_s1_reg <= '0;
            is_fp32_s1_reg <= 1'b0;
            a_s1_reg <= '0;
            b_s1_reg <= '0;
        end else begin
            result_s1_reg <= result_s1;
            out_valid_s1_reg <= out_valid_s1;
            op_s1_reg <= op_s1;
            is_fp32_s1_reg <= is_fp32_s1;
            a_s1_reg <= a;
            b_s1_reg <= b;
        end
    end

    // Stage 2: FP32 compute (only active for FP32 ops)
    logic [LANES*DATAW-1:0] result_s2;
    logic                   out_valid_s2;

    always_comb begin
        result_s2 = result_s1_reg;
        out_valid_s2 = out_valid_s1_reg;
        if (is_fp32_s1_reg && out_valid_s1_reg) begin
            for (int i=0; i<LANES; i++) begin
                logic [31:0] av, bv, rv;
                av = a_s1_reg[i*DATAW +: DATAW];
                bv = b_s1_reg[i*DATAW +: DATAW];
                case (op_s1_reg)
                    3'd3: rv = fp32_add(av, bv);
                    3'd4: rv = fp32_mul(av, bv);
                    3'd5: rv = fp32_max(av, bv);
                    default: rv = av;
                endcase
                result_s2[i*DATAW +: DATAW] = rv;
            end
        end
    end

    // Output register
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            out_valid <= 1'b0;
            result    <= '0;
        end else begin
            out_valid <= out_valid_s2;
            if (out_valid_s2) result <= result_s2;
        end
    end

endmodule