#!/usr/bin/env python3
"""Functional verification of lfsr64_core.py.

Run with:
    python test_lfsr64_core.py

No third-party packages are required.
"""

from __future__ import annotations

import itertools
import struct
import unittest

from lfsr64_core import (
    DEFAULT_INITIAL_STATE,
    GALOIS_MASK,
    OUTPUT_BITS,
    OUTPUT_MASK,
    STATE_BITS,
    STATE_MASK,
    LFSR64,
    lfsr64_next,
    step_bit,
    step_u32,
)


GOLDEN_BIT_TRANSITIONS = (
    (0x0123_4567_89AB_CDEF, 1, 0xD891_A2B3_C4D5_E6F7),
    (0xD891_A2B3_C4D5_E6F7, 1, 0xB448_D159_E26A_F37B),
    (0xB448_D159_E26A_F37B, 1, 0x8224_68AC_F135_79BD),
    (0x8224_68AC_F135_79BD, 1, 0x9912_3456_789A_BCDE),
)

GOLDEN_WORD_TRANSITIONS = (
    (0x0123_4567_89AB_CDEF, 0x89AB_CDEF, 0xD4D1_EE7B_9123_4567),
    (0xD4D1_EE7B_9123_4567, 0x9123_4567, 0xC284_BB2E_C4D1_EE7B),
    (0xC284_BB2E_C4D1_EE7B, 0xC4D1_EE7B, 0xB26E_3A6E_9284_BB2E),
    (0xB26E_3A6E_9284_BB2E, 0x9284_BB2E, 0xC0BE_3A6E_926E_3A6E),
    (0xC0BE_3A6E_926E_3A6E, 0x926E_3A6E, 0xC032_03B2_E0BE_3A6E),
    (0xC032_03B2_E0BE_3A6E, 0xE0BE_3A6E, 0x82FD_03B2_E032_03B2),
    (0x82FD_03B2_E032_03B2, 0xE032_03B2, 0x822E_6226_E2FD_03B2),
    (0x822E_6226_E2FD_03B2, 0xE2FD_03B2, 0x81F3_F226_E22E_6226),
)

CHARACTERISTIC_STATES = (
    0x0000_0000_0000_0001,
    0x8000_0000_0000_0000,
    0xFFFF_FFFF_FFFF_FFFF,
    0xAAAA_AAAA_AAAA_AAAA,
    0x5555_5555_5555_5555,
    DEFAULT_INITIAL_STATE,
)


def reference_next_u32(state: int) -> tuple[int, int]:
    """Literal 32-step definition used only as an independent test oracle."""

    word = 0
    work_state = state

    for bit_index in range(OUTPUT_BITS):
        serial_bit = work_state & 1
        word |= serial_bit << bit_index
        work_state = (work_state >> 1) ^ (
            GALOIS_MASK if serial_bit else 0
        )

    return word & OUTPUT_MASK, work_state & STATE_MASK


class ConstantsTests(unittest.TestCase):
    def test_locked_constants(self) -> None:
        self.assertEqual(STATE_BITS, 64)
        self.assertEqual(OUTPUT_BITS, 32)
        self.assertEqual(STATE_MASK, 0xFFFF_FFFF_FFFF_FFFF)
        self.assertEqual(OUTPUT_MASK, 0xFFFF_FFFF)
        self.assertEqual(GALOIS_MASK, 0xD800_0000_0000_0000)
        self.assertEqual(DEFAULT_INITIAL_STATE, 0x0123_4567_89AB_CDEF)


class PureTransitionTests(unittest.TestCase):
    def test_elementary_golden_transitions(self) -> None:
        for old_state, expected_bit, expected_state in GOLDEN_BIT_TRANSITIONS:
            with self.subTest(old_state=f"0x{old_state:016X}"):
                bit, new_state = step_bit(old_state)
                self.assertEqual(bit, expected_bit)
                self.assertEqual(new_state, expected_state)

    def test_elementary_even_state_has_no_feedback(self) -> None:
        old_state = 0x8000_0000_0000_0002
        self.assertEqual(step_bit(old_state), (0, old_state >> 1))

    def test_elementary_odd_state_applies_feedback_mask(self) -> None:
        self.assertEqual(step_bit(1), (1, GALOIS_MASK))

    def test_word_golden_transitions(self) -> None:
        for old_state, expected_word, expected_state in GOLDEN_WORD_TRANSITIONS:
            with self.subTest(old_state=f"0x{old_state:016X}"):
                word, new_state = step_u32(old_state)
                self.assertEqual(word, expected_word)
                self.assertEqual(new_state, expected_state)

    def test_word_is_exactly_32_serial_steps(self) -> None:
        for state in CHARACTERISTIC_STATES:
            with self.subTest(state=f"0x{state:016X}"):
                self.assertEqual(step_u32(state), reference_next_u32(state))

    def test_all_one_hot_states_match_literal_transition(self) -> None:
        for bit_index in range(STATE_BITS):
            state = 1 << bit_index
            with self.subTest(bit_index=bit_index):
                self.assertEqual(step_u32(state), reference_next_u32(state))

    def test_10000_states_match_literal_transition(self) -> None:
        state = DEFAULT_INITIAL_STATE

        for index in range(10_000):
            state = (
                state * 0x5851_F42D_4C95_7F2D + 0x1405_7B7E_F767_814F
            ) & STATE_MASK
            if state == 0:
                state = 1

            with self.subTest(index=index, state=f"0x{state:016X}"):
                self.assertEqual(step_u32(state), reference_next_u32(state))

    def test_descriptive_alias_matches_common_api(self) -> None:
        self.assertEqual(
            lfsr64_next(DEFAULT_INITIAL_STATE),
            step_u32(DEFAULT_INITIAL_STATE),
        )
        self.assertEqual(
            LFSR64.step_u32(DEFAULT_INITIAL_STATE),
            step_u32(DEFAULT_INITIAL_STATE),
        )

    def test_temporal_bit_order_is_lsb_first(self) -> None:
        word, _ = step_u32(DEFAULT_INITIAL_STATE)
        expected_bits = []
        state = DEFAULT_INITIAL_STATE

        for _ in range(OUTPUT_BITS):
            bit, state = step_bit(state)
            expected_bits.append(bit)

        observed_bits = [(word >> index) & 1 for index in range(OUTPUT_BITS)]
        self.assertEqual(observed_bits, expected_bits)


