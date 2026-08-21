`default_nettype none

// Bit-exact xoroshiro64** 1.0 core with a transactional 32-bit interface.
//
// The packed 64-bit state uses the same convention as xoroshiro64ss_core.py:
//     state[63:32] = s0
//     state[31:0]  = s1
//
// One accepted request (next_i && ready_o) returns one 32-bit word computed
// from the old s0 value and advances the 64-bit state exactly once.  The core
// can accept one request per clock while next_i remains asserted.
module xoroshiro64ss_core #(
    // Must be nonzero; the forbidden all-zero state is not repaired in RTL.
    parameter [63:0] RESET_STATE = 64'h0123_4567_89AB_CDEF
)(
    input  wire        clk_i,
    input  wire        rst_ni,

    input  wire        next_i,
    output wire        ready_o,

    output reg  [31:0] random_o,
    output reg         valid_o
);

    localparam [31:0] STARSTAR_MULTIPLIER = 32'h9E37_79BB;

    reg  [63:0] state_reg;

    wire [31:0] s0_wire;
    wire [31:0] s1_wire;
    wire [31:0] product_wire;
    wire [31:0] rotated_product_wire;
    wire [31:0] output_word_wire;
    wire [31:0] xor_state_wire;
    wire [31:0] next_s0_wire;
    wire [31:0] next_s1_wire;

    assign s0_wire = state_reg[63:32];
    assign s1_wire = state_reg[31:0];

    // xoroshiro64** output function, evaluated from the old s0:
    //     rotl32(s0 * 0x9E3779BB, 5) * 5  (modulo 2^32)
    // Assigning the product to 32 bits intentionally keeps its low 32 bits.
    assign product_wire = s0_wire * STARSTAR_MULTIPLIER;
    assign rotated_product_wire = {
        product_wire[26:0], product_wire[31:27]
    };

    // Multiplication by five modulo 2^32, expressed as shift-and-add so that
    // synthesis does not infer a second general multiplier.
    assign output_word_wire = rotated_product_wire
                              + {rotated_product_wire[29:0], 2'b00};

    // xoroshiro64** 1.0 state transition:
    //     t       = s1 ^ s0
    //     new_s0  = rotl32(s0, 26) ^ t ^ (t << 9)
    //     new_s1  = rotl32(t, 13)
    assign xor_state_wire = s1_wire ^ s0_wire;
    assign next_s0_wire = {s0_wire[5:0], s0_wire[31:6]}
                          ^ xor_state_wire
                          ^ {xor_state_wire[22:0], 9'b0};
    assign next_s1_wire = {
        xor_state_wire[18:0], xor_state_wire[31:19]
    };

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
                state_reg <= {next_s0_wire, next_s1_wire};
                valid_o   <= 1'b1;
            end
        end
    end

endmodule

`default_nettype wire
