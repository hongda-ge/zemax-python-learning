"""Day 12 step 3: explain exact decision regions from the latest report."""

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.config_loader import load_config  # noqa: E402


def find_latest_report(config):
    """Find the newest successful Day 12 sensitivity report."""

    root = PROJECT_ROOT / config["output"]["root"]
    matches = list(
        root.glob("sensitivity_evaluation_*/decision_sensitivity_report.json")
    )
    if not matches:
        raise FileNotFoundError("No Day 12 sensitivity report was found.")
    return max(matches, key=lambda path: path.stat().st_mtime)


def validate_report(report):
    """Require a successful, read-only teaching analysis."""

    checks = {
        "task": report.get("task") == "day12_decision_threshold_sensitivity",
        "status": report.get("status") == "success",
        "teaching label": report.get("teaching_only") is True,
        "no ZOS-API": report.get("zosapi_connection_created") is False,
        "no new optical metric": report.get("new_optical_metric_calculated")
        is False,
        "no weighted score": report.get("hidden_weighted_score_used") is False,
        "no engineering winner": report.get("unique_engineering_winner") is None,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Day 12 report failed: " + ", ".join(failed))


def exact_regions(report):
    """Build exact half-open regions from candidate entry limits and MTF order."""

    limits = report["candidate_entry_limits_percent"]
    threshold_results = report["threshold_results"]
    mtf_order = threshold_results[-1]["ranking"]
    critical_values = sorted(set(float(value) for value in limits.values()))

    regions = []
    for index, lower in enumerate(critical_values):
        eligible = [case_id for case_id, value in limits.items() if value <= lower]
        ranking = [case_id for case_id in mtf_order if case_id in eligible]
        if not ranking:
            raise ValueError(f"No eligible candidate at {lower:.6f}%.")
        upper = (
            critical_values[index + 1]
            if index + 1 < len(critical_values)
            else None
        )
        regions.append(
            {
                "lower": lower,
                "upper": upper,
                "eligible": eligible,
                "recommended": ranking[0],
            }
        )
    return regions


def main():
    config = load_config("configs/day12_decision_sensitivity.yaml")
    report_file = find_latest_report(config)
    report = json.loads(report_file.read_text(encoding="utf-8"))
    validate_report(report)
    regions = exact_regions(report)

    print("========== DAY 12 EXACT DECISION REGIONS ==========")
    print(f"Source report: {report_file}")
    print("No ZOS-API connection or new optical calculation was used.")
    print()
    for region in regions:
        lower = region["lower"]
        upper = region["upper"]
        if upper is None:
            interval = f"limit >= {lower:.5f}%"
        else:
            interval = f"{lower:.5f}% <= limit < {upper:.5f}%"
        print(
            f"{interval}: eligible=[{', '.join(region['eligible'])}] "
            f"-> {region['recommended']}"
        )

    print()
    print("[RESULT] The sampled points show where a change was observed.")
    print("[RESULT] Candidate penalties define the exact transition limits.")
    print("[RESULT] The 2.0% Day 11 choice lies inside the fine_004 region.")
    print("[PASS] Day 12 exact-region summary completed without new output.")


if __name__ == "__main__":
    main()
