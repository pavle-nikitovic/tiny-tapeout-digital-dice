"""Common statistical test platform for three 64-bit-state PRNG cores.

The platform compares the public 32-bit outputs of:

* LFSR64
* xoroshiro64** 1.0
* PCG32-oneseq (PCG-XSH-RR 64/32)

All generators receive the same raw, nonzero 64-bit seed and produce the same
number of 32-bit words.  Each word is converted to bits in the same selected
order.  The default is LSB-first because the agreed LFSR64 model stores its
first chronologically generated bit in output bit 0.

The implementation intentionally uses only the Python standard library for
the statistical calculations.  Matplotlib is optional and is needed only for
PNG plots.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Sequence


PLATFORM_VERSION = "1.0"
COMMON_SEED = 0x0123_4567_89AB_CDEF
MASK32 = 0xFFFF_FFFF
DEFAULT_WORDS = 32_768  # 2^20 output bits
DEFAULT_ALPHA = 0.01
DEFAULT_LAGS = (1, 2, 3, 4, 8, 16, 31, 32, 33, 64)
MINIMUM_WORDS = 320  # 1280 bytes -> expected byte-bin count is at least 5


@dataclass(frozen=True)
class CoreDefinition:
    """How to locate and identify one existing PRNG core."""

    key: str
    display_name: str
    module_name: str
    accepted_class_names: tuple[str, ...]


CORE_DEFINITIONS = {
    "lfsr64": CoreDefinition(
        key="lfsr64",
        display_name="LFSR64",
        module_name="lfsr64_core",
        accepted_class_names=("LFSR64", "LFSR64Model"),
    ),
    "xoroshiro64ss": CoreDefinition(
        key="xoroshiro64ss",
        display_name="xoroshiro64**",
        module_name="xoroshiro64ss_core",
        accepted_class_names=("Xoroshiro64SS",),
    ),
    "pcg32_oneseq": CoreDefinition(
        key="pcg32_oneseq",
        display_name="PCG32-oneseq",
        module_name="pcg32_oneseq_core",
        accepted_class_names=("PCG32OneSeq",),
    ),
}


@dataclass
class StatisticalResult:
    """Result of one statistical decision."""

    test: str
    parameter: str
    statistic_name: str
    statistic: float
    p_value: float | None
    adjusted_p_value: float | None
    alpha: float
    applicable: bool
    passed: bool | None
    details: dict[str, Any]


@dataclass
class GeneratorReport:
    """All data retained for one tested generator."""

    key: str
    display_name: str
    module_path: str
    class_name: str
    seed: int
    word_count: int
    bit_count: int
    bit_order: str
    ones: int
    zeros: int
    byte_counts: list[int]
    results: list[StatisticalResult]

    @property
    def overall_passed(self) -> bool:
        applicable_results = [result for result in self.results if result.applicable]
        return bool(applicable_results) and all(
            result.passed is True for result in applicable_results
        )


def _candidate_core_directories() -> tuple[Path, ...]:
    """Return local directories in which a core file may reasonably live."""
    here = Path(__file__).resolve().parent
    if here.name == "test":
        candidates = (here, here.parent)
    else:
        candidates = (here, here / "test")
    return tuple(dict.fromkeys(path.resolve() for path in candidates))


def load_local_core(module_name: str) -> ModuleType:
    """Load exactly one local core file without depending on the launch CWD."""
    filename = f"{module_name}.py"
    matches = [
        directory / filename
        for directory in _candidate_core_directories()
        if (directory / filename).is_file()
    ]

    if not matches:
        searched = "\n".join(
            f"  - {directory / filename}"
            for directory in _candidate_core_directories()
        )
        raise FileNotFoundError(
            f"Cannot find {filename}. Searched:\n{searched}\n"
            "Place the statistical platform beside the three core files, "
            "or place all four files in the repository's test/ directory."
        )

    if len(matches) > 1:
        locations = "\n".join(f"  - {path}" for path in matches)
        raise RuntimeError(
            f"Multiple copies of {filename} were found:\n{locations}\n"
            "Remove or rename the stale copy so the tested core is unambiguous."
        )

    path = matches[0]
    internal_name = f"_prng_platform_{module_name}"
    spec = importlib.util.spec_from_file_location(internal_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create an import specification for {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[internal_name] = module
    spec.loader.exec_module(module)
    return module


def resolve_generator_class(
    module: ModuleType,
    accepted_names: Sequence[str],
) -> type:
    """Resolve a class that exposes ``next_u32()``.

    Known class names are preferred.  A narrow fallback accepts a single local
    class with ``next_u32()`` so that a harmless LFSR class-name difference does
    not require changing the bit-exact core.
    """
    for name in accepted_names:
        candidate = getattr(module, name, None)
        if isinstance(candidate, type) and callable(
            getattr(candidate, "next_u32", None)
        ):
            return candidate

    fallback_candidates = [
        value
        for value in vars(module).values()
        if isinstance(value, type)
        and value.__module__ == module.__name__
        and callable(getattr(value, "next_u32", None))
    ]
    if len(fallback_candidates) == 1:
        return fallback_candidates[0]

    expected = ", ".join(accepted_names)
    raise ImportError(
        f"Cannot identify the generator class in {module.__file__}. "
        f"Expected one of [{expected}] with a next_u32() method."
    )


def instantiate_generator(definition: CoreDefinition, seed: int) -> tuple[Any, str, str]:
    """Load one core and construct it from the common raw seed."""
    module = load_local_core(definition.module_name)
    generator_class = resolve_generator_class(
        module,
        definition.accepted_class_names,
    )

    try:
        generator = generator_class(seed)
    except Exception as error:
        raise RuntimeError(
            f"Could not construct {definition.display_name} with raw seed "
            f"0x{seed:016X}: {error}"
        ) from error

    if not callable(getattr(generator, "next_u32", None)):
        raise TypeError(
            f"{generator_class.__name__} does not expose a callable next_u32()"
        )

    return generator, str(Path(module.__file__).resolve()), generator_class.__name__


def generate_words(generator: Any, count: int) -> list[int]:
    """Generate and strictly validate ``count`` consecutive 32-bit words."""
    words: list[int] = []
    for index in range(count):
        word = generator.next_u32()
        if not isinstance(word, int) or isinstance(word, bool):
            raise TypeError(
                f"output {index} is {type(word).__name__}, not an integer"
            )
        if not 0 <= word <= MASK32:
            raise ValueError(
                f"output {index} does not fit in 32 bits: {word!r}"
            )
        words.append(word)
    return words


def words_to_bits(words: Iterable[int], bit_order: str = "lsb") -> bytearray:
    """Serialize 32-bit words into a bytearray whose items are zeros or ones."""
    if bit_order not in ("lsb", "msb"):
        raise ValueError("bit_order must be 'lsb' or 'msb'")

    bit_positions: Iterable[int]
    if bit_order == "lsb":
        bit_positions = range(32)
    else:
        bit_positions = range(31, -1, -1)

    bits = bytearray()
    for word_index, word in enumerate(words):
        if not isinstance(word, int) or isinstance(word, bool):
            raise TypeError(
                f"word {word_index} is {type(word).__name__}, not an integer"
            )
        if not 0 <= word <= MASK32:
            raise ValueError(
                f"word {word_index} does not fit in 32 bits: {word!r}"
            )
        bits.extend((word >> position) & 1 for position in bit_positions)
    return bits


def pack_chronological_bits(bits: Sequence[int]) -> bytes:
    """Pack chronological bits so the first bit becomes the next byte's MSB."""
    if len(bits) % 8 != 0:
        raise ValueError("the number of bits must be divisible by 8")

    packed = bytearray(len(bits) // 8)
    for byte_index in range(len(packed)):
        value = 0
        start = byte_index * 8
        for bit in bits[start : start + 8]:
            if bit not in (0, 1):
                raise ValueError("bits must contain only 0 and 1")
            value = (value << 1) | bit
        packed[byte_index] = value
    return bytes(packed)


def _normal_two_sided_p_value(z_score: float) -> float:
    return math.erfc(abs(z_score) / math.sqrt(2.0))


def monobit_test(bits: Sequence[int], alpha: float) -> StatisticalResult:
    """NIST-style frequency (monobit) test."""
    n = len(bits)
    ones = sum(bits)
    signed_sum = 2 * ones - n
    z_score = signed_sum / math.sqrt(n)
    p_value = _normal_two_sided_p_value(z_score)

    return StatisticalResult(
        test="monobit",
        parameter="-",
        statistic_name="z",
        statistic=z_score,
        p_value=p_value,
        adjusted_p_value=None,
        alpha=alpha,
        applicable=True,
        passed=None,
        details={
            "ones": ones,
            "zeros": n - ones,
            "ones_proportion": ones / n,
        },
    )


def runs_test(bits: Sequence[int], alpha: float) -> StatisticalResult:
    """NIST-style runs test, including its frequency precondition."""
    n = len(bits)
    ones = sum(bits)
    proportion = ones / n
    precondition_limit = 2.0 / math.sqrt(n)
    precondition_passed = abs(proportion - 0.5) < precondition_limit
    applicable = precondition_passed and proportion not in (0.0, 1.0)
    number_of_runs = 1 + sum(
        bits[index] != bits[index - 1]
        for index in range(1, n)
    )

    if not applicable:
        p_value = None
    else:
        expected_runs = 2.0 * n * proportion * (1.0 - proportion)
        denominator = (
            2.0
            * math.sqrt(2.0 * n)
            * proportion
            * (1.0 - proportion)
        )
        p_value = math.erfc(abs(number_of_runs - expected_runs) / denominator)

    return StatisticalResult(
        test="runs",
        parameter="-",
        statistic_name="runs",
        statistic=float(number_of_runs),
        p_value=p_value,
        adjusted_p_value=None,
        alpha=alpha,
        applicable=applicable,
        passed=None,
        details={
            "ones_proportion": proportion,
            "frequency_precondition_limit": precondition_limit,
            "frequency_precondition_passed": precondition_passed,
        },
    )


def autocorrelation_test(
    bits: Sequence[int],
    lag: int,
    alpha: float,
) -> StatisticalResult:
    """Two-sided binary autocorrelation test at one positive lag."""
    n = len(bits)
    if not isinstance(lag, int) or isinstance(lag, bool):
        raise TypeError("lag must be an integer")
    if not 0 < lag < n:
        raise ValueError("lag must satisfy 0 < lag < number of bits")

    compared = n - lag
    disagreements = sum(
        bits[index] ^ bits[index + lag]
        for index in range(compared)
    )
    z_score = (2.0 * disagreements - compared) / math.sqrt(compared)
    p_value = _normal_two_sided_p_value(z_score)

    return StatisticalResult(
        test="autocorrelation",
        parameter=f"lag={lag}",
        statistic_name="z",
        statistic=z_score,
        p_value=p_value,
        adjusted_p_value=None,
        alpha=alpha,
        applicable=True,
        passed=None,
        details={
            "lag": lag,
            "compared_pairs": compared,
            "disagreements": disagreements,
            "disagreement_proportion": disagreements / compared,
            "correlation_estimate": 1.0 - 2.0 * disagreements / compared,
        },
    )


def regularized_gamma_q(a: float, x: float) -> float:
    """Return Q(a, x), the regularized upper incomplete gamma function.

    This standard series/continued-fraction implementation avoids a SciPy
    dependency and is sufficient for the chi-square survival probability used
    by this platform.
    """
    if a <= 0.0:
        raise ValueError("a must be positive")
    if x < 0.0:
        raise ValueError("x must be non-negative")
    if x == 0.0:
        return 1.0

    epsilon = 3.0e-14
    tiny = 1.0e-300
    maximum_iterations = 10_000
    log_factor = -x + a * math.log(x) - math.lgamma(a)

    if x < a + 1.0:
        # Compute P(a, x) as a series, then return Q(a, x) = 1 - P(a, x).
        ap = a
        term = 1.0 / a
        series_sum = term
        for _ in range(maximum_iterations):
            ap += 1.0
            term *= x / ap
            series_sum += term
            if abs(term) <= abs(series_sum) * epsilon:
                p_value = series_sum * math.exp(log_factor)
                return min(1.0, max(0.0, 1.0 - p_value))
        raise ArithmeticError("regularized gamma series did not converge")

    # Compute Q(a, x) directly as a continued fraction (Lentz's method).
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / max(abs(b), tiny)
    if b < 0.0:
        d = -d
    fraction = d

    for index in range(1, maximum_iterations + 1):
        coefficient = -index * (index - a)
        b += 2.0
        d = coefficient * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + coefficient / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        fraction *= delta
        if abs(delta - 1.0) <= epsilon:
            q_value = math.exp(log_factor) * fraction
            return min(1.0, max(0.0, q_value))

    raise ArithmeticError("regularized gamma continued fraction did not converge")


def byte_chi_square_test(
    packed_bits: bytes,
    alpha: float,
) -> tuple[StatisticalResult, list[int]]:
    """Chi-square goodness-of-fit test over the 256 possible byte values."""
    number_of_bytes = len(packed_bits)
    if number_of_bytes == 0:
        raise ValueError("packed_bits must not be empty")

    counts = [0] * 256
    for value in packed_bits:
        counts[value] += 1

    expected = number_of_bytes / 256.0
    chi_square = sum(
        (observed - expected) ** 2 / expected
        for observed in counts
    )
    degrees_of_freedom = 255
    p_value = regularized_gamma_q(
        degrees_of_freedom / 2.0,
        chi_square / 2.0,
    )

    result = StatisticalResult(
        test="byte_chi_square",
        parameter="256 bins",
        statistic_name="chi2",
        statistic=chi_square,
        p_value=p_value,
        adjusted_p_value=None,
        alpha=alpha,
        applicable=expected >= 5.0,
        passed=None,
        details={
            "degrees_of_freedom": degrees_of_freedom,
            "number_of_bytes": number_of_bytes,
            "expected_per_bin": expected,
            "minimum_observed": min(counts),
            "maximum_observed": max(counts),
            "expected_count_condition_passed": expected >= 5.0,
        },
    )
    return result, counts


def evaluate_bitstream(
    bits: Sequence[int],
    alpha: float,
    lags: Sequence[int],
) -> tuple[list[StatisticalResult], list[int]]:
    """Run the same complete statistical suite on one unchanged bitstream."""
    if not bits:
        raise ValueError("bits must not be empty")
    if any(bit not in (0, 1) for bit in bits):
        raise ValueError("bits must contain only 0 and 1")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must satisfy 0 < alpha < 1")
    if not lags:
        raise ValueError("at least one autocorrelation lag is required")
    if len(set(lags)) != len(lags):
        raise ValueError("autocorrelation lags must be unique")

    results = [monobit_test(bits, alpha), runs_test(bits, alpha)]
    results.extend(
        autocorrelation_test(bits, lag, alpha)
        for lag in lags
    )

    packed_bits = pack_chronological_bits(bits)
    chi_square_result, byte_counts = byte_chi_square_test(packed_bits, alpha)
    results.append(chi_square_result)
    return results, byte_counts


def apply_holm_bonferroni(
    reports: Sequence[GeneratorReport],
    alpha: float,
) -> None:
    """Apply one global Holm-Bonferroni correction in place.

    The family contains every applicable p-value from every selected generator.
    Holm-adjusted p-values control the family-wise false-rejection probability
    without assuming that the tests are independent.
    """
    applicable_results = [
        result
        for report in reports
        for result in report.results
        if result.applicable and result.p_value is not None
    ]
    if not applicable_results:
        raise ValueError("there are no applicable p-values to correct")

    ordered = sorted(applicable_results, key=lambda result: result.p_value)
    family_size = len(ordered)
    running_adjusted = 0.0
    for zero_based_rank, result in enumerate(ordered):
        multiplier = family_size - zero_based_rank
        adjusted = min(1.0, multiplier * result.p_value)
        running_adjusted = max(running_adjusted, adjusted)
        result.adjusted_p_value = running_adjusted
        result.passed = running_adjusted >= alpha

    for report in reports:
        for result in report.results:
            if not result.applicable:
                result.adjusted_p_value = None
                result.passed = None


def _result_by_test(
    report: GeneratorReport,
    test_name: str,
) -> StatisticalResult:
    matches = [result for result in report.results if result.test == test_name]
    if len(matches) != 1:
        raise ValueError(
            f"expected one {test_name!r} result for {report.display_name}"
        )
    return matches[0]


def _autocorrelation_results(report: GeneratorReport) -> list[StatisticalResult]:
    return [
        result
        for result in report.results
        if result.test == "autocorrelation"
    ]


def write_detailed_csv(reports: Sequence[GeneratorReport], path: Path) -> None:
    """Write one row per statistical decision."""
    fieldnames = [
        "generator",
        "test",
        "parameter",
        "statistic_name",
        "statistic",
        "raw_p_value",
        "holm_adjusted_p_value",
        "alpha",
        "applicable",
        "status",
        "details",
    ]
    with path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        for report in reports:
            for result in report.results:
                writer.writerow(
                    {
                        "generator": report.display_name,
                        "test": result.test,
                        "parameter": result.parameter,
                        "statistic_name": result.statistic_name,
                        "statistic": f"{result.statistic:.17g}",
                        "raw_p_value": (
                            "" if result.p_value is None
                            else f"{result.p_value:.17g}"
                        ),
                        "holm_adjusted_p_value": (
                            "" if result.adjusted_p_value is None
                            else f"{result.adjusted_p_value:.17g}"
                        ),
                        "alpha": f"{result.alpha:.17g}",
                        "applicable": result.applicable,
                        "status": (
                            "N/A" if not result.applicable
                            else "PASS" if result.passed
                            else "FAIL"
                        ),
                        "details": json.dumps(
                            result.details,
                            sort_keys=True,
                            ensure_ascii=False,
                        ),
                    }
                )


def write_summary_csv(reports: Sequence[GeneratorReport], path: Path) -> None:
    """Write a compact one-row-per-generator comparison."""
    fieldnames = [
        "generator",
        "seed",
        "words",
        "bits",
        "bit_order",
        "ones",
        "zeros",
        "ones_proportion",
        "monobit_raw_p",
        "monobit_holm_p",
        "runs_raw_p",
        "runs_holm_p",
        "minimum_autocorrelation_raw_p",
        "minimum_autocorrelation_holm_p",
        "byte_chi_square_raw_p",
        "byte_chi_square_holm_p",
        "overall_passed",
    ]
    with path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        for report in reports:
            monobit = _result_by_test(report, "monobit")
            runs = _result_by_test(report, "runs")
            chi_square = _result_by_test(report, "byte_chi_square")
            autocorrelations = _autocorrelation_results(report)
            writer.writerow(
                {
                    "generator": report.display_name,
                    "seed": f"0x{report.seed:016X}",
                    "words": report.word_count,
                    "bits": report.bit_count,
                    "bit_order": report.bit_order,
                    "ones": report.ones,
                    "zeros": report.zeros,
                    "ones_proportion": f"{report.ones / report.bit_count:.17g}",
                    "monobit_raw_p": f"{monobit.p_value:.17g}",
                    "monobit_holm_p": f"{monobit.adjusted_p_value:.17g}",
                    "runs_raw_p": (
                        "" if runs.p_value is None else f"{runs.p_value:.17g}"
                    ),
                    "runs_holm_p": (
                        "" if runs.adjusted_p_value is None
                        else f"{runs.adjusted_p_value:.17g}"
                    ),
                    "minimum_autocorrelation_raw_p": (
                        f"{min(result.p_value for result in autocorrelations):.17g}"
                    ),
                    "minimum_autocorrelation_holm_p": (
                        f"{min(result.adjusted_p_value for result in autocorrelations):.17g}"
                    ),
                    "byte_chi_square_raw_p": f"{chi_square.p_value:.17g}",
                    "byte_chi_square_holm_p": (
                        f"{chi_square.adjusted_p_value:.17g}"
                    ),
                    "overall_passed": report.overall_passed,
                }
            )


def write_json_report(
    reports: Sequence[GeneratorReport],
    path: Path,
    alpha: float,
    lags: Sequence[int],
) -> None:
    """Write machine-readable metadata and all detailed results."""
    payload = {
        "platform_version": PLATFORM_VERSION,
        "common_seed": f"0x{reports[0].seed:016X}",
        "word_count_per_generator": reports[0].word_count,
        "bit_count_per_generator": reports[0].bit_count,
        "bit_order_within_each_word": reports[0].bit_order,
        "alpha": alpha,
        "autocorrelation_lags": list(lags),
        "multiple_testing_correction": (
            "Holm-Bonferroni across all applicable results from all selected generators"
        ),
        "decision_alpha": alpha,
        "generators": [
            {
                **{
                    key: value
                    for key, value in asdict(report).items()
                    if key != "results"
                },
                "seed": f"0x{report.seed:016X}",
                "overall_passed": report.overall_passed,
                "results": [asdict(result) for result in report.results],
            }
            for report in reports
        ],
    }
    with path.open("w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, indent=2, ensure_ascii=False)
        output_file.write("\n")


def write_plots(reports: Sequence[GeneratorReport], output_directory: Path) -> list[Path]:
    """Create three PNG comparison plots and return their paths."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise RuntimeError(
            "Matplotlib is not installed; use --no-plots or install the "
            "provided requirements file."
        ) from error

    written_paths: list[Path] = []

    # Show raw p-values for diagnosis.  Pass/fail still uses Holm-adjusted p.
    category_labels = ("Monobit", "Runs", "Autocorr. min", "Byte chi-square")
    figure, axis = plt.subplots(figsize=(10, 5.5))
    group_width = 0.8
    bar_width = group_width / len(reports)
    base_positions = list(range(len(category_labels)))

    for report_index, report in enumerate(reports):
        monobit = _result_by_test(report, "monobit")
        runs = _result_by_test(report, "runs")
        chi_square = _result_by_test(report, "byte_chi_square")
        autocorrelations = _autocorrelation_results(report)
        minimum_autocorrelation = min(
            autocorrelations,
            key=lambda result: result.p_value,
        )
        selected = (monobit, runs, minimum_autocorrelation, chi_square)
        plot_floor = max(selected[0].alpha / 1_000.0, 1.0e-12)
        raw_p_values = [
            (
                max(result.p_value, plot_floor)
                if result.applicable and result.p_value is not None
                else plot_floor
            )
            for result in selected
        ]
        offset = (report_index - (len(reports) - 1) / 2.0) * bar_width
        bars = axis.bar(
            [position + offset for position in base_positions],
            raw_p_values,
            width=bar_width,
            label=report.display_name,
        )
        for bar, result in zip(bars, selected):
            if not result.applicable:
                bar.set_facecolor("lightgray")
                bar.set_edgecolor("gray")
                bar.set_hatch("//")
                axis.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    plot_floor * 1.5,
                    "N/A",
                    ha="center",
                    va="bottom",
                    rotation=90,
                    fontsize=8,
                )
            elif result.passed is False:
                bar.set_edgecolor("red")
                bar.set_linewidth(2.0)

    alpha = reports[0].results[0].alpha
    axis.axhline(
        alpha,
        color="black",
        linestyle="--",
        linewidth=1.2,
        label=f"alpha = {alpha:g} (odluka koristi Holm p)",
    )
    axis.set_yscale("log")
    axis.set_ylim(bottom=max(alpha / 1_000.0, 1.0e-12), top=1.05)
    axis.set_xticks(base_positions, category_labels)
    axis.set_ylabel("Sirova p-vrednost")
    axis.set_title("Sirove p-vrednosti (crvena ivica = Holm FAIL)")
    axis.grid(axis="y", which="both", alpha=0.25)
    axis.legend()
    figure.tight_layout()
    path = output_directory / "p_values.png"
    figure.savefig(path, dpi=170)
    plt.close(figure)
    written_paths.append(path)

    figure, axis = plt.subplots(figsize=(10, 5.5))
    for report in reports:
        autocorrelations = _autocorrelation_results(report)
        lags = [int(result.details["lag"]) for result in autocorrelations]
        correlations = [
            float(result.details["correlation_estimate"])
            for result in autocorrelations
        ]
        axis.plot(lags, correlations, marker="o", label=report.display_name)

    axis.axhline(0.0, color="black", linestyle="--", linewidth=1.2)
    axis.set_xlabel("Kasnjenje (lag) [bita]")
    axis.set_ylabel("Procena korelacije rho")
    axis.set_title("Autokorelacija bitstreama")
    axis.grid(alpha=0.25)
    axis.legend()
    figure.tight_layout()
    path = output_directory / "autocorrelation.png"
    figure.savefig(path, dpi=170)
    plt.close(figure)
    written_paths.append(path)

    figure, axes = plt.subplots(
        len(reports),
        1,
        figsize=(11, 3.0 * len(reports)),
        sharex=True,
        squeeze=False,
    )
    byte_values = list(range(256))
    expected = reports[0].bit_count / 8.0 / 256.0
    for axis, report in zip(axes[:, 0], reports):
        axis.bar(byte_values, report.byte_counts, width=1.0)
        axis.axhline(expected, color="red", linestyle="--", linewidth=1.0)
        axis.set_ylabel("Broj")
        axis.set_title(report.display_name)
        axis.grid(axis="y", alpha=0.2)
    axes[-1, 0].set_xlabel("Vrednost bajta")
    figure.suptitle("Raspodela 256 vrednosti bajta", y=1.0)
    figure.tight_layout()
    path = output_directory / "byte_distribution.png"
    figure.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(figure)
    written_paths.append(path)

    return written_paths


def print_results_table(reports: Sequence[GeneratorReport]) -> None:
    """Print detailed decisions and a compact final summary."""
    print()
    print(
        f"{'Generator':<18} {'Test':<22} {'Parametar':<10} "
        f"{'Statistika':>12} {'sirovo p':>12} {'Holm p':>12} {'Rezultat':>9}"
    )
    print("-" * 104)
    for report in reports:
        for result in report.results:
            status = (
                "N/A" if not result.applicable
                else "PASS" if result.passed
                else "FAIL"
            )
            raw_p = "-" if result.p_value is None else f"{result.p_value:.5g}"
            holm_p = (
                "-" if result.adjusted_p_value is None
                else f"{result.adjusted_p_value:.5g}"
            )
            print(
                f"{report.display_name:<18} {result.test:<22} "
                f"{result.parameter:<10} {result.statistic:>12.5g} "
                f"{raw_p:>12} {holm_p:>12} "
                f"{status:>9}"
            )

    print()
    print("Zbirni rezultat:")
    for report in reports:
        status = "PASS" if report.overall_passed else "FAIL"
        proportion = report.ones / report.bit_count
        print(
            f"  {report.display_name:<18} {status:<4}  "
            f"jedinice={proportion:.6f}"
        )


def _parse_seed(text: str) -> int:
    try:
        seed = int(text.replace("_", ""), 0)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "seed must be a decimal or 0x-prefixed integer"
        ) from error
    if not 0 < seed <= 0xFFFF_FFFF_FFFF_FFFF:
        raise argparse.ArgumentTypeError(
            "the common seed must be a nonzero 64-bit integer"
        )
    return seed


def _parse_lags(text: str) -> tuple[int, ...]:
    try:
        lags = tuple(int(part.strip()) for part in text.split(","))
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "lags must be comma-separated positive integers"
        ) from error
    if not lags or any(lag <= 0 for lag in lags):
        raise argparse.ArgumentTypeError("all lags must be positive")
    if len(set(lags)) != len(lags):
        raise argparse.ArgumentTypeError("lags must be unique")
    return lags


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run identical statistical tests on LFSR64, xoroshiro64** and "
            "PCG32-oneseq."
        )
    )
    parser.add_argument(
        "--words",
        type=int,
        default=DEFAULT_WORDS,
        help=(
            f"32-bit outputs per generator (default: {DEFAULT_WORDS}; "
            f"minimum: {MINIMUM_WORDS})"
        ),
    )
    parser.add_argument(
        "--seed",
        type=_parse_seed,
        default=COMMON_SEED,
        help="common raw 64-bit state (default: 0x0123456789ABCDEF)",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=DEFAULT_ALPHA,
        help="family-wise decision level after Holm correction (default: 0.01)",
    )
    parser.add_argument(
        "--lags",
        type=_parse_lags,
        default=DEFAULT_LAGS,
        help="comma-separated autocorrelation lags",
    )
    parser.add_argument(
        "--bit-order",
        choices=("lsb", "msb"),
        default="lsb",
        help="serialization order within every 32-bit word (default: lsb)",
    )
    parser.add_argument(
        "--generators",
        nargs="+",
        choices=tuple(CORE_DEFINITIONS),
        default=list(CORE_DEFINITIONS),
        help="subset of generator keys to test",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("prng_results"),
        help="directory for CSV, JSON, PNG and optional stream files",
    )
    parser.add_argument(
        "--save-streams",
        action="store_true",
        help="also save each tested chronological bitstream as a .bin file",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="skip PNG plots (all numerical results are still written)",
    )
    return parser


def validate_arguments(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if args.words < MINIMUM_WORDS:
        parser.error(
            f"--words must be at least {MINIMUM_WORDS} so every expected "
            "byte-bin count is at least 5"
        )
    if not 0.0 < args.alpha < 1.0:
        parser.error("--alpha must satisfy 0 < alpha < 1")
    bit_count = args.words * 32
    if any(lag >= bit_count for lag in args.lags):
        parser.error("every autocorrelation lag must be smaller than the bit count")
    if any(bit_count - lag < 100 for lag in args.lags):
        parser.error(
            "every autocorrelation lag must leave at least 100 compared bit pairs"
        )
    if len(set(args.generators)) != len(args.generators):
        parser.error("--generators must not contain duplicate keys")


def run_platform(args: argparse.Namespace) -> list[GeneratorReport]:
    """Load selected cores, generate equal streams, and run all tests."""
    reports: list[GeneratorReport] = []
    saved_streams: dict[str, bytes] = {}

    loaded_generators = []
    for key in args.generators:
        definition = CORE_DEFINITIONS[key]
        generator, module_path, class_name = instantiate_generator(
            definition,
            args.seed,
        )
        loaded_generators.append(
            (key, definition, generator, module_path, class_name)
        )

    for key, definition, generator, module_path, class_name in loaded_generators:
        print(
            f"Generisem {args.words:,} reci ({args.words * 32:,} bita): "
            f"{definition.display_name}..."
        )
        words = generate_words(generator, args.words)
        bits = words_to_bits(words, args.bit_order)
        results, byte_counts = evaluate_bitstream(bits, args.alpha, args.lags)

        report = GeneratorReport(
            key=key,
            display_name=definition.display_name,
            module_path=module_path,
            class_name=class_name,
            seed=args.seed,
            word_count=args.words,
            bit_count=len(bits),
            bit_order=args.bit_order,
            ones=sum(bits),
            zeros=len(bits) - sum(bits),
            byte_counts=byte_counts,
            results=results,
        )
        reports.append(report)

        if args.save_streams:
            saved_streams[key] = pack_chronological_bits(bits)

    apply_holm_bonferroni(reports, args.alpha)
    output_directory = args.output_dir.resolve()
    output_directory.mkdir(parents=True, exist_ok=True)

    for key, stream_bytes in saved_streams.items():
        (output_directory / f"{key}_stream.bin").write_bytes(stream_bytes)

    write_detailed_csv(reports, output_directory / "detailed_results.csv")
    write_summary_csv(reports, output_directory / "summary.csv")
    write_json_report(
        reports,
        output_directory / "results.json",
        args.alpha,
        args.lags,
    )

    if not args.no_plots:
        try:
            write_plots(reports, output_directory)
        except RuntimeError as error:
            print(f"Upozorenje: {error}", file=sys.stderr)

    return reports


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    validate_arguments(args, parser)

    try:
        reports = run_platform(args)
    except (
        ArithmeticError,
        FileNotFoundError,
        ImportError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as error:
        print(f"Greska: {error}", file=sys.stderr)
        return 2

    print_results_table(reports)
    print()
    print(f"Rezultati su sacuvani u: {args.output_dir.resolve()}")
    print(
        "Napomena: PASS nije dokaz potpune slucajnosti, a Python vreme "
        "izvrsavanja nije ASIC benchmark."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