class StatefulModelTests(unittest.TestCase):
    def test_default_state_and_first_word(self) -> None:
        generator = LFSR64()
        self.assertEqual(generator.get_state(), DEFAULT_INITIAL_STATE)
        self.assertEqual(generator.next_u32(), 0x89AB_CDEF)
        self.assertEqual(generator.get_state(), 0xD4D1_EE7B_9123_4567)

    def test_next_u32_follows_all_golden_vectors(self) -> None:
        generator = LFSR64()

        for old_state, expected_word, expected_state in GOLDEN_WORD_TRANSITIONS:
            with self.subTest(old_state=f"0x{old_state:016X}"):
                self.assertEqual(generator.get_state(), old_state)
                self.assertEqual(generator.next_u32(), expected_word)
                self.assertEqual(generator.get_state(), expected_state)

    def test_custom_initial_state_is_loaded_directly(self) -> None:
        generator = LFSR64(initial_state=0xFFFF_FFFF_FFFF_FFFF)
        self.assertEqual(generator.get_state(), 0xFFFF_FFFF_FFFF_FFFF)
        self.assertEqual(
            generator.next_u32(),
            step_u32(0xFFFF_FFFF_FFFF_FFFF)[0],
        )

    def test_load_state_and_fixed_reset(self) -> None:
        generator = LFSR64()
        generator.load_state(0xAAAA_AAAA_AAAA_AAAA)
        self.assertEqual(generator.get_state(), 0xAAAA_AAAA_AAAA_AAAA)

        generator.reset()
        self.assertEqual(generator.get_state(), DEFAULT_INITIAL_STATE)

    def test_reset_is_fixed_after_custom_construction(self) -> None:
        generator = LFSR64(0xFFFF_FFFF_FFFF_FFFF)
        generator.reset()
        self.assertEqual(generator.get_state(), DEFAULT_INITIAL_STATE)

    def test_failed_loads_do_not_change_state(self) -> None:
        generator = LFSR64()
        invalid_states = (0, -1, 1 << STATE_BITS, True, False, 1.5, "1", None)

        for state in invalid_states:
            with self.subTest(state=state):
                state_before = generator.get_state()
                with self.assertRaises((TypeError, ValueError)):
                    generator.load_state(state)  # type: ignore[arg-type]
                self.assertEqual(generator.get_state(), state_before)

    def test_generate_and_iter_u32_preserve_sequence_continuity(self) -> None:
        expected_generator = LFSR64()
        expected = [expected_generator.next_u32() for _ in range(19)]

        generated = LFSR64()
        generated_words = generated.generate(7) + generated.generate(12)

        iterated = LFSR64()
        iterated_words = list(iterated.iter_u32(19))

        self.assertEqual(generated_words, expected)
        self.assertEqual(iterated_words, expected)
        self.assertEqual(generated.get_state(), expected_generator.get_state())
        self.assertEqual(iterated.get_state(), expected_generator.get_state())

    def test_unbounded_iterator_continues_same_sequence(self) -> None:
        expected = LFSR64().generate(19)
        observed = list(itertools.islice(LFSR64().iter_u32(), 19))
        self.assertEqual(observed, expected)

    def test_zero_length_requests_do_not_change_state(self) -> None:
        generator = LFSR64()
        state_before = generator.get_state()

        self.assertEqual(generator.generate(0), [])
        self.assertEqual(list(generator.iter_u32(0)), [])
        self.assertEqual(generator.get_state(), state_before)

    def test_little_endian_stream_convention(self) -> None:
        words = LFSR64().generate(2)
        packed = struct.pack("<2I", *words)
        self.assertEqual(packed, bytes.fromhex("EF CD AB 89 67 45 23 91"))

    def test_repr_shows_full_raw_state(self) -> None:
        self.assertEqual(
            repr(LFSR64()),
            "LFSR64(state=0x0123456789ABCDEF)",
        )


class InputValidationTests(unittest.TestCase):
    def test_invalid_states_are_rejected(self) -> None:
        invalid_states = (0, -1, 1 << STATE_BITS, True, False, 1.5, "1", None)

        for state in invalid_states:
            with self.subTest(state=state):
                with self.assertRaises((TypeError, ValueError)):
                    LFSR64(state)  # type: ignore[arg-type]
                with self.assertRaises((TypeError, ValueError)):
                    step_bit(state)  # type: ignore[arg-type]
                with self.assertRaises((TypeError, ValueError)):
                    step_u32(state)  # type: ignore[arg-type]

    def test_invalid_finite_counts_are_rejected(self) -> None:
        for count in (-1, True, 1.5, "1", None):
            with self.subTest(count=count):
                with self.assertRaises((TypeError, ValueError)):
                    LFSR64().generate(count)  # type: ignore[arg-type]

    def test_invalid_iterator_counts_are_rejected_on_iteration(self) -> None:
        for count in (-1, True, 1.5, "1"):
            with self.subTest(count=count):
                with self.assertRaises((TypeError, ValueError)):
                    next(LFSR64().iter_u32(count))  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main(verbosity=2)
