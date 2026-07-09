from pathlib import Path
import json

import pandas as pd
import matplotlib.pyplot as plt


WEIGHTS = {
    "mtf_30_avg": 0.3,
    "mtf_40_avg": 0.3,
    "mtf_50_avg": 0.4,
}


def load_clean_results(csv_path):
    """
    读取 D18 清洗后的 CSV。
    """
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"Cannot find clean results CSV: {csv_path}")

    df = pd.read_csv(csv_path)

    print("Loaded clean results:", csv_path)
    print("Rows:", len(df))
    print("Columns:", list(df.columns))

    return df


def prepare_numeric_data(df):
    """
    确保关键列都是数字，并去掉无效行。
    """
    df = df.copy()

    numeric_cols = [
        "delta_mm",
        "actual_thickness_mm",
        "mtf_30_avg",
        "mtf_40_avg",
        "mtf_50_avg",
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=numeric_cols)
    df = df.sort_values("actual_thickness_mm")

    print("Valid rows after numeric cleaning:", len(df))

    if len(df) == 0:
        raise ValueError("No valid rows after cleaning. Please check D18_clean_sweep_results.csv.")

    return df


def calculate_score(df):
    """
    根据 MTF@30/40/50 计算综合评分。

    当前 D19 是 MTF-only 版本：
    score = 0.3*MTF30 + 0.3*MTF40 + 0.4*MTF50
    """
    df = df.copy()

    df["mtf_score"] = (
        WEIGHTS["mtf_30_avg"] * df["mtf_30_avg"]
        + WEIGHTS["mtf_40_avg"] * df["mtf_40_avg"]
        + WEIGHTS["mtf_50_avg"] * df["mtf_50_avg"]
    )

    # 预留字段：以后加入 RMS Spot 后，可以在这里加入 penalty
    df["spot_penalty"] = 0.0
    df["final_score"] = df["mtf_score"] - df["spot_penalty"]

    return df


def select_best_design(df):
    """
    选择 final_score 最大的那一组。
    """
    best_index = df["final_score"].idxmax()
    best_row = df.loc[best_index]

    return best_row


def save_scored_results(df, output_path):
    """
    保存包含 score 的完整结果表。
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print("Saved scored results:", output_path)


def save_top_cases(df, output_path, top_n=5):
    """
    保存排名前 N 的结果。
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    top_df = df.sort_values("final_score", ascending=False).head(top_n)
    top_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"Saved top {top_n} cases:", output_path)

    return top_df


def to_python_number(value):
    """
    将 pandas/numpy 数值转换为普通 Python 数值，方便写入 JSON。
    """
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass

    if hasattr(value, "item"):
        return value.item()

    return value


def save_best_design_json(best_row, output_path):
    """
    保存最佳设计结果到 JSON。
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    best_design = {
        "task": "D19_best_design_selection",
        "selection_method": "MTF-only weighted score",
        "score_formula": "final_score = 0.3*mtf_30_avg + 0.3*mtf_40_avg + 0.4*mtf_50_avg",
        "note": "Spot penalty is reserved for future update. Current selection is based on averaged MTF metrics only.",
        "weights": WEIGHTS,
        "best_case": {
            "case_index": to_python_number(best_row.get("case_index")),
            "delta_mm": to_python_number(best_row.get("delta_mm")),
            "actual_thickness_mm": to_python_number(best_row.get("actual_thickness_mm")),
            "mtf_30_avg": to_python_number(best_row.get("mtf_30_avg")),
            "mtf_40_avg": to_python_number(best_row.get("mtf_40_avg")),
            "mtf_50_avg": to_python_number(best_row.get("mtf_50_avg")),
            "mtf_score": to_python_number(best_row.get("mtf_score")),
            "spot_penalty": to_python_number(best_row.get("spot_penalty")),
            "final_score": to_python_number(best_row.get("final_score")),
            "mtf_txt_path": to_python_number(best_row.get("mtf_txt_path")),
            "spot_txt_path": to_python_number(best_row.get("spot_txt_path")),
        },
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(best_design, f, indent=4, ensure_ascii=False)

    print("Saved best design JSON:", output_path)


def plot_score_vs_thickness(df, best_row, output_path):
    """
    绘制 final_score 随 Surface 3 Thickness 变化的曲线。
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(7, 5))

    plt.plot(
        df["actual_thickness_mm"],
        df["final_score"],
        marker="o",
        label="Final score",
    )

    plt.scatter(
        [best_row["actual_thickness_mm"]],
        [best_row["final_score"]],
        s=80,
        label="Best case",
    )

    plt.xlabel("Surface 3 Thickness (mm)")
    plt.ylabel("Score")
    plt.title("D19 Score vs Surface 3 Thickness")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    plt.savefig(output_path, dpi=300)
    plt.close()

    print("Saved score figure:", output_path)


