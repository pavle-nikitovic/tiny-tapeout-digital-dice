`default_nettype none

// Bit-exact PCG-XSH-RR 64/32 (one-sequence) core with a transactional
// 32-bit interface.
//
// RESET_STATE is interpreted directly as the raw 64-bit internal state.
// There is no seed transformation or warm-up step, and the all-zero state is
// valid.  One accepted request (next_i && ready_o) returns one 32-bit word
// computed from the old state and advances the 64-bit LCG state exactly once.
// The core can accept one request per clock while next_i remains asserted.
module pcg32_oneseq_core #(
    parameter [63:0] RESET_STATE = 64'h0123_4567_89AB_CDEF
)(
    input  wire        clk_i,
    input  wire        rst_ni,

    input  wire        next_i,
    output wire        ready_o,

    output reg  [31:0] random_o,
    output reg         valid_o
);

    // Fixed constants of the agreed PCG32 one-sequence LCG:
    //     new_state = old_state * MULTIPLIER + INCREMENT (modulo 2^64)
    localparam [63:0] LCG_MULTIPLIER = 64'h5851_F42D_4C95_7F2D;
    localparam [63:0] LCG_INCREMENT  = 64'h1405_7B7E_F767_814F;

    reg [63:0] state_reg;

    wire [63:0] xorshift_value_wire;
    wire [31:0] xorshifted_wire;
    wire  [4:0] rotation_wire;
    wire [63:0] rotated_double_wire;
    wire [31:0] output_word_wire;
    wire [63:0] product_low_wire;
    wire [63:0] next_state_wire;

    // PCG XSH-RR output permutation, evaluated from the old state:
    //     xorshifted = (((state >> 18) ^ state) >> 27) & 0xFFFF_FFFF
    //     rotation   = state >> 59
    //     output     = rotr32(xorshifted, rotation)
    assign xorshift_value_wire = (state_reg >> 6'd18) ^ state_reg;

    // The low 32 bits after the 27-bit right shift are bits [58:27] of the
    // value before that shift.  Selecting them explicitly makes truncation to
    // 32 bits independent of expression-width rules.
    assign xorshifted_wire = xorshift_value_wire[58:27];
    assign rotation_wire   = state_reg[63:59];

    // Duplicating the word implements a fully defined 32-bit rotate-right:
    // the low 32 bits of ({x, x} >> r) equal rotr32(x, r) for r = 0..31.
    assign rotated_double_wire = {xorshifted_wire, xorshifted_wire}
                                 >> rotation_wire;
    assign output_word_wire = rotated_double_wire[31:0];

    // Keeping only the low 64 product bits, then keeping only the low 64 sum
    // bits, implements the Python model's two modulo-2^64 operations.
    assign product_low_wire = state_reg * LCG_MULTIPLIER;
    assign next_state_wire  = product_low_wire + LCG_INCREMENT;

    // This generator completes one transition per accepted request, so it is
    // ready in every non-reset cycle and can produce back-to-back valid words.
    assign ready_o = rst_ni;

    always @(posedge clk_i) begin
        if (!rst_ni) begin
            state_reg <= RESET_STATE;
            random_o  <= 32'b0;
            valid_o   <= 1'b0;
        end else begin
            // valid_o is low when no new word is produced.  With next_i held
            // high it is also allowed to remain high across consecutive words.
            valid_o <= 1'b0;

            if (next_i && ready_o) begin
                // Both values on the right are derived from the old state_reg.
                random_o  <= output_word_wire;
                state_reg <= next_state_wire;
                valid_o   <= 1'b1;
            end
        end
    end

endmodule

`default_nettype wire
