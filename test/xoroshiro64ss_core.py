"""Bit-exact reference model of xoroshiro64** 1.0.

The 64-bit state is packed as::

    state[63:32] = s0
    state[31:0]  = s1

The all-zero state is forbidden.  Each call to ``next_u32()`` returns one
32-bit output computed from the old state and then advances the state once.
"""

MASK32 = 0xFFFF_FFFF
MASK64 = 0xFFFF_FFFF_FFFF_FFFF

DEFAULT_SEED = 0x0123_4567_89AB_CDEF
STARSTAR_MULTIPLIER = 0x9E37_79BB


def _validate_state(state):
    """Validate and return a raw, nonzero 64-bit state."""
    if not isinstance(state, int) or isinstance(state, bool):
        raise TypeError("state must be an integer")
    if not 0 <= state <= MASK64:
        raise ValueError("state must fit in 64 bits")
    if state == 0:
        raise ValueError("the all-zero state is not allowed")
    return state


def _rotl32(value, amount):
    """Rotate a 32-bit value left by ``amount`` positions."""
    value &= MASK32
    return ((value << amount) | (value >> (32 - amount))) & MASK32


def xoroshiro64ss_next(old_state):
    """Return ``(output_word, new_state)`` for one generator transition.

    ``old_state`` is a directly packed 64-bit xoroshiro64** state.  The output
    is calculated from the old ``s0`` value, exactly as in the reference C
    implementation, before the next state is formed.
    """
    old_state = _validate_state(old_state)

    s0 = (old_state >> 32) & MASK32
    s1 = old_state & MASK32

    product = (s0 * STARSTAR_MULTIPLIER) & MASK32
    output_word = (_rotl32(product, 5) * 5) & MASK32

    t = (s1 ^ s0) & MASK32
    new_s0 = (_rotl32(s0, 26) ^ t ^ ((t << 9) & MASK32)) & MASK32
    new_s1 = _rotl32(t, 13)
    new_state = ((new_s0 << 32) | new_s1) & MASK64

    return output_word, new_state


class Xoroshiro64SS:
    """Stateful xoroshiro64** 1.0 reference model."""

    def __init__(self, seed=DEFAULT_SEED):
        seed = _validate_state(seed)
        self._reset_seed = seed
        self._state = seed

    def next_u32(self):
        """Return one 32-bit output and advance the state once."""
        output_word, self._state = xoroshiro64ss_next(self._state)
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
        """Return the current packed 64-bit state."""
        return self._state
