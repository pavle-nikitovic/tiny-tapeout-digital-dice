"""Deterministic tests for ``prng_statistical_tests.py``.

Run directly with::

    python3 test/test_prng_statistical_tests.py

The tests require neither pytest nor SciPy.  Plot verification is skipped when
Matplotlib is not installed.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import math
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace

import prng_statistical_tests as platform


def bits_from_msb_first_bytes(values: bytes) -> bytearray:
    bits = bytearray()
    for value in values:
        bits.extend((value >> position) & 1 for position in range(7, -1, -1))
    return bits


class TestBitstreamContract(unittest.TestCase):
    def test_lsb_first_word_conversion(self):
        bits = platform.words_to_bits([0x0000_000D], "lsb")
        self.assertEqual(list(bits[:4]), [1, 0, 1, 1])
        self.assertEqual(len(bits), 32)

    def test_msb_first_word_conversion(self):
        bits = platform.words_to_bits([0x0000_000D], "msb")
        self.assertEqual(list(bits[-4:]), [1, 1, 0, 1])
        self.assertEqual(len(bits), 32)

    def test_chronological_bit_packing(self):
        bits = bytearray([1, 0, 1, 1, 0, 0, 1, 0])
        self.assertEqual(platform.pack_chronological_bits(bits), bytes([0xB2]))

    def test_invalid_words_are_not_silently_masked(self):
        invalid_values = [-1, 0x1_0000_0000, True, 1.5]
        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    platform.words_to_bits([value])

    def test_generate_words_validates_public_output_width(self):
        valid = SimpleNamespace(next_u32=lambda: 0x89AB_CDEF)
        self.assertEqual(
            platform.generate_words(valid, 2),
            [0x89AB_CDEF, 0x89AB_CDEF],
        )

        invalid = SimpleNamespace(next_u32=lambda: 0x1_0000_0000)
        with self.assertRaises(ValueError):
            platform.generate_words(invalid, 1)


class TestStatisticalFormulas(unittest.TestCase):
    def test_monobit_known_values(self):
        balanced = platform.monobit_test(bytearray([0, 1] * 4), 0.01)
        self.assertAlmostEqual(balanced.statistic, 0.0)
        self.assertAlmostEqual(balanced.p_value, 1.0)

        all_zero = platform.monobit_test(bytearray([0] * 8), 0.01)
        self.assertAlmostEqual(
            all_zero.p_value,
            0.004677734981047265,
            places=15,
        )

    def test_runs_known_values_and_precondition(self):
        four_runs = platform.runs_test(bytearray([0, 0, 1, 1, 0, 0, 1, 1]), 0.01)
        self.assertTrue(four_runs.applicable)
        self.assertEqual(four_runs.statistic, 4.0)
        self.assertAlmostEqual(four_runs.p_value, 1.0)

        alternating = platform.runs_test(bytearray([0, 1] * 4), 0.01)
        self.assertTrue(alternating.applicable)
        self.assertEqual(alternating.statistic, 8.0)
        self.assertAlmostEqual(
            alternating.p_value,
            0.004677734981047265,
            places=15,
        )

        biased = platform.runs_test(bytearray([0] * 1_000), 0.01)
        self.assertFalse(biased.applicable)
        self.assertIsNone(biased.p_value)

    def test_autocorrelation_known_value(self):
        alternating = bytearray([0, 1] * 4)
        result = platform.autocorrelation_test(alternating, lag=1, alpha=0.01)
        self.assertEqual(result.details["disagreements"], 7)
        self.assertAlmostEqual(result.details["correlation_estimate"], -1.0)
        self.assertAlmostEqual(
            result.p_value,
            0.008150971593502702,
            places=15,
        )

        for invalid_lag in (0, -1, len(alternating)):
            with self.subTest(lag=invalid_lag):
                with self.assertRaises(ValueError):
                    platform.autocorrelation_test(
                        alternating,
                        lag=invalid_lag,
                        alpha=0.01,
                    )

        with self.assertRaises(TypeError):
            platform.autocorrelation_test(alternating, lag=True, alpha=0.01)

    def test_regularized_gamma_q_against_closed_forms(self):
        # Chi-square df=2 survival: exp(-x/2).
        self.assertAlmostEqual(
            platform.regularized_gamma_q(1.0, 1.0),
            math.exp(-1.0),
            places=13,
        )
        # Chi-square df=4 survival at x=4: exp(-2) * (1 + 2).
        self.assertAlmostEqual(
            platform.regularized_gamma_q(2.0, 2.0),
            3.0 * math.exp(-2.0),
            places=13,
        )
        # Trusted SciPy gammaincc values at the actual chi-square a=127.5,
        # exercising both the series and continued-fraction branches.
        self.assertAlmostEqual(
            platform.regularized_gamma_q(127.5, 100.0),
            0.99542544454195192,
            places=13,
        )
        self.assertAlmostEqual(
            platform.regularized_gamma_q(127.5, 150.0),
            0.027727522053904829,
            places=13,
        )

    def test_byte_chi_square_known_counts(self):
        uniform = bytes(range(256))
        uniform_result, counts = platform.byte_chi_square_test(uniform, 0.01)
        self.assertEqual(uniform_result.statistic, 0.0)
        self.assertEqual(uniform_result.p_value, 1.0)
        self.assertEqual(counts, [1] * 256)
        # The approximation condition is intentionally false with one per bin.
        self.assertFalse(uniform_result.applicable)

        all_zero = bytes([0] * 256)
        zero_result, _ = platform.byte_chi_square_test(all_zero, 0.01)
        self.assertEqual(zero_result.statistic, 65_280.0)
        self.assertLessEqual(zero_result.p_value, 1.0e-100)


class TestMultipleTestingCorrection(unittest.TestCase):
    @staticmethod
    def make_result(p_value: float) -> platform.StatisticalResult:
        return platform.StatisticalResult(
            test="demo",
            parameter="-",
            statistic_name="z",
            statistic=0.0,
            p_value=p_value,
            adjusted_p_value=None,
            alpha=0.01,
            applicable=True,
            passed=None,
            details={},
        )

    def test_holm_bonferroni_adjusted_values(self):
        results = [self.make_result(value) for value in (0.001, 0.02, 0.04)]
        report = platform.GeneratorReport(
            key="demo",
            display_name="Demo",
            module_path="demo.py",
            class_name="Demo",
            seed=platform.COMMON_SEED,
            word_count=320,
            bit_count=10_240,
            bit_order="lsb",
            ones=5_120,
            zeros=5_120,
            byte_counts=[5] * 256,
            results=results,
        )
        platform.apply_holm_bonferroni([report], 0.01)

        self.assertAlmostEqual(results[0].adjusted_p_value, 0.003)
        self.assertAlmostEqual(results[1].adjusted_p_value, 0.04)
        self.assertAlmostEqual(results[2].adjusted_p_value, 0.04)
        self.assertFalse(results[0].passed)
        self.assertTrue(results[1].passed)
        self.assertTrue(results[2].passed)
        self.assertFalse(report.overall_passed)


class TestCoreLoading(unittest.TestCase):
    def test_known_available_cores_and_first_words(self):
        expected = {
            "xoroshiro64ss": 0x4F7C_C6BB,
            "pcg32_oneseq": 0x2468_A5EB,
        }
        for key, expected_word in expected.items():
            with self.subTest(generator=key):
                generator, module_path, class_name = platform.instantiate_generator(
                    platform.CORE_DEFINITIONS[key],
                    platform.COMMON_SEED,
                )
                self.assertEqual(generator.next_u32(), expected_word)
                self.assertTrue(Path(module_path).is_file())
                self.assertTrue(class_name)

    def test_lfsr_first_word_when_core_is_present(self):
        try:
            generator, module_path, class_name = platform.instantiate_generator(
                platform.CORE_DEFINITIONS["lfsr64"],
                platform.COMMON_SEED,
            )
        except FileNotFoundError:
            self.skipTest("lfsr64_core.py is not present in this workspace")

        self.assertEqual(generator.next_u32(), 0x89AB_CDEF)
        self.assertTrue(Path(module_path).is_file())
        self.assertTrue(class_name)

    def test_single_compatible_class_fallback(self):
        module = ModuleType("demo_fallback_module")

        class UnusualName:
            def next_u32(self):
                return 0

        UnusualName.__module__ = module.__name__
        module.UnusualName = UnusualName
        resolved = platform.resolve_generator_class(module, ("MissingName",))
        self.assertIs(resolved, UnusualName)


class TestCommandLineValidation(unittest.TestCase):
    def test_duplicate_generator_keys_are_rejected(self):
        parser = platform.build_argument_parser()
        arguments = parser.parse_args(
            ["--generators", "lfsr64", "lfsr64"]
        )
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                platform.validate_arguments(arguments, parser)

    def test_lag_must_leave_at_least_100_pairs(self):
        parser = platform.build_argument_parser()
        # Minimum stream has 10,240 bits; lag 10,141 leaves only 99 pairs.
        arguments = parser.parse_args(["--words", "320", "--lags", "10141"])
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                platform.validate_arguments(arguments, parser)


class TestReportsAndPlots(unittest.TestCase):
    def make_report(self) -> platform.GeneratorReport:
        packed = bytes(range(256)) * 5
        bits = bits_from_msb_first_bytes(packed)
        results, counts = platform.evaluate_bitstream(
            bits,
            alpha=0.01,
            lags=(1, 2, 7),
        )
        report = platform.GeneratorReport(
            key="demo",
            display_name="Demo",
            module_path="demo.py",
            class_name="DemoGenerator",
            seed=platform.COMMON_SEED,
            word_count=len(bits) // 32,
            bit_count=len(bits),
            bit_order="lsb",
            ones=sum(bits),
            zeros=len(bits) - sum(bits),
            byte_counts=counts,
            results=results,
        )
        platform.apply_holm_bonferroni([report], 0.01)
        return report

    def test_csv_and_json_outputs_are_deterministic(self):
        report = self.make_report()
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            detailed = directory / "detailed.csv"
            summary = directory / "summary.csv"
            json_path = directory / "results.json"

            platform.write_detailed_csv([report], detailed)
            platform.write_summary_csv([report], summary)
            platform.write_json_report([report], json_path, 0.01, (1, 2, 7))
            first_contents = (
                detailed.read_bytes(),
                summary.read_bytes(),
                json_path.read_bytes(),
            )

            platform.write_detailed_csv([report], detailed)
            platform.write_summary_csv([report], summary)
            platform.write_json_report([report], json_path, 0.01, (1, 2, 7))
            second_contents = (
                detailed.read_bytes(),
                summary.read_bytes(),
                json_path.read_bytes(),
            )

            self.assertEqual(first_contents, second_contents)
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["common_seed"], "0x0123456789ABCDEF")
            self.assertEqual(payload["bit_order_within_each_word"], "lsb")
            self.assertEqual(len(payload["generators"][0]["byte_counts"]), 256)

    @unittest.skipUnless(
        importlib.util.find_spec("matplotlib") is not None,
        "Matplotlib is not installed",
    )
    def test_plot_files_are_valid_pngs(self):
        report = self.make_report()
        with tempfile.TemporaryDirectory() as temporary_directory:
            paths = platform.write_plots([report], Path(temporary_directory))
            self.assertEqual(len(paths), 3)
            for path in paths:
                with self.subTest(path=path.name):
                    self.assertGreater(path.stat().st_size, 100)
                    self.assertEqual(
                        path.read_bytes()[:8],
                        b"\x89PNG\r\n\x1a\n",
                    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
