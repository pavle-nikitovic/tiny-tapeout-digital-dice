"""Cocotb verification of lfsr64_core.v against lfsr64_core.py."""

import cocotb
from cocotb.triggers import FallingEdge, ReadOnly

from lfsr64_core import LFSR64
from prng_cocotb_common import (
    check_bit_exact_sequence,
    check_continuous_requests,
    check_first_word_and_latency,
    check_pause_and_output_hold,
    check_reset_restarts_sequence,
    request_one_word,
    sample_rising,
    signal_value,
    start_clock_and_reset,
)


LATENCY = 32


@cocotb.test()
async def test_first_word_and_exact_32_cycle_latency(dut):
    await check_first_word_and_latency(dut, LFSR64, LATENCY)


@cocotb.test()
async def test_1000_words_match_python_model(dut):
    await check_bit_exact_sequence(dut, LFSR64, LATENCY, word_count=1000)


@cocotb.test()
async def test_pause_holds_state_and_last_output(dut):
    await check_pause_and_output_hold(dut, LFSR64, LATENCY)


@cocotb.test()
async def test_continuous_next_produces_one_word_every_32_cycles(dut):
    await check_continuous_requests(dut, LFSR64, LATENCY, word_count=16)


@cocotb.test()
async def test_reset_restarts_original_sequence(dut):
    await check_reset_restarts_sequence(dut, LFSR64, LATENCY)


@cocotb.test()
async def test_request_while_busy_is_ignored(dut):
    await start_clock_and_reset(dut)
    model = LFSR64()
    expected_first = model.next_u32()

    # Accept the real request; this edge is LFSR step 1 of 32.
    await FallingEdge(dut.clk_i)
    assert signal_value(dut.ready_o) == 1
    dut.next_i.value = 1
    sample = await sample_rising(dut)
    assert sample["ready"] == 0
    assert sample["valid"] == 0

    await FallingEdge(dut.clk_i)
    dut.next_i.value = 0

    # Advance through four more busy cycles (steps 2 through 5).
    for _ in range(4):
        sample = await sample_rising(dut)
        assert sample["ready"] == 0
        assert sample["valid"] == 0

    # Pulse next_i for one edge while ready_o is low.  It must not be queued.
    await FallingEdge(dut.clk_i)
    assert signal_value(dut.ready_o) == 0
    dut.next_i.value = 1
    sample = await sample_rising(dut)
    assert sample["ready"] == 0
    assert sample["valid"] == 0

    await FallingEdge(dut.clk_i)
    dut.next_i.value = 0

    # The ignored pulse was sampled on step 6, so exactly 26 LFSR steps remain.
    # It must neither shorten nor restart the in-flight transaction.
    for remaining_cycle in range(1, 27):
        sample = await sample_rising(dut)
        if remaining_cycle < 26:
            assert sample["valid"] == 0, (
                "busy request changed the completion latency: "
                f"valid_o asserted {26 - remaining_cycle} cycles too early"
            )
            assert sample["ready"] == 0
        else:
            assert sample["valid"] == 1, (
                "LFSR did not finish exactly 26 cycles after the busy pulse"
            )

    assert sample["ready"] == 1
    assert sample["random"] == expected_first

    # If the busy pulse altered or queued work, this next legal result will
    # not be the Python model's second word.
    expected_second = model.next_u32()
    actual_second = await request_one_word(dut, LATENCY)
    assert actual_second == expected_second


@cocotb.test()
async def test_reset_aborts_an_unfinished_word(dut):
    await start_clock_and_reset(dut)

    await FallingEdge(dut.clk_i)
    dut.next_i.value = 1
    sample = await sample_rising(dut)
    assert sample["ready"] == 0
    assert sample["valid"] == 0

    await FallingEdge(dut.clk_i)
    dut.next_i.value = 0

    for _ in range(7):
        sample = await sample_rising(dut)
        assert sample["ready"] == 0
        assert sample["valid"] == 0

    await FallingEdge(dut.clk_i)
    dut.rst_ni.value = 0
    sample = await sample_rising(dut)
    assert sample == {"ready": 0, "valid": 0, "random": 0}

    await FallingEdge(dut.clk_i)
    dut.rst_ni.value = 1
    await ReadOnly()
    assert signal_value(dut.ready_o) == 1

    model = LFSR64()
    expected_first = model.next_u32()
    actual_first = await request_one_word(dut, LATENCY)
    assert actual_first == expected_first
