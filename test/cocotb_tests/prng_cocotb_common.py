"""Shared cocotb checks for all three transactional PRNG cores.

The helpers deliberately drive inputs on falling clock edges and sample
outputs only after a rising edge reaches cocotb's read-only phase.  This avoids
races with the nonblocking assignments in the Verilog sequential logic.
"""

from collections import deque

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge


CLOCK_PERIOD_NS = 10
RESET_CYCLES = 2


def signal_value(signal):
    """Return a resolved RTL signal as a Python integer."""
    return int(signal.value)


def _make_clock(signal):
    """Construct a clock with cocotb 2.x and 1.x argument compatibility."""
    try:
        return Clock(signal, CLOCK_PERIOD_NS, unit="ns")
    except TypeError:
        return Clock(signal, CLOCK_PERIOD_NS, units="ns")


async def sample_rising(dut):
    """Sample the public protocol outputs after sequential RTL has settled."""
    await RisingEdge(dut.clk_i)
    await ReadOnly()
    return {
        "ready": signal_value(dut.ready_o),
        "valid": signal_value(dut.valid_o),
        "random": signal_value(dut.random_o),
    }


async def start_clock_and_reset(dut, reset_cycles=RESET_CYCLES):
    """Start the clock and perform the agreed synchronous active-low reset."""
    dut.clk_i.value = 0
    dut.rst_ni.value = 0
    dut.next_i.value = 0
    cocotb.start_soon(_make_clock(dut.clk_i).start())

    for cycle in range(1, reset_cycles + 1):
        sample = await sample_rising(dut)
        assert sample["ready"] == 0, (
            f"ready_o must be 0 during reset (reset cycle {cycle})"
        )
        assert sample["valid"] == 0, (
            f"valid_o must be 0 during reset (reset cycle {cycle})"
        )
        assert sample["random"] == 0, (
            f"random_o must be 0 during reset (reset cycle {cycle})"
        )

    await FallingEdge(dut.clk_i)
    dut.rst_ni.value = 1
    await ReadOnly()

    assert signal_value(dut.ready_o) == 1, (
        "ready_o must become 1 after reset is released"
    )
    assert signal_value(dut.valid_o) == 0
    assert signal_value(dut.random_o) == 0


async def request_one_word(dut, expected_latency):
    """Request one word and verify its exact accepted-edge latency.

    The acceptance edge itself is latency cycle 1.  Thus the fast cores use
    ``expected_latency=1`` and the serial LFSR uses ``expected_latency=32``.
    """
    assert expected_latency >= 1

    await FallingEdge(dut.clk_i)
    assert signal_value(dut.ready_o) == 1, (
        "request_one_word called while ready_o was low"
    )
    dut.next_i.value = 1

    completed_word = None

    for latency_cycle in range(1, expected_latency + 1):
        sample = await sample_rising(dut)

        if latency_cycle < expected_latency:
            assert sample["valid"] == 0, (
                "valid_o asserted too early: "
                f"cycle {latency_cycle}, expected {expected_latency}"
            )
        else:
            assert sample["valid"] == 1, (
                "valid_o did not assert at the expected latency: "
                f"cycle {expected_latency}"
            )
            completed_word = sample["random"]

        if latency_cycle == 1:
            # The request is a one-cycle pulse.  Lower it on the falling edge,
            # after the RTL has already sampled the accepting rising edge.
            await FallingEdge(dut.clk_i)
            dut.next_i.value = 0

    return completed_word


async def check_first_word_and_latency(dut, model_type, expected_latency):
    """Check reset values, one accepted request, and the first golden word."""
    await start_clock_and_reset(dut)
    model = model_type()
    expected = model.next_u32()
    actual = await request_one_word(dut, expected_latency)
    assert actual == expected, (
        f"first word mismatch: RTL=0x{actual:08X}, Python=0x{expected:08X}"
    )


async def check_bit_exact_sequence(
    dut,
    model_type,
    expected_latency,
    word_count=1000,
):
    """Compare a long RTL sequence word-for-word with its Python model."""
    await start_clock_and_reset(dut)
    model = model_type()

    for index in range(word_count):
        expected = model.next_u32()
        actual = await request_one_word(dut, expected_latency)
        assert actual == expected, (
            f"word {index} mismatch: "
            f"RTL=0x{actual:08X}, Python=0x{expected:08X}"
        )


async def check_pause_and_output_hold(
    dut,
    model_type,
    expected_latency,
    idle_cycles=7,
):
    """Verify that pausing holds state/output and produces no valid pulse."""
    await start_clock_and_reset(dut)
    model = model_type()

    expected_first = model.next_u32()
    actual_first = await request_one_word(dut, expected_latency)
    assert actual_first == expected_first

    for idle_cycle in range(1, idle_cycles + 1):
        sample = await sample_rising(dut)
        assert sample["ready"] == 1, (
            f"ready_o must be 1 while idle (idle cycle {idle_cycle})"
        )
        assert sample["valid"] == 0, (
            f"valid_o asserted without a request (idle cycle {idle_cycle})"
        )
        assert sample["random"] == actual_first, (
            f"random_o changed while idle (idle cycle {idle_cycle})"
        )

    expected_second = model.next_u32()
    actual_second = await request_one_word(dut, expected_latency)
    assert actual_second == expected_second, (
        "generator state advanced during the pause: "
        f"RTL=0x{actual_second:08X}, Python=0x{expected_second:08X}"
    )


