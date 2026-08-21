"""Tests for the bit-exact xoroshiro64** reference model.

The file can be run directly with::

    python test_xoroshiro64ss_core.py

Its ``test_*`` functions can also be collected with ``pytest``.
"""

from xoroshiro64ss_core import (
    DEFAULT_SEED,
    MASK32,
    MASK64,
    Xoroshiro64SS,
    xoroshiro64ss_next,
)


GOLDEN_VECTORS = [
    (0x4F7C_C6BB, 0x059D_159D_1111_1111),
    (0x4E9F_2DEC, 0x7893_68DA_8091_8291),
    (0xEBA4_C742, 0x9434_31E8_5D49_7F00),
    (0x1971_CB82, 0x91B0_4E2F_A9DD_192F),
    (0x45F4_1575, 0x5C85_9638_AAE0_070D),
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


def test_default_seed_is_the_agreed_nonzero_64_bit_value():
    assert DEFAULT_SEED == 0x0123_4567_89AB_CDEF
    assert 0 < DEFAULT_SEED <= MASK64


def test_pure_function_matches_golden_vectors():
    state = DEFAULT_SEED

    for index, expected in enumerate(GOLDEN_VECTORS, start=1):
        actual = xoroshiro64ss_next(state)
        assert actual == expected, (
            f"golden vector {index} failed: "
            f"output=0x{actual[0]:08X}, state=0x{actual[1]:016X}"
        )
        state = actual[1]


def test_class_matches_golden_vectors_and_updates_state_after_each_output():
    generator = Xoroshiro64SS()

    for expected_word, expected_state in GOLDEN_VECTORS:
        assert generator.next_u32() == expected_word
        assert generator.get_state() == expected_state


def test_generate_matches_repeated_next_u32_calls():
    count = 100
    generator_a = Xoroshiro64SS()
    generator_b = Xoroshiro64SS()

    expected = [generator_a.next_u32() for _ in range(count)]
    assert generator_b.generate(count) == expected
    assert generator_b.get_state() == generator_a.get_state()


def test_generate_zero_returns_empty_list_without_changing_state():
    generator = Xoroshiro64SS()
    state_before = generator.get_state()

    assert generator.generate(0) == []
    assert generator.get_state() == state_before


def test_load_state_changes_current_state_and_reset_restores_constructor_seed():
    generator = Xoroshiro64SS(DEFAULT_SEED)
    loaded_state = 0xFEDC_BA98_7654_3210

    generator.load_state(loaded_state)
    assert generator.get_state() == loaded_state

    expected_word, expected_next_state = xoroshiro64ss_next(loaded_state)
    assert generator.next_u32() == expected_word
    assert generator.get_state() == expected_next_state

    generator.reset()
    assert generator.get_state() == DEFAULT_SEED
    assert generator.next_u32() == GOLDEN_VECTORS[0][0]


def test_fixed_width_boundary_vectors():
    boundary_vectors = [
        (0xFFFF_FFFF_FFFF_FFFF, 0x1D53_EB5C, 0xFFFF_FFFF_0000_0000),
        (0x1234_5678_FFFF_FFFF, 0x0D2D_0969, 0x9AD0_76DE_7530_FDB9),
        (0x0000_0000_0000_0001, 0x0000_0000, 0x0000_0201_0000_2000),
    ]

    for old_state, expected_word, expected_state in boundary_vectors:
        word, new_state = xoroshiro64ss_next(old_state)
        assert word == expected_word
        assert new_state == expected_state
        assert 0 <= word <= MASK32
        assert 0 < new_state <= MASK64


def test_two_instances_are_independent():
    generator_a = Xoroshiro64SS()
    generator_b = Xoroshiro64SS()

    generator_a.next_u32()
    assert generator_a.get_state() != generator_b.get_state()
    assert generator_b.get_state() == DEFAULT_SEED


def test_nonzero_boundary_states_are_allowed():
    for valid_state in (1, 1 << 63, MASK64):
        generator = Xoroshiro64SS(valid_state)
        word = generator.next_u32()
        assert 0 <= word <= MASK32
        assert 0 < generator.get_state() <= MASK64


def test_invalid_numeric_states_are_rejected():
    for invalid_state in (0, -1, MASK64 + 1):
        _expect_exception(ValueError, Xoroshiro64SS, invalid_state)
        _expect_exception(ValueError, xoroshiro64ss_next, invalid_state)

        generator = Xoroshiro64SS()
        state_before = generator.get_state()
        _expect_exception(ValueError, generator.load_state, invalid_state)
        assert generator.get_state() == state_before


def test_noninteger_states_are_rejected():
    for invalid_state in (None, 1.5, "1", True):
        _expect_exception(TypeError, Xoroshiro64SS, invalid_state)
        _expect_exception(TypeError, xoroshiro64ss_next, invalid_state)


def test_generate_rejects_invalid_counts():
    for invalid_count in (-1, -100):
        _expect_exception(ValueError, Xoroshiro64SS().generate, invalid_count)

    for invalid_count in (None, 1.5, "10", True):
        _expect_exception(TypeError, Xoroshiro64SS().generate, invalid_count)


def test_long_sequence_stays_within_fixed_widths_and_never_reaches_zero_state():
    generator = Xoroshiro64SS()

    for _ in range(10_000):
        word = generator.next_u32()
        assert 0 <= word <= MASK32
        assert 0 < generator.get_state() <= MASK64


def main():
    test_default_seed_is_the_agreed_nonzero_64_bit_value()
    test_pure_function_matches_golden_vectors()
    test_class_matches_golden_vectors_and_updates_state_after_each_output()
    test_generate_matches_repeated_next_u32_calls()
    test_generate_zero_returns_empty_list_without_changing_state()
    test_load_state_changes_current_state_and_reset_restores_constructor_seed()
    test_fixed_width_boundary_vectors()
    test_two_instances_are_independent()
    test_nonzero_boundary_states_are_allowed()
    test_invalid_numeric_states_are_rejected()
    test_noninteger_states_are_rejected()
    test_generate_rejects_invalid_counts()
    test_long_sequence_stays_within_fixed_widths_and_never_reaches_zero_state()

    print("All xoroshiro64** core tests passed.")


if __name__ == "__main__":
    main()
