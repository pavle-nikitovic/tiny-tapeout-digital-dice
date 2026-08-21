"""Bit-exact reference model of PCG-XSH-RR 64/32 (one-sequence).

The seed is interpreted directly as the raw 64-bit internal state.  There is
no seed transformation and no warm-up step.  The all-zero state is valid.

Each call to ``next_u32()`` returns one 32-bit output computed from the old
state and then advances the 64-bit LCG state once.
"""

MASK32 = 0xFFFF_FFFF
MASK64 = 0xFFFF_FFFF_FFFF_FFFF

DEFAULT_SEED = 0x0123_4567_89AB_CDEF
MULTIPLIER = 0x5851_F42D_4C95_7F2D
INCREMENT = 0x1405_7B7E_F767_814F


def _validate_state(state):
    """Validate and return a raw 64-bit state, including zero."""
    if not isinstance(state, int) or isinstance(state, bool):
        raise TypeError("state must be an integer")
    if not 0 <= state <= MASK64:
        raise ValueError("state must fit in 64 bits")
    return state


def _rotr32(value, amount):
    """Rotate a 32-bit value right by ``amount`` positions."""
    value &= MASK32
    amount &= 31
    return ((value >> amount) | (value << ((-amount) & 31))) & MASK32


def pcg32_oneseq_next(old_state):
    """Return ``(output_word, new_state)`` for one generator transition.

    ``old_state`` is the raw 64-bit PCG state.  The XSH-RR output and the next
    LCG state are both formed from that old state, matching the reference
    PCG32 step exactly.
    """
    old_state = _validate_state(old_state)

    xorshifted = (((old_state >> 18) ^ old_state) >> 27) & MASK32
    rotation = (old_state >> 59) & 31
    output_word = _rotr32(xorshifted, rotation)

    new_state = (old_state * MULTIPLIER + INCREMENT) & MASK64

    return output_word, new_state


class PCG32OneSeq:
    """Stateful PCG-XSH-RR 64/32 one-sequence reference model."""

    def __init__(self, seed=DEFAULT_SEED):
        seed = _validate_state(seed)
        self._reset_seed = seed
        self._state = seed

    def next_u32(self):
        """Return one 32-bit output and advance the state once."""
        output_word, self._state = pcg32_oneseq_next(self._state)
        return output_word

    def generate(self, n):
        """Return a list containing exactly ``n`` consecutive outputs."""
        if not isinstance(n, int) or isinstance(n, bool):
            raise TypeError("n must be an integer")
        if n < 0:
            raise ValueError("n must be non-negative")
        return [self.next_u32() for _ in range(n)]

    def load_state(self, state):
        """Replace the current state without changing the reset seed."""
        self._state = _validate_state(state)

    def reset(self):
        """Restore the seed supplied when this instance was constructed."""
        self._state = self._reset_seed

    def get_state(self):
        """Return the current raw 64-bit state."""
        return self._state
