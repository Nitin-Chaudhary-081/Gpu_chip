// axi_slave.sv — AXI4-Lite slave for host interface  gpu_A.md:87
// Real GPU needs host interface so CPU can send commands/data.
// Implements AXI4-Lite slave 32-bit, 1 outstanding, for gpu_top host_req_* bridging.
// Lean: 4 registers at 0x00..0x0C (control, status, data, config)

`default_nettype none

module axi_slave #(
    parameter int ADDRW = 32,
    parameter int DATAW = 32
)(
    input  logic               aclk,
    input  logic               aresetn,
    // Write address
    input  logic [ADDRW-1:0]   awaddr,
    input  logic               awvalid,
    output logic               awready,
    // Write data
    input  logic [DATAW-1:0]   wdata,
    input  logic [(DATAW/8)-1:0] wstrb,
    input  logic               wvalid,
    output logic               wready,
    // Write response
    output logic [1:0]         bresp,
    output logic               bvalid,
    input  logic               bready,
    // Read address
    input  logic [ADDRW-1:0]   araddr,
    input  logic               arvalid,
    output logic               arready,
    // Read data
    output logic [DATAW-1:0]   rdata,
    output logic [1:0]         rresp,
    output logic               rvalid,
    input  logic               rready,
    // Host side (to gpu_top)
    output logic               host_req_valid,
    output logic [5:0]         host_req_x,
    output logic [5:0]         host_req_y,
    output logic [4:0]         host_req_z,
    output logic [3:0]         host_req_t,
    input  logic               host_req_ready,
    input  logic               host_resp_valid,
    input  logic [3:0]         host_resp_bank
);
    // Register map
    // 0x00: host_req (bits 22:0 = {is_store, x6, y6, z5, t4}) + valid bit 31
    // 0x04: status (bit0 host_resp_valid, bits 4:1 bank)
    // 0x08: config (unused)
    // 0x0C: control (matmul start)

    logic [31:0] reg_req, reg_status, reg_config, reg_ctrl;
    logic        aw_done, w_done;

    // AXI write
    assign awready = 1'b1;
    assign wready  = 1'b1;
    assign bresp   = 2'b00; // OKAY
    assign bvalid  = awvalid && wvalid;
    always_ff @(posedge aclk or negedge aresetn) begin
        if (!aresetn) begin
            reg_req <= '0; reg_config <= '0; reg_ctrl <= '0;
            aw_done <= 0; w_done <= 0;
        end else if (awvalid && wvalid) begin
            case (awaddr[3:2])
                2'd0: reg_req <= wdata;
                2'd2: reg_config <= wdata;
                2'd3: reg_ctrl <= wdata;
                default: ;
            endcase
        end
        // clear ctrl after one cycle (pulse)
        if (reg_ctrl[0]) reg_ctrl[0] <= 1'b0;
    end

    // AXI read
    assign arready = 1'b1;
    assign rresp   = 2'b00;
    assign rvalid  = arvalid;
    always_comb begin
        case (araddr[3:2])
            2'd0: rdata = reg_req;
            2'd1: rdata = {27'd0, host_resp_bank, host_resp_valid};
            2'd2: rdata = reg_config;
            2'd3: rdata = reg_ctrl;
            default: rdata = 32'd0;
        endcase
    end

    // Host side decode
    assign host_req_valid = reg_req[31];
    assign host_req_x = reg_req[22:17];
    assign host_req_y = reg_req[16:11];
    assign host_req_z = reg_req[10:6];
    assign host_req_t = reg_req[5:2];
    // is_store at bit 23 not used yet
    // host_req_ready unused in this lite version (always ready)
    logic _unused;
    assign _unused = host_req_ready;

endmodule
