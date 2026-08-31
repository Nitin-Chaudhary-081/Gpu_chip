// WDM/TDM Arbiter — gpu.md:6,16
// Allocates (lambda, slot) deterministically, no arbiter contention beyond wait
// 8 wavelengths * 4 slots -> 32 virtual channels per waveguide

module wdm_tdm_arbiter #(
    parameter WAVELENGTHS = 8,
    parameter TDM_SLOTS = 4,
    parameter N_WAVEGUIDES = 8,
    parameter BASE_LATENCY_NS = 2,
    parameter SLOT_NS = 1
)(
    input  logic        clk,
    input  logic        rst_n,
    // Request
    input  logic        req_valid,
    input  logic [5:0]  req_id,
    // Grant — deterministic same cycle
    output logic        gnt_valid,
    output logic [2:0]  gnt_lambda,
    output logic [1:0]  gnt_slot,
    output logic [3:0]  gnt_latency_ns
);
    // Deterministic hash: lambda = req_id % W, slot = (req_id / W) % T  gpu.md:16
    /* verilator lint_off WIDTHEXPAND */
    /* verilator lint_off WIDTHTRUNC */
    assign gnt_lambda     = req_id[2:0] % WAVELENGTHS;
    assign gnt_slot       = (req_id[5:3]) % TDM_SLOTS;
    /* verilator lint_on WIDTHEXPAND */
    /* verilator lint_on WIDTHTRUNC */
    assign gnt_latency_ns = BASE_LATENCY_NS + gnt_slot * SLOT_NS;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) gnt_valid <= 1'b0;
        else        gnt_valid <= req_valid;
    end

    // Parallelism check
    // max_parallel = N_WAVEGUIDES * WAVELENGTHS = 64
endmodule
