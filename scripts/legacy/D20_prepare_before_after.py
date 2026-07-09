from pathlib import Path
import json
import shutil

import pandas as pd
import matplotlib.pyplot as plt


MTF_COLS = ["mtf_30_avg", "mtf_40_avg", "mtf_50_avg"]


def load_json(json_path):
    json_path = Path(json_path)

    if not json_path.exists():
        raise FileNotFoundError(f"Cannot find JSON file: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data


def load_csv(csv_path):
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"Cannot find CSV file: {csv_path}")

    df = pd.read_csv(csv_path)

    return df


def normalize_case_index(df):
    """
    把 case_index 转成整数，方便跨 CSV 匹配。
    """
    df = df.copy()
    df["case_index_int"] = pd.to_numeric(df["case_index"], errors="coerce").astype("Int64")
    return df


def prepare_scored_df(df):
    """
    确保 D19 的评分表中关键列都是数值。
    """
    df = normalize_case_index(df)

    numeric_cols = [
        "delta_mm",
        "actual_thickness_mm",
        "mtf_30_avg",
        "mtf_40_avg",
        "mtf_50_avg",
        "final_score",
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["case_index_int", "delta_mm", "actual_thickness_mm"] + MTF_COLS)

    return df


def find_initial_case(scored_df):
    """
    找初始设计。
    这里把 delta 最接近 0 的 case 作为 initial/before。
    """
    idx = scored_df["delta_mm"].abs().idxmin()
    return scored_df.loc[idx]


def find_best_case(scored_df, best_json):
    """
    优先根据 best_design.json 中的 case_index 找最佳设计。
    如果找不到，就回退到 final_score 最大的行。
    """
    best_case = best_json.get("best_case", {})
    best_case_index = best_case.get("case_index", None)

    if best_case_index is not None:
        best_case_index = int(best_case_index)
        matched = scored_df[scored_df["case_index_int"] == best_case_index]

        if len(matched) > 0:
            return matched.iloc[0]

    idx = scored_df["final_score"].idxmax()
    return scored_df.loc[idx]


def find_case_in_d16_summary(d16_df, case_index):
    """
    根据 case_index 在 D16_sweep_summary.csv 中找到对应文件路径。
    """
    d16_df = normalize_case_index(d16_df)
    matched = d16_df[d16_df["case_index_int"] == int(case_index)]

    if len(matched) == 0:
        raise ValueError(f"Cannot find case_index={case_index} in D16 summary.")

    return matched.iloc[0]


def copy_if_exists(src_path, dst_path):
    """
    如果源文件存在，就复制到目标位置。
    如果不存在，只打印提示，不中断整个流程。
    """
    if src_path is None or str(src_path).strip() == "":
        print("Skip empty path:", dst_path)
        return False

    src_path = Path(str(src_path))
    dst_path = Path(dst_path)
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    if not src_path.exists():
        print("Source file does not exist:", src_path)
        return False

    shutil.copy2(src_path, dst_path)
    print("Copied:", src_path, "->", dst_path)
    return True


def copy_case_files(d16_row, output_dir, prefix):
    """
    复制某个 case 的模型、LDE、MTF、Spot 文件。
    prefix 可以是 initial 或 best。
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    copied = {}

    copied["model"] = copy_if_exists(
        d16_row.get("model_path", ""),
        output_dir / f"{prefix}_model.zmx"
    )

    copied["lde_csv"] = copy_if_exists(
        d16_row.get("lde_csv_path", ""),
        output_dir / f"{prefix}_lde.csv"
    )

    copied["mtf_txt"] = copy_if_exists(
        d16_row.get("mtf_txt_path", ""),
        output_dir / f"{prefix}_fft_mtf.txt"
    )

    copied["spot_txt"] = copy_if_exists(
        d16_row.get("spot_txt_path", ""),
        output_dir / f"{prefix}_standard_spot.txt"
    )

    return copied


def build_before_after_metrics(initial_row, best_row):
    """
    生成 before/after 对比表。
    """
    rows = []

    rows.append({
        "design": "initial",
        "case_index": int(initial_row["case_index_int"]),
        "delta_mm": initial_row["delta_mm"],
        "actual_thickness_mm": initial_row["actual_thickness_mm"],
        "mtf_30_avg": initial_row["mtf_30_avg"],
        "mtf_40_avg": initial_row["mtf_40_avg"],
        "mtf_50_avg": initial_row["mtf_50_avg"],
        "final_score": initial_row.get("final_score", ""),
    })

    rows.append({
        "design": "best",
        "case_index": int(best_row["case_index_int"]),
        "delta_mm": best_row["delta_mm"],
        "actual_thickness_mm": best_row["actual_thickness_mm"],
        "mtf_30_avg": best_row["mtf_30_avg"],
        "mtf_40_avg": best_row["mtf_40_avg"],
        "mtf_50_avg": best_row["mtf_50_avg"],
        "final_score": best_row.get("final_score", ""),
    })

    return pd.DataFrame(rows)


def calculate_improvement(initial_row, best_row):
    """
    计算 best 相对 initial 的提升百分比。
    """
    improvement = {}

    for col in MTF_COLS + ["final_score"]:
        initial_value = float(initial_row[col])
        best_value = float(best_row[col])

        if abs(initial_value) < 1e-12:
            improvement[col + "_improvement_percent"] = None
        else:
            improvement[col + "_improvement_percent"] = (best_value - initial_value) / initial_value * 100

    return improvement


def plot_before_after_bar(metrics_df, output_path):
    """
    画 before/after 的 MTF 柱状对比图。
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    initial = metrics_df[metrics_df["design"] == "initial"].iloc[0]
    best = metrics_df[metrics_df["design"] == "best"].iloc[0]

    labels = ["MTF@30", "MTF@40", "MTF@50"]
    initial_values = [initial["mtf_30_avg"], initial["mtf_40_avg"], initial["mtf_50_avg"]]
    best_values = [best["mtf_30_avg"], best["mtf_40_avg"], best["mtf_50_avg"]]

    x = list(range(len(labels)))
    width = 0.35

    plt.figure(figsize=(7, 5))

    plt.bar([i - width / 2 for i in x], initial_values, width, label="Initial")
    plt.bar([i + width / 2 for i in x], best_values, width, label="Best")

    plt.xticks(x, labels)
    plt.ylabel("Average MTF")
    plt.title("D20 Before/After MTF Comparison")
    plt.ylim(0, 1.05)
    plt.grid(True, axis="y")
    plt.legend()
    plt.tight_layout()

    plt.savefig(output_path, dpi=300)
    plt.close()

    print("Saved before/after MTF bar figure:", output_path)


