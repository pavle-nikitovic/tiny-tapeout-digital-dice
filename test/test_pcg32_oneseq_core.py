"""Tests for the bit-exact PCG32 one-sequence reference model.

The file can be run directly with::

    python test_pcg32_oneseq_core.py

Its ``test_*`` functions can also be collected with ``pytest``.
"""

from pcg32_oneseq_core import (
    DEFAULT_SEED,
    INCREMENT,
    MASK32,
    MASK64,
    MULTIPLIER,
    PCG32OneSeq,
    pcg32_oneseq_next,
)


GOLDEN_VECTORS = [
    (0x2468_A5EB, 0x2CE3_2D23_35DF_4552),
    (0xFCE3_261B, 0xCA18_DD5A_E3C4_5EB9),
    (0x8EFD_CD21, 0x860F_5366_7996_EED4),
    (0x5CB5_C1EE, 0xE212_99D8_28CE_A893),
    (0x2542_B914, 0xC60C_9AE7_6AEB_1026),
]


def _expect_exception(exception_type, function, *args):
    try:
        function(*args)
    except exception_type:
        return
    except Exception as error:
        raise AssertionError(
            f"expected {exception_type.__name__}, "
            f"got {type(error).__name__}"
        ) from error

    raise AssertionError(f"expected {exception_type.__name__}")


def test_constants_and_default_seed_match_the_agreed_pcg_variant():
    assert DEFAULT_SEED == 0x0123_4567_89AB_CDEF
    assert MULTIPLIER == 0x5851_F42D_4C95_7F2D
    assert INCREMENT == 0x1405_7B7E_F767_814F
    assert 0 <= DEFAULT_SEED <= MASK64


def test_pure_function_matches_golden_vectors():
    state = DEFAULT_SEED

    for index, expected in enumerate(GOLDEN_VECTORS, start=1):
        actual = pcg32_oneseq_next(state)
        assert actual == expected, (
            f"golden vector {index} failed: "
            f"output=0x{actual[0]:08X}, state=0x{actual[1]:016X}"
        )
        state = actual[1]


def test_class_matches_golden_vectors_and_updates_state_after_each_output():
    generator = PCG32OneSeq()

    for expected_word, expected_state in GOLDEN_VECTORS:
        assert generator.next_u32() == expected_word
        assert generator.get_state() == expected_state


def test_generate_matches_repeated_next_u32_calls():
    count = 100
    generator_a = PCG32OneSeq()
    generator_b = PCG32OneSeq()

    expected = [generator_a.next_u32() for _ in range(count)]
    assert generator_b.generate(count) == expected
    assert generator_b.get_state() == generator_a.get_state()


def test_generate_zero_returns_empty_list_without_changing_state():
    generator = PCG32OneSeq()
    state_before = generator.get_state()

    assert generator.generate(0) == []
    assert generator.get_state() == state_before


def test_sequence_continues_correctly_across_separate_generate_calls():
    generator_a = PCG32OneSeq()
    generator_b = PCG32OneSeq()

    split_sequence = generator_a.generate(37) + generator_a.generate(63)
    assert split_sequence == generator_b.generate(100)
    assert generator_a.get_state() == generator_b.get_state()


def test_load_state_changes_current_state_and_reset_restores_constructor_seed():
    constructor_seed = 0x1357_9BDF_2468_ACE0
    loaded_state = 0xFEDC_BA98_7654_3210
    generator = PCG32OneSeq(constructor_seed)

    generator.load_state(loaded_state)
    assert generator.get_state() == loaded_state

    expected_word, expected_next_state = pcg32_oneseq_next(loaded_state)
    assert generator.next_u32() == expected_word
    assert generator.get_state() == expected_next_state

    generator.reset()
    assert generator.get_state() == constructor_seed

    expected_word, expected_next_state = pcg32_oneseq_next(constructor_seed)
    assert generator.next_u32() == expected_word
    assert generator.get_state() == expected_next_state


def test_zero_state_is_valid_reachable_and_advances_by_the_fixed_increment():
    predecessor_of_zero = 0x9995_B5B6_2153_5015
    output_word, new_state = pcg32_oneseq_next(predecessor_of_zero)
    assert output_word == 0x4F4D_2656
    assert new_state == 0

    output_word, new_state = pcg32_oneseq_next(0)
    assert output_word == 0x0000_0000
    assert new_state == INCREMENT

    generator = PCG32OneSeq(0)
    assert generator.get_state() == 0
    assert generator.next_u32() == 0
    assert generator.get_state() == INCREMENT

    generator.reset()
    assert generator.get_state() == 0


