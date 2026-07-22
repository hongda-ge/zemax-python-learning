from pathlib import Path
import csv
import re


TARGET_FREQS = [30, 40, 50]


def read_text_auto(path):
    """
    自动尝试几种编码读取 Zemax 导出的 txt。
    """
    path = Path(path)

    encodings = ["utf-8-sig", "utf-16", "gbk", "latin1"]

    for enc in encodings:
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            pass

    return path.read_text(errors="ignore")


def extract_numeric_rows_from_mtf_txt(text):
    """
    从 Zemax FFT MTF txt 中提取频率-MTF数据。

    支持格式:

    空间频率    子午    弧矢

    0.000000  1.000000  1.000000
    5.000000  0.898800  0.898800
    ...

    返回:
    [
        [freq, mtf1, mtf2],
        ...
    ]
    """

    rows = []

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        # 只处理纯数字行
        nums = re.findall(
            r"[-+]?\d*\.\d+(?:[Ee][-+]?\d+)?",
            line
        )

        # FFT MTF 数据至少三列
        if len(nums) < 3:
            continue


        values = [
            float(x)
            for x in nums
        ]


        freq = values[0]
        mtf_values = values[1:]


        # 过滤
        #
        # 空间频率:
        # 0~200 lp/mm
        #
        # MTF:
        # 0~1
        #
        if not (0 <= freq <= 200):
            continue


        if not all(
            -0.05 <= x <= 1.05
            for x in mtf_values
        ):
            continue


        rows.append(values)


    rows.sort(
        key=lambda x:x[0]
    )


    return rows


def find_nearest_mtf(rows, target_freq):
    """
    找到最接近 target_freq 的频率点，并返回平均 MTF。
    """
    if not rows:
        return {
            "nearest_freq": "",
            "mtf_avg": "",
            "mtf_min": "",
            "mtf_max": "",
            "n_curves": 0,
        }

    nearest_row = min(rows, key=lambda r: abs(r[0] - target_freq))

    nearest_freq = nearest_row[0]
    mtf_values = nearest_row[1:]

    mtf_avg = sum(mtf_values) / len(mtf_values)
    mtf_min = min(mtf_values)
    mtf_max = max(mtf_values)

    return {
        "nearest_freq": nearest_freq,
        "mtf_avg": mtf_avg,
        "mtf_min": mtf_min,
        "mtf_max": mtf_max,
        "n_curves": len(mtf_values),
    }


def extract_mtf_metrics(mtf_txt_path):
    """
    从单个 MTF txt 文件中提取 30/40/50 lp/mm 附近的 MTF 指标。
    """
    mtf_txt_path = Path(mtf_txt_path)

    if not mtf_txt_path.exists():
        raise FileNotFoundError(f"MTF txt not found: {mtf_txt_path}")

    text = read_text_auto(mtf_txt_path)
    rows = extract_numeric_rows_from_mtf_txt(text)

    metrics = {}

    for freq in TARGET_FREQS:
        result = find_nearest_mtf(rows, freq)

        metrics[f"mtf_{freq}_nearest_freq"] = result["nearest_freq"]
        metrics[f"mtf_{freq}_avg"] = result["mtf_avg"]
        metrics[f"mtf_{freq}_min"] = result["mtf_min"]
        metrics[f"mtf_{freq}_max"] = result["mtf_max"]
        metrics[f"mtf_{freq}_n_curves"] = result["n_curves"]

    metrics["mtf_rows_found"] = len(rows)

    return metrics


def main():
    print("===== D17 MTF Metric Extraction Started =====")

    project_dir = Path(__file__).resolve().parents[2]

    d16_summary_csv = project_dir / "results" / "archive" /"D16_thickness_sweep" / "D16_sweep_summary.csv"
    output_dir = project_dir / "results"/ "archive" / "D17_metric_extraction"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_csv = output_dir / "sweep_results.csv"

    if not d16_summary_csv.exists():
        raise FileNotFoundError(f"D16 summary CSV not found: {d16_summary_csv}")

    results = []

    with open(d16_summary_csv, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            case_index = row.get("case_index", "")
            delta_mm = row.get("delta_mm", "")
            actual_thickness_mm = row.get("actual_thickness_mm", "")
            status = row.get("status", "")

            mtf_txt_path = project_dir / row.get("mtf_txt_path", "")
            spot_txt_path = row.get("spot_txt_path", "")

            print(f"\nProcessing case {case_index}, delta = {delta_mm}")

            output_row = {
                "case_index": case_index,
                "delta_mm": delta_mm,
                "actual_thickness_mm": actual_thickness_mm,
                "d16_status": status,
                "mtf_txt_path": mtf_txt_path,
                "spot_txt_path": spot_txt_path,
                "metric_status": "success",
                "metric_error": "",
            }

            try:
                if status != "success":
                    raise RuntimeError(f"D16 case status is not success: {status}")

                mtf_metrics = extract_mtf_metrics(mtf_txt_path)
                output_row.update(mtf_metrics)

            except Exception as e:
                output_row["metric_status"] = "failed"
                output_row["metric_error"] = str(e)

                for freq in TARGET_FREQS:
                    output_row[f"mtf_{freq}_nearest_freq"] = ""
                    output_row[f"mtf_{freq}_avg"] = ""
                    output_row[f"mtf_{freq}_min"] = ""
                    output_row[f"mtf_{freq}_max"] = ""
                    output_row[f"mtf_{freq}_n_curves"] = ""

                output_row["mtf_rows_found"] = ""

                print("Failed:", e)

            results.append(output_row)

    fieldnames = [
        "case_index",
        "delta_mm",
        "actual_thickness_mm",
        "d16_status",
        "metric_status",
        "metric_error",
        "mtf_30_nearest_freq",
        "mtf_30_avg",
        "mtf_30_min",
        "mtf_30_max",
        "mtf_30_n_curves",
        "mtf_40_nearest_freq",
        "mtf_40_avg",
        "mtf_40_min",
        "mtf_40_max",
        "mtf_40_n_curves",
        "mtf_50_nearest_freq",
        "mtf_50_avg",
        "mtf_50_min",
        "mtf_50_max",
        "mtf_50_n_curves",
        "mtf_rows_found",
        "mtf_txt_path",
        "spot_txt_path",
    ]

    with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print("\nD17 sweep results saved to:", output_csv)
    print("Total cases:", len(results))
    print("===== D17 MTF Metric Extraction Finished =====")


if __name__ == "__main__":
    main()