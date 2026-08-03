"""Day 6: compare the latest focused baseline and Case 002 Spot text."""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.zemax.analysis_ops import (  # noqa: E402
    parse_standard_spot_text,
)


SPOT_ROOT = PROJECT_ROOT / "outputs" / "day6_quick_focus"


def newest_file(pattern):
    """Return the newest result matching one controlled output pattern."""

    matches = list(SPOT_ROOT.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No Spot text matches: {pattern}")
    return max(matches, key=lambda path: path.stat().st_mtime)


def main():
    baseline_file = newest_file(
        "baseline_focus_check_*/case_003_standard_spot_raw.txt"
    )
    case_002_file = newest_file(
        "case_002_focus_check_*/case_002_standard_spot_raw.txt"
    )

    baseline = parse_standard_spot_text(baseline_file)
    case_002 = parse_standard_spot_text(case_002_file)

    if baseline["reference"] != "质心" or case_002["reference"] != "质心":
        raise ValueError("Both Spot results must use the centroid reference.")

    if baseline["field_count"] != case_002["field_count"]:
        raise ValueError("The two Spot results have different field counts.")

    rows = []
    for base_field, offset_field in zip(
        baseline["fields"],
        case_002["fields"],
    ):
        if base_field["field_y_degree"] != offset_field["field_y_degree"]:
            raise ValueError("The two Spot results use different fields.")

        rms_delta = (
            offset_field["rms_radius_um"] - base_field["rms_radius_um"]
        )
        maximum_delta = (
            offset_field["maximum_radius_um"]
            - base_field["maximum_radius_um"]
        )
        rms_percent = 100.0 * rms_delta / base_field["rms_radius_um"]

        rows.append(
            {
                "field_y_degree": base_field["field_y_degree"],
                "baseline_rms_um": base_field["rms_radius_um"],
                "case_002_rms_um": offset_field["rms_radius_um"],
                "rms_delta_um": rms_delta,
                "rms_change_percent": rms_percent,
                "baseline_maximum_um": base_field["maximum_radius_um"],
                "case_002_maximum_um": offset_field["maximum_radius_um"],
                "maximum_delta_um": maximum_delta,
                "rms_outcome": "improved" if rms_delta < 0 else "worsened",
            }
        )

    comparison = {
        "task": "day6_focused_spot_comparison",
        "time_local": datetime.now().astimezone().isoformat(),
        "reference": "centroid",
        "unit": "um",
        "baseline_source": str(baseline_file),
        "case_002_source": str(case_002_file),
        "fields": rows,
    }

    output_dir = SPOT_ROOT / "comparisons"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = output_dir / f"spot_comparison_{timestamp}.json"
    csv_file = output_dir / f"spot_comparison_{timestamp}.csv"

    json_file.write_text(
        json.dumps(comparison, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    with csv_file.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print("========== DAY 6 FOCUSED SPOT COMPARISON ==========")
    for row in rows:
        print(
            f"Field {row['field_y_degree']:.1f} deg: "
            f"{row['baseline_rms_um']:.3f} -> "
            f"{row['case_002_rms_um']:.3f} um, "
            f"change {row['rms_change_percent']:+.1f}% "
            f"({row['rms_outcome']})"
        )

    print(f"[PASS] JSON comparison: {json_file}")
    print(f"[PASS] CSV comparison: {csv_file}")


if __name__ == "__main__":
    main()