def write_summary_md(initial_row, best_row, improvement, output_path):
    """
    写 D20 的 markdown 总结。
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# D20 Before/After Comparison Summary")
    lines.append("")
    lines.append("## Comparison target")
    lines.append("")
    lines.append("- Initial design: delta closest to 0 mm")
    lines.append("- Best design: selected from D19 `best_design.json`")
    lines.append("- Current criterion: MTF-only weighted score")
    lines.append("")
    lines.append("## Initial design")
    lines.append("")
    lines.append(f"- case_index: {int(initial_row['case_index_int'])}")
    lines.append(f"- delta_mm: {initial_row['delta_mm']}")
    lines.append(f"- actual_thickness_mm: {initial_row['actual_thickness_mm']}")
    lines.append(f"- mtf_30_avg: {initial_row['mtf_30_avg']}")
    lines.append(f"- mtf_40_avg: {initial_row['mtf_40_avg']}")
    lines.append(f"- mtf_50_avg: {initial_row['mtf_50_avg']}")
    lines.append(f"- final_score: {initial_row['final_score']}")
    lines.append("")
    lines.append("## Best design")
    lines.append("")
    lines.append(f"- case_index: {int(best_row['case_index_int'])}")
    lines.append(f"- delta_mm: {best_row['delta_mm']}")
    lines.append(f"- actual_thickness_mm: {best_row['actual_thickness_mm']}")
    lines.append(f"- mtf_30_avg: {best_row['mtf_30_avg']}")
    lines.append(f"- mtf_40_avg: {best_row['mtf_40_avg']}")
    lines.append(f"- mtf_50_avg: {best_row['mtf_50_avg']}")
    lines.append(f"- final_score: {best_row['final_score']}")
    lines.append("")
    lines.append("## Improvement")
    lines.append("")

    for key, value in improvement.items():
        if value is None:
            lines.append(f"- {key}: N/A")
        else:
            lines.append(f"- {key}: {value:.2f}%")

    lines.append("")
    lines.append("## Note")
    lines.append("")
    lines.append("This before/after comparison is based on the current MTF-only score. A more rigorous optical evaluation should also include RMS Spot, field-dependent metrics, Tangential/Sagittal curves, distortion, and focal length constraints.")

    output_path.write_text("\n".join(lines), encoding="utf-8")

    print("Saved D20 summary markdown:", output_path)


def main():
    print("===== D20 Before/After Preparation Started =====")

    project_dir = Path(__file__).resolve().parents[1]

    d16_summary_csv = project_dir / "results" / "D16_thickness_sweep" / "D16_sweep_summary.csv"
    d19_scored_csv = project_dir / "results" / "D19_best_design" / "D19_scored_results.csv"
    best_json_path = project_dir / "results" / "D19_best_design" / "best_design.json"

    output_dir = project_dir / "results" / "D20_before_after"
    before_dir = output_dir / "before"
    after_dir = output_dir / "after"

    metrics_csv = output_dir / "D20_before_after_metrics.csv"
    bar_fig = output_dir / "D20_mtf_before_after_bar.png"
    summary_md = output_dir / "D20_before_after_summary.md"

    d16_df = load_csv(d16_summary_csv)
    scored_df = load_csv(d19_scored_csv)
    best_json = load_json(best_json_path)

    scored_df = prepare_scored_df(scored_df)

    initial_row = find_initial_case(scored_df)
    best_row = find_best_case(scored_df, best_json)

    initial_d16_row = find_case_in_d16_summary(d16_df, initial_row["case_index_int"])
    best_d16_row = find_case_in_d16_summary(d16_df, best_row["case_index_int"])

    before_dir.mkdir(parents=True, exist_ok=True)
    after_dir.mkdir(parents=True, exist_ok=True)

    copy_case_files(initial_d16_row, before_dir, prefix="initial")
    copy_case_files(best_d16_row, after_dir, prefix="best")

    metrics_df = build_before_after_metrics(initial_row, best_row)
    metrics_df.to_csv(metrics_csv, index=False, encoding="utf-8-sig")
    print("Saved before/after metrics CSV:", metrics_csv)

    improvement = calculate_improvement(initial_row, best_row)

    plot_before_after_bar(metrics_df, bar_fig)
    write_summary_md(initial_row, best_row, improvement, summary_md)

    print("\nInitial case:")
    print(metrics_df[metrics_df["design"] == "initial"])

    print("\nBest case:")
    print(metrics_df[metrics_df["design"] == "best"])

    print("\n===== D20 Before/After Preparation Finished =====")


if __name__ == "__main__":
    main()