def write_summary_text(best_row, top_df, output_path):
    """
    写一个简单的文字总结，方便放入日志或 README。
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("D19 Best Design Summary")
    lines.append("=" * 40)
    lines.append("")
    lines.append("Current score formula:")
    lines.append("final_score = 0.3*mtf_30_avg + 0.3*mtf_40_avg + 0.4*mtf_50_avg")
    lines.append("")
    lines.append("Best case:")
    lines.append(f"  case_index = {best_row.get('case_index')}")
    lines.append(f"  delta_mm = {best_row.get('delta_mm')}")
    lines.append(f"  actual_thickness_mm = {best_row.get('actual_thickness_mm')}")
    lines.append(f"  mtf_30_avg = {best_row.get('mtf_30_avg')}")
    lines.append(f"  mtf_40_avg = {best_row.get('mtf_40_avg')}")
    lines.append(f"  mtf_50_avg = {best_row.get('mtf_50_avg')}")
    lines.append(f"  final_score = {best_row.get('final_score')}")
    lines.append("")
    lines.append("Top cases:")
    lines.append(top_df[["case_index", "delta_mm", "actual_thickness_mm", "final_score"]].to_string(index=False))
    lines.append("")
    lines.append("Note:")
    lines.append("This is an MTF-only score. A more complete optical evaluation should include RMS Spot or other image quality metrics.")

    output_path.write_text("\n".join(lines), encoding="utf-8")

    print("Saved summary text:", output_path)


def main():
    print("===== D19 Best Design Selection Started =====")

    project_dir = Path(__file__).resolve().parents[1]

    input_csv = project_dir / "results" / "D18_mtf_plots" / "D18_clean_sweep_results.csv"
    output_dir = project_dir / "results" / "D19_best_design"
    output_dir.mkdir(parents=True, exist_ok=True)

    scored_csv = output_dir / "D19_scored_results.csv"
    top_cases_csv = output_dir / "D19_top_cases.csv"
    best_json = output_dir / "best_design.json"
    score_fig = output_dir / "D19_score_vs_thickness.png"
    summary_txt = output_dir / "D19_best_design_summary.txt"

    df_raw = load_clean_results(input_csv)
    df_clean = prepare_numeric_data(df_raw)
    df_scored = calculate_score(df_clean)

    best_row = select_best_design(df_scored)

    save_scored_results(df_scored, scored_csv)
    top_df = save_top_cases(df_scored, top_cases_csv, top_n=5)
    save_best_design_json(best_row, best_json)
    plot_score_vs_thickness(df_scored, best_row, score_fig)
    write_summary_text(best_row, top_df, summary_txt)

    print("\nBest design:")
    print("case_index:", best_row.get("case_index"))
    print("delta_mm:", best_row.get("delta_mm"))
    print("actual_thickness_mm:", best_row.get("actual_thickness_mm"))
    print("final_score:", best_row.get("final_score"))

    print("\n===== D19 Best Design Selection Finished =====")


if __name__ == "__main__":
    main()