def test_xsh_rr_rotation_and_fixed_width_boundary_vectors():
    boundary_vectors = [
        (0x0000_0000_0000_0001, 0x0000_0000, 0x6C57_6FAC_43FD_007C),
        (0x0800_0000_0000_0000, 0x0000_2000, 0x7C05_7B7E_F767_814F),
        (0x8000_0000_0000_0000, 0x0000_0004, 0x9405_7B7E_F767_814F),
        (0xFFFF_FFFF_FFFF_FFFF, 0xFFF0_0001, 0xBBB3_8751_AAD2_0222),
    ]

    for old_state, expected_word, expected_state in boundary_vectors:
        word, new_state = pcg32_oneseq_next(old_state)
        assert word == expected_word
        assert new_state == expected_state
        assert 0 <= word <= MASK32
        assert 0 <= new_state <= MASK64


def test_lcg_constants_satisfy_the_full_period_conditions():
    assert INCREMENT & 1 == 1
    assert MULTIPLIER & 3 == 1


def test_two_instances_are_independent():
    generator_a = PCG32OneSeq()
    generator_b = PCG32OneSeq()

    generator_a.next_u32()
    assert generator_a.get_state() != generator_b.get_state()
    assert generator_b.get_state() == DEFAULT_SEED


def test_all_64_bit_boundary_states_are_allowed():
    for valid_state in (0, 1, 1 << 63, MASK64):
        generator = PCG32OneSeq(valid_state)
        word = generator.next_u32()
        assert 0 <= word <= MASK32
        assert 0 <= generator.get_state() <= MASK64


def test_out_of_range_states_are_rejected_without_changing_current_state():
    for invalid_state in (-1, MASK64 + 1):
        _expect_exception(ValueError, PCG32OneSeq, invalid_state)
        _expect_exception(ValueError, pcg32_oneseq_next, invalid_state)

        generator = PCG32OneSeq()
        state_before = generator.get_state()
        _expect_exception(ValueError, generator.load_state, invalid_state)
        assert generator.get_state() == state_before


def test_noninteger_states_are_rejected_without_changing_current_state():
    for invalid_state in (None, 1.5, "1", True):
        _expect_exception(TypeError, PCG32OneSeq, invalid_state)
        _expect_exception(TypeError, pcg32_oneseq_next, invalid_state)

        generator = PCG32OneSeq()
        state_before = generator.get_state()
        _expect_exception(TypeError, generator.load_state, invalid_state)
        assert generator.get_state() == state_before


def test_generate_rejects_invalid_counts_without_changing_state():
    for invalid_count in (-1, -100):
        generator = PCG32OneSeq()
        state_before = generator.get_state()
        _expect_exception(ValueError, generator.generate, invalid_count)
        assert generator.get_state() == state_before

    for invalid_count in (None, 1.5, "10", True):
        generator = PCG32OneSeq()
        state_before = generator.get_state()
        _expect_exception(TypeError, generator.generate, invalid_count)
        assert generator.get_state() == state_before


def test_long_sequence_stays_within_fixed_widths():
    generator = PCG32OneSeq()

    for _ in range(10_000):
        word = generator.next_u32()
        assert 0 <= word <= MASK32
        assert 0 <= generator.get_state() <= MASK64


def main():
    test_constants_and_default_seed_match_the_agreed_pcg_variant()
    test_pure_function_matches_golden_vectors()
    test_class_matches_golden_vectors_and_updates_state_after_each_output()
    test_generate_matches_repeated_next_u32_calls()
    test_generate_zero_returns_empty_list_without_changing_state()
    test_sequence_continues_correctly_across_separate_generate_calls()
    test_load_state_changes_current_state_and_reset_restores_constructor_seed()
    test_zero_state_is_valid_reachable_and_advances_by_the_fixed_increment()
    test_xsh_rr_rotation_and_fixed_width_boundary_vectors()
    test_lcg_constants_satisfy_the_full_period_conditions()
    test_two_instances_are_independent()
    test_all_64_bit_boundary_states_are_allowed()
    test_out_of_range_states_are_rejected_without_changing_current_state()
    test_noninteger_states_are_rejected_without_changing_current_state()
    test_generate_rejects_invalid_counts_without_changing_state()
    test_long_sequence_stays_within_fixed_widths()

    print("All PCG32-oneseq core tests passed.")


if __name__ == "__main__":
    main()
