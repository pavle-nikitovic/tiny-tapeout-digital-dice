`default_nettype none

// 64-bit maximal-length Galois LFSR with a transactional 32-bit interface.
//
// One accepted request (next_i && ready_o) advances the LFSR 32 times and
// returns exactly one 32-bit word.  Each output bit is taken from state[0]
// before the corresponding state transition.  The first generated bit is
// stored in random_o[0], matching the LSB-first Python reference model.
module lfsr64_core #(
    // Must be nonzero; the all-zero LFSR state is intentionally not repaired.
    parameter [63:0] RESET_STATE = 64'h0123_4567_89AB_CDEF
)(
    input  wire        clk_i,
    input  wire        rst_ni,

    input  wire        next_i,
    output wire        ready_o,

    output reg  [31:0] random_o,
    output reg         valid_o
);

    // Right-shifting Galois form of:
    //     x^64 + x^63 + x^61 + x^60 + 1
    localparam [63:0] LFSR_MASK = 64'hD800_0000_0000_0000;

    reg [63:0] state_reg;
    reg [31:0] partial_word_reg;
    reg  [4:0] steps_left_reg;
    reg        busy_reg;

    // A request may be accepted only while the core is idle and out of reset.
    assign ready_o = rst_ni && !busy_reg;

    // One bit-exact Galois LFSR transition.  The XOR mask is applied only
    // when the outgoing LSB is one, exactly as in lfsr64_core.py.
    function [63:0] lfsr_step;
        input [63:0] current_state;
        begin
            lfsr_step = {1'b0, current_state[63:1]}
                        ^ ({64{current_state[0]}} & LFSR_MASK);
        end
    endfunction

    always @(posedge clk_i) begin
        if (!rst_ni) begin
            state_reg        <= RESET_STATE;
            partial_word_reg <= 32'b0;
            steps_left_reg   <= 5'd0;
            busy_reg         <= 1'b0;
            random_o         <= 32'b0;
            valid_o          <= 1'b0;
        end else begin
            // valid_o marks only cycles in which a new word is completed.
            valid_o <= 1'b0;

            if (busy_reg) begin
                // Shift the next bit into bit 31.  After all 32 steps, the
                // first generated bit has moved to bit 0 and the final bit is
                // at bit 31, which implements the agreed LSB-first packing.
                partial_word_reg <= {state_reg[0], partial_word_reg[31:1]};
                state_reg        <= lfsr_step(state_reg);

                if (steps_left_reg == 5'd1) begin
                    // partial_word_reg is updated nonblockingly on this edge,
                    // so form random_o explicitly with the final bit.
                    random_o       <= {state_reg[0], partial_word_reg[31:1]};
                    valid_o        <= 1'b1;
                    busy_reg       <= 1'b0;
                    steps_left_reg <= 5'd0;
                end else begin
                    steps_left_reg <= steps_left_reg - 5'd1;
                end
            end else if (next_i && ready_o) begin
                // The acceptance edge performs step 1 of 32 immediately.
                // The first bit enters at bit 31 and shifts down to bit 0
                // during the remaining 31 steps.
                partial_word_reg <= {state_reg[0], 31'b0};
                state_reg        <= lfsr_step(state_reg);
                steps_left_reg   <= 5'd31;
                busy_reg         <= 1'b1;
            end
        end
    end

endmodule

`default_nettype wire
