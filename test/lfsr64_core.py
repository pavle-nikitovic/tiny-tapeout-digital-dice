#!/usr/bin/env python3
"""Pure bit-exact model of the agreed 64-bit Galois LFSR.

Algorithm conventions:
    * 64-bit unsigned state
    * right shift
    * old state bit 0 is the serial output bit
    * Galois feedback mask 0xD800000000000000
    * one 32-bit word contains 32 consecutive serial bits
    * the first generated bit is placed in output bit 0 (LSB-first)
    * the state advances by exactly 32 elementary steps per output word

The module contains only the generator model.  It has no command-line entry
point, stored reference vectors, self-checks, or statistical tests.
"""

from __future__ import annotations

from typing import Iterator, List, Optional, Tuple


STATE_BITS = 64
OUTPUT_BITS = 32

STATE_MASK = (1 << STATE_BITS) - 1
OUTPUT_MASK = (1 << OUTPUT_BITS) - 1

GALOIS_MASK = 0xD800_0000_0000_0000
DEFAULT_INITIAL_STATE = 0x0123_4567_89AB_CDEF


def _validate_state(state: int) -> int:
    """Validate and return a non-zero raw 64-bit LFSR state."""

    if isinstance(state, bool) or not isinstance(state, int):
        raise TypeError("state must be a Python int")
    if state == 0:
        raise ValueError("state 0 is forbidden for this XOR LFSR")
    if state < 0 or state > STATE_MASK:
        raise ValueError("state must be in the range 1 .. 2**64 - 1")
    return state


def _validate_word_count(word_count: Optional[int]) -> Optional[int]:
    """Validate a non-negative count; None selects an endless iterator."""

    if word_count is None:
        return None
    if isinstance(word_count, bool) or not isinstance(word_count, int):
        raise TypeError("word_count must be a Python int or None")
    if word_count < 0:
        raise ValueError("word_count must be non-negative")
    return word_count


def step_bit(state: int) -> Tuple[int, int]:
    """Generate one serial bit and advance the LFSR by one step.

    Returns ``(serial_bit, next_state)``.  The serial bit is the old LSB.
    This function is pure: it does not modify any generator object.
    """

    state = _validate_state(state)
    serial_bit = state & 1
    next_state = (state >> 1) ^ (GALOIS_MASK if serial_bit else 0)
    return serial_bit, next_state & STATE_MASK


def _step_u32_unchecked(state: int) -> Tuple[int, int]:
    """Fast 32-step transition for an already validated state."""

    # For the locked mask, feedback inserted during these 32 steps cannot
    # reach bit 0.  Therefore the 32 serial bits are exactly the old lower
    # 32 state bits, in the required temporal LSB-first order.
    word = state & OUTPUT_MASK

    # This is the closed form of 32 applications of step_bit().  It retains
    # fixed-width 64-bit behaviour and is convenient for long output streams.
    next_state = (
        (state >> 32)
        ^ (word << 32)
        ^ (word << 31)
        ^ (word << 29)
        ^ (word << 28)
    ) & STATE_MASK

    return word, next_state


def step_u32(state: int) -> Tuple[int, int]:
    """Return one 32-bit output word and the state after 32 LFSR steps.

    The returned word is formed from the old state.  Output bit ``i`` is the
    serial bit generated in elementary step ``i``.  The function is pure and
    returns ``(word, next_state)``.
    """

    return _step_u32_unchecked(_validate_state(state))


def lfsr64_next(state: int) -> Tuple[int, int]:
    """Descriptive alias for the pure 32-bit transition."""

    return step_u32(state)


class LFSR64:
    """Stateful wrapper around the pure bit-exact LFSR transition.

    ``initial_state`` is loaded directly into the 64-bit state register.  It
    is not hashed, expanded, or warmed up.  Calling :meth:`reset` always
    restores the fixed reset state used by the planned RTL implementation.
    """

    __slots__ = ("_state",)

    def __init__(self, initial_state: int = DEFAULT_INITIAL_STATE) -> None:
        self._state = _validate_state(initial_state)

    def get_state(self) -> int:
        """Return the current raw 64-bit state."""

        return self._state

    def load_state(self, state: int) -> None:
        """Load a new non-zero raw 64-bit state."""

        self._state = _validate_state(state)

    def reset(self) -> None:
        """Restore the fixed default reset state."""

        self._state = DEFAULT_INITIAL_STATE

    @staticmethod
    def step_u32(state: int) -> Tuple[int, int]:
        """Expose the pure transition through the shared class API."""

        return step_u32(state)

    def next_u32(self) -> int:
        """Return the next 32-bit word and advance the internal state."""

        word, self._state = _step_u32_unchecked(self._state)
        return word

    def generate(self, word_count: int) -> List[int]:
        """Return exactly ``word_count`` consecutive output words."""

        checked_count = _validate_word_count(word_count)
        if checked_count is None:
            raise TypeError("word_count must be a Python int")
        return [self.next_u32() for _ in range(checked_count)]

    def iter_u32(self, word_count: Optional[int] = None) -> Iterator[int]:
        """Yield a finite number of words, or endlessly when count is None."""

        checked_count = _validate_word_count(word_count)

        if checked_count is None:
            while True:
                yield self.next_u32()
        else:
            for _ in range(checked_count):
                yield self.next_u32()

    def __repr__(self) -> str:
        return f"LFSR64(state=0x{self._state:016X})"
