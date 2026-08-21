"""Cocotb verification of pcg32_oneseq_core.v against its Python model."""

import cocotb

from pcg32_oneseq_core import PCG32OneSeq
from prng_cocotb_common import (
    check_bit_exact_sequence,
    check_continuous_requests,
    check_first_word_and_latency,
    check_pause_and_output_hold,
    check_reset_restarts_sequence,
    check_single_cycle_request_pattern,
)


LATENCY = 1


@cocotb.test()
async def test_first_word_and_one_cycle_latency(dut):
    await check_first_word_and_latency(dut, PCG32OneSeq, LATENCY)


@cocotb.test()
async def test_1000_words_match_python_model(dut):
    await check_bit_exact_sequence(dut, PCG32OneSeq, LATENCY, word_count=1000)


@cocotb.test()
async def test_pause_holds_state_and_last_output(dut):
    await check_pause_and_output_hold(dut, PCG32OneSeq, LATENCY)


@cocotb.test()
async def test_continuous_next_produces_one_word_per_cycle(dut):
    await check_continuous_requests(dut, PCG32OneSeq, LATENCY, word_count=64)


@cocotb.test()
async def test_valid_follows_an_irregular_request_pattern(dut):
    pattern = (1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 1)
    await check_single_cycle_request_pattern(dut, PCG32OneSeq, pattern)


@cocotb.test()
async def test_reset_restarts_original_sequence(dut):
    await check_reset_restarts_sequence(dut, PCG32OneSeq, LATENCY)