async def check_reset_restarts_sequence(
    dut,
    model_type,
    expected_latency,
    words_before_reset=5,
):
    """Verify that a later reset restarts the original deterministic stream."""
    await start_clock_and_reset(dut)
    model = model_type()

    for _ in range(words_before_reset):
        expected = model.next_u32()
        actual = await request_one_word(dut, expected_latency)
        assert actual == expected

    await FallingEdge(dut.clk_i)
    dut.next_i.value = 0
    dut.rst_ni.value = 0

    for reset_cycle in range(1, RESET_CYCLES + 1):
        sample = await sample_rising(dut)
        assert sample["ready"] == 0, (
            f"ready_o must be 0 during repeated reset cycle {reset_cycle}"
        )
        assert sample["valid"] == 0
        assert sample["random"] == 0

    await FallingEdge(dut.clk_i)
    dut.rst_ni.value = 1
    await ReadOnly()
    assert signal_value(dut.ready_o) == 1

    restarted_model = model_type()
    expected_first = restarted_model.next_u32()
    actual_first = await request_one_word(dut, expected_latency)
    assert actual_first == expected_first, (
        "reset did not restart the original sequence: "
        f"RTL=0x{actual_first:08X}, Python=0x{expected_first:08X}"
    )


async def check_continuous_requests(
    dut,
    model_type,
    expected_latency,
    word_count=16,
):
    """Hold next_i high and score every accepted request and valid result."""
    await start_clock_and_reset(dut)
    model = model_type()
    pending_words = deque()
    valid_cycles = []
    accepted_count = 0
    produced_count = 0
    cycle = 0
    last_word = 0

    await FallingEdge(dut.clk_i)
    dut.next_i.value = 1

    while produced_count < word_count:
        cycle += 1

        # ready_o is sampled before the rising edge: this is exactly when the
        # protocol decides whether the pending next_i request is accepted.
        ready_before_edge = signal_value(dut.ready_o)
        if ready_before_edge:
            pending_words.append(model.next_u32())
            accepted_count += 1

        sample = await sample_rising(dut)
        expected_valid = int(cycle % expected_latency == 0)
        assert sample["valid"] == expected_valid, (
            f"unexpected valid_o at continuous-request cycle {cycle}: "
            f"got {sample['valid']}, expected {expected_valid}"
        )

        if sample["valid"]:
            assert pending_words, (
                f"valid_o at cycle {cycle} had no accepted request"
            )
            expected = pending_words.popleft()
            actual = sample["random"]
            assert actual == expected, (
                f"continuous word {produced_count} mismatch at cycle {cycle}: "
                f"RTL=0x{actual:08X}, Python=0x{expected:08X}"
            )
            last_word = actual
            valid_cycles.append(cycle)
            produced_count += 1

        if produced_count < word_count:
            await FallingEdge(dut.clk_i)

    await FallingEdge(dut.clk_i)
    dut.next_i.value = 0

    assert accepted_count == word_count, (
        f"accepted {accepted_count} requests for {word_count} results"
    )
    assert not pending_words
    assert valid_cycles == [
        expected_latency * index for index in range(1, word_count + 1)
    ]

    # One idle edge must clear valid_o and retain the final word.
    sample = await sample_rising(dut)
    assert sample["ready"] == 1
    assert sample["valid"] == 0
    assert sample["random"] == last_word


async def check_single_cycle_request_pattern(dut, model_type, pattern):
    """For a one-cycle core, prove valid_o exactly follows accepted next_i."""
    await start_clock_and_reset(dut)
    model = model_type()
    last_word = 0

    for cycle, request in enumerate(pattern, start=1):
        await FallingEdge(dut.clk_i)
        assert signal_value(dut.ready_o) == 1, (
            f"ready_o fell in a one-cycle core before pattern cycle {cycle}"
        )
        dut.next_i.value = request

        expected = model.next_u32() if request else last_word
        sample = await sample_rising(dut)

        assert sample["ready"] == 1, (
            f"ready_o fell in a one-cycle core at pattern cycle {cycle}"
        )
        assert sample["valid"] == request, (
            f"valid_o did not follow accepted next_i at pattern cycle {cycle}"
        )
        assert sample["random"] == expected, (
            f"pattern cycle {cycle}: RTL=0x{sample['random']:08X}, "
            f"Python=0x{expected:08X}"
        )

        if request:
            last_word = expected

    await FallingEdge(dut.clk_i)
    dut.next_i.value = 0

