"""Small offline regression suite for the interview-ready workflow."""

import tempfile
import unittest
from pathlib import Path

from modules.zemax.install_paths import discover_zemax_install_dir
from scripts.demos.day25_validate_baseline_control import (
    evaluate_balanced,
    evaluate_balanced_checks,
)


class InstallPathTests(unittest.TestCase):
    def test_explicit_environment_override_wins(self):
        expected = Path(r"X:\OpticStudio")
        self.assertEqual(
            discover_zemax_install_dir(str(expected), candidates=()),
            expected,
        )

    def test_first_complete_candidate_is_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            incomplete = root / "incomplete"
            complete = root / "complete"
            incomplete.mkdir()
            complete.mkdir()
            for name in ("ZOSAPI_NetHelper.dll", "ZOSAPI.dll", "ZOSAPI_Interfaces.dll"):
                (complete / name).touch()
            self.assertEqual(
                discover_zemax_install_dir("", candidates=(incomplete, complete)),
                complete,
            )


class BalancedAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "balanced_acceptance": {
                "limits": {
                    "spot_mean_rms_um_max": 11.3,
                    "spot_worst_rms_um_max": 16.5,
                    "mtf30_minimum_min": 0.16,
                    "mtf50_minimum_min": 0.05,
                }
            }
        }

    def test_batch_checks_record_failure_without_raising(self):
        observed = {
            "spot_mean_rms_um": 11.14,
            "spot_worst_rms_um": 16.30,
            "mtf30_minimum": 0.156,
            "mtf50_minimum": 0.048,
        }
        checks = evaluate_balanced_checks(self.config, observed)
        self.assertEqual(
            checks,
            {
                "spot_mean": True,
                "spot_worst": True,
                "mtf30_minimum": False,
                "mtf50_minimum": False,
            },
        )

    def test_zero_control_still_requires_all_checks(self):
        observed = {
            "spot_mean_rms_um": 11.14,
            "spot_worst_rms_um": 16.30,
            "mtf30_minimum": 0.156,
            "mtf50_minimum": 0.048,
        }
        with self.assertRaises(ValueError):
            evaluate_balanced(self.config, observed)


if __name__ == "__main__":
    unittest.main()
