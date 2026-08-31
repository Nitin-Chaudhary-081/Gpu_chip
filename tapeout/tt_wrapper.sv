// TinyTapeout wrapper — gpu_1.md:6 + gpu_1.md:8
// Serializes 23-input cache_4d_controller to TT's 8+8 pins via shift registers
// Fits TinyTapeout die constraints (160x100um per tile)
// Not yet DRC/LVS verified — IMPLEMENTED but not VERIFIED; needs yosys + cocotb on wrapper
// Replaces photonic/M3D wafers with Si proxy; CNFET power stays in sim model gpu.md:5

`default_nettype none

module tt_um_4d_cache (
    input  wire [7:0] ui_in,    // dedicated inputs
    output wire [7:0] uo_out,   // dedicated outputs
    input  wire [7:0] uio_in,   // IOs
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,      // will go high when design is enabled
    input  wire       clk,
    input  wire       rst_n
);
    // Cache controller instance — Si-proxy for CNFET gpu.md:5
    // Photonics / M3D tiers abstracted; GDS will be pure sky130 logic
    logic        req_valid;
    logic [5:0]  req_x, req_y;
    logic [4:0]  req_z;
    logic [3:0]  req_t;
    logic        req_is_store;

    logic        resp_valid;
    logic [3:0]  resp_bank;
    logic [9:0]  resp_line;
    logic [2:0]  resp_lambda;
    logic [1:0]  resp_slot;
    logic [3:0]  resp_cycles;
    logic        resp_hit;

    // Shift-in: 3 bytes = 24 bits holds {valid,is_store,x6,y6,z5,t4} packed into 23 bits
    logic [23:0] shift_in;
    logic [1:0]  in_cnt;
    logic        latched_valid;

    // Shift-out: 3 bytes = resp {valid,bank4,lambda3,slot2,cycles4,hit} = 15 bits -> pad to 16
    logic [15:0] shift_out;
    logic [1:0]  out_cnt;

    cache_4d_controller ctrl (
        .clk(clk), .rst_n(rst_n),
        .req_valid(req_valid),
        .req_x(req_x), .req_y(req_y), .req_z(req_z), .req_t(req_t),
        .req_is_store(req_is_store),
        .resp_valid(resp_valid),
        .resp_bank(resp_bank), .resp_line(resp_line),
        .resp_lambda(resp_lambda), .resp_slot(resp_slot),
        .resp_cycles(resp_cycles), .resp_hit(resp_hit)
    );

    // Input serializer: ui_in[7] is load strobe (high for cycle 0 of packet)
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            shift_in <= '0; in_cnt <= '0; latched_valid <= 1'b0;
            req_valid <= 1'b0; req_is_store <= 1'b0;
            req_x <= '0; req_y <= '0; req_z <= '0; req_t <= '0;
        end else begin
            if (ui_in[7]) begin // start of packet
                shift_in[7:0] <= ui_in;
                in_cnt <= 1;
            end else if (in_cnt == 1) begin
                shift_in[15:8] <= ui_in;
                in_cnt <= 2;
            end else if (in_cnt == 2) begin
                shift_in[23:16] <= ui_in;
                // Unpack: layout [23:23]=valid, [22]=is_store, [21:16]=x, [15:10]=y, [9:5]=z, [4:1]=t, [0]=0 pad
                req_valid    <= shift_in[23];
                req_is_store <= shift_in[22];
                req_x        <= shift_in[21:16];
                req_y        <= shift_in[15:10];
                req_z        <= shift_in[9:5];
                req_t        <= shift_in[4:1];
                in_cnt <= 0;
                latched_valid <= 1'b1;
            end else begin
                if (latched_valid) begin
                    // hold for one cycle to let controller respond
                    latched_valid <= 1'b0;
                end else begin
                    req_valid <= 1'b0;
                end
            end
        end
    end

    // Output serializer: on resp_valid, load shift_out and clock out over 2 bytes
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            shift_out <= '0; out_cnt <= '0;
        end else begin
            if (resp_valid && out_cnt == 0) begin
                shift_out <= {resp_valid, resp_hit, resp_bank, resp_lambda, resp_slot, resp_cycles, 1'b0}; // 1+1+4+3+2+4+1=16
                out_cnt <= 1;
            end else if (out_cnt != 0) begin
                out_cnt <= out_cnt + 1;
                if (out_cnt == 2) out_cnt <= 0;
            end
        end
    end

    assign uo_out  = (out_cnt == 1) ? shift_out[7:0]  :
                     (out_cnt == 2) ? shift_out[15:8] : 8'h00;
    assign uio_out = 8'h00;
    assign uio_oe  = 8'h00;

endmodule
