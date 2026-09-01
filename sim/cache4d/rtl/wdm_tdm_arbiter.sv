// WDM/TDM Arbiter — gpu_A.md:93-94,99
// Full round-robin + priority arbitration for memory bus access between compute units
// Wavelength-division multiplexing (WDM) + Time-division multiplexing (TDM)
// Deterministic arbitration: no CU ever stalls waiting for bus
// Flattened interface for Yosys compatibility

`default_nettype none

module wdm_tdm_arbiter #(
    parameter int WAVELENGTHS = 8,          // WDM channels per waveguide
    parameter int TDM_SLOTS = 4,            // TDM slots per wavelength
    parameter int N_WAVEGUIDES = 8,         // Number of waveguides (max 64 virtual channels)
    parameter int N_REQUESTORS = 4,         // Number of compute units (CUs)
    parameter int BASE_LATENCY_NS = 2,      // Base latency in ns
    parameter int SLOT_NS = 1               // Slot duration in ns
)(
    input  logic                        clk,
    input  logic                        rst_n,
    // Request interface (one per CU) - flattened for Yosys compatibility
    input  logic [N_REQUESTORS-1:0]     req_valid,
    input  logic [N_REQUESTORS*6-1:0]   req_id,        // {waveguide[2:0], cu_id[2:0]} per CU
    input  logic [N_REQUESTORS*32-1:0]  req_addr,     // Memory address per CU
    input  logic [N_REQUESTORS-1:0]     req_is_write,   // 1=write, 0=read
    input  logic [N_REQUESTORS*32-1:0]  req_wdata,    // Write data per CU
    // Grant interface
    output logic [N_REQUESTORS-1:0]     gnt_valid,
    output logic [N_REQUESTORS*3-1:0]   gnt_lambda,    // WDM wavelength per CU
    output logic [N_REQUESTORS*2-1:0]   gnt_slot,      // TDM slot per CU
    output logic [N_REQUESTORS*4-1:0]   gnt_latency_ns,// Total latency per CU
    output logic [N_REQUESTORS-1:0]     gnt_ready,      // Data phase ready
    // Response interface (from memory)
    input  logic [N_REQUESTORS-1:0]     resp_valid,
    input  logic [N_REQUESTORS*32-1:0]  resp_rdata,
    // Status
    output logic [$clog2(N_REQUESTORS):0] active_count,
    output logic                        bus_busy
);

    localparam int MAX_CHANNELS = N_WAVEGUIDES * WAVELENGTHS * TDM_SLOTS;

    // Round-robin pointer
    logic [$clog2(N_REQUESTORS)-1:0] rr_ptr;

    // Time-slot counter (global across all waveguides)
    logic [$clog2(TDM_SLOTS * WAVELENGTHS * N_WAVEGUIDES)-1:0] slot_counter;

    // Per-requestor assigned channel/slot (flattened)
    logic [N_REQUESTORS*3-1:0] assigned_lambda;
    logic [N_REQUESTORS*2-1:0] assigned_slot;
    logic [N_REQUESTORS*3-1:0] assigned_waveguide;
    logic [N_REQUESTORS-1:0]   has_assignment;

    // Priority encoder for round-robin
    logic [N_REQUESTORS-1:0] req_masked;
    logic [$clog2(N_REQUESTORS)-1:0] grant_idx;
    logic grant_found;

    // Round-robin priority encoder
    always_comb begin
        req_masked = '0;
        grant_found = 1'b0;
        grant_idx = '0;
        if (req_valid[0]) begin
            req_masked[0] = 1'b1; grant_idx = 0; grant_found = 1'b1;
        end else if (req_valid[1]) begin
            req_masked[1] = 1'b1; grant_idx = 1; grant_found = 1'b1;
        end else if (req_valid[2]) begin
            req_masked[2] = 1'b1; grant_idx = 2; grant_found = 1'b1;
        end else if (req_valid[3]) begin
            req_masked[3] = 1'b1; grant_idx = 3; grant_found = 1'b1;
        end
    end

    // Slot counter increments every cycle
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            slot_counter <= '0;
        end else begin
            slot_counter <= slot_counter + 1'b1;
        end
    end

    // Round-robin pointer advances when grant is issued
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rr_ptr <= '0;
        end else if (grant_found) begin
            /* verilator lint_off WIDTHEXPAND */
            /* verilator lint_off WIDTHTRUNC */
            rr_ptr <= (grant_idx + 1) % N_REQUESTORS;
            /* verilator lint_on WIDTHTRUNC */
            /* verilator lint_on WIDTHEXPAND */
        end
    end

    // Channel assignment: deterministic based on CU ID
    // Each CU gets a dedicated virtual channel (waveguide, lambda, slot)
    always_comb begin
        logic [2:0] cu_id_0, cu_id_1, cu_id_2, cu_id_3;
        logic [2:0] wg_id_0, wg_id_1, wg_id_2, wg_id_3;
        
        cu_id_0 = req_id[0*6 +: 3]; wg_id_0 = req_id[0*6+3 +: 3];
        cu_id_1 = req_id[1*6 +: 3]; wg_id_1 = req_id[1*6+3 +: 3];
        cu_id_2 = req_id[2*6 +: 3]; wg_id_2 = req_id[2*6+3 +: 3];
        cu_id_3 = req_id[3*6 +: 3]; wg_id_3 = req_id[3*6+3 +: 3];
        
        assigned_waveguide[0*3 +: 3] = wg_id_0;
        assigned_waveguide[1*3 +: 3] = wg_id_1;
        assigned_waveguide[2*3 +: 3] = wg_id_2;
        assigned_waveguide[3*3 +: 3] = wg_id_3;
        
        /* verilator lint_off WIDTHTRUNC */
        /* verilator lint_off WIDTHEXPAND */
        assigned_lambda[0*3 +: 3] = cu_id_0 % WAVELENGTHS;
        assigned_lambda[1*3 +: 3] = cu_id_1 % WAVELENGTHS;
        assigned_lambda[2*3 +: 3] = cu_id_2 % WAVELENGTHS;
        assigned_lambda[3*3 +: 3] = cu_id_3 % WAVELENGTHS;
        // Static slot assignment based on CU ID
        assigned_slot[0*2 +: 2] = cu_id_0[1:0] % TDM_SLOTS;
        assigned_slot[1*2 +: 2] = cu_id_1[1:0] % TDM_SLOTS;
        assigned_slot[2*2 +: 2] = cu_id_2[1:0] % TDM_SLOTS;
        assigned_slot[3*2 +: 2] = cu_id_3[1:0] % TDM_SLOTS;
        /* verilator lint_on WIDTHTRUNC */
        /* verilator lint_on WIDTHEXPAND */
    end

    // Grant logic: issue grant when requestor's assigned slot matches current slot
    logic [N_REQUESTORS-1:0] slot_match;
    always_comb begin
        logic [1:0] current_slot;
        current_slot = slot_counter[1:0];
        
        slot_match[0] = (assigned_slot[0*2 +: 2] == current_slot) && req_valid[0] && req_masked[0];
        slot_match[1] = (assigned_slot[1*2 +: 2] == current_slot) && req_valid[1] && req_masked[1];
        slot_match[2] = (assigned_slot[2*2 +: 2] == current_slot) && req_valid[2] && req_masked[2];
        slot_match[3] = (assigned_slot[3*2 +: 2] == current_slot) && req_valid[3] && req_masked[3];
    end

    // Output grant signals
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            gnt_valid <= '0;
            gnt_lambda <= '0;
            gnt_slot <= '0;
            gnt_latency_ns <= '0;
            gnt_ready <= '0;
            has_assignment <= '0;
        end else begin
            gnt_valid <= slot_match;
            gnt_ready <= slot_match;
            if (slot_match[0]) begin
                gnt_lambda[0*3 +: 3] <= assigned_lambda[0*3 +: 3];
                gnt_slot[0*2 +: 2] <= assigned_slot[0*2 +: 2];
                gnt_latency_ns[0*4 +: 4] <= BASE_LATENCY_NS[3:0] + (assigned_slot[0*2 +: 2] * SLOT_NS[3:0]);
                has_assignment[0] <= 1'b1;
            end else has_assignment[0] <= 1'b0;
            
            if (slot_match[1]) begin
                gnt_lambda[1*3 +: 3] <= assigned_lambda[1*3 +: 3];
                gnt_slot[1*2 +: 2] <= assigned_slot[1*2 +: 2];
                gnt_latency_ns[1*4 +: 4] <= BASE_LATENCY_NS[3:0] + (assigned_slot[1*2 +: 2] * SLOT_NS[3:0]);
                has_assignment[1] <= 1'b1;
            end else has_assignment[1] <= 1'b0;
            
            if (slot_match[2]) begin
                gnt_lambda[2*3 +: 3] <= assigned_lambda[2*3 +: 3];
                gnt_slot[2*2 +: 2] <= assigned_slot[2*2 +: 2];
                gnt_latency_ns[2*4 +: 4] <= BASE_LATENCY_NS[3:0] + (assigned_slot[2*2 +: 2] * SLOT_NS[3:0]);
                has_assignment[2] <= 1'b1;
            end else has_assignment[2] <= 1'b0;
            
            if (slot_match[3]) begin
                gnt_lambda[3*3 +: 3] <= assigned_lambda[3*3 +: 3];
                gnt_slot[3*2 +: 2] <= assigned_slot[3*2 +: 2];
                gnt_latency_ns[3*4 +: 4] <= BASE_LATENCY_NS[3:0] + (assigned_slot[3*2 +: 2] * SLOT_NS[3:0]);
                has_assignment[3] <= 1'b1;
            end else has_assignment[3] <= 1'b0;
        end
    end

    // Active count and bus busy
    always_comb begin
        logic [$clog2(N_REQUESTORS):0] count;
        count = '0;
        /* verilator lint_off WIDTHEXPAND */
        count = count + (gnt_valid[0] || has_assignment[0]);
        count = count + (gnt_valid[1] || has_assignment[1]);
        count = count + (gnt_valid[2] || has_assignment[2]);
        count = count + (gnt_valid[3] || has_assignment[3]);
        /* verilator lint_on WIDTHEXPAND */
        active_count = count;
        bus_busy = |gnt_valid || |has_assignment;
    end

endmodule