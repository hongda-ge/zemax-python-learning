from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


def load_sweep_results(csv_path):
    """
    读取 D17 生成的 sweep_results.csv。
    """
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"Cannot find sweep results CSV: {csv_path}")

    df = pd.read_csv(csv_path)

    print("Loaded CSV:", csv_path)
    print("Rows:", len(df))
    print("Columns:", list(df.columns))

    return df


def clean_sweep_results(df):
    """
    清洗数据：
    1. 只保留 metric_status 为 success 的行
    2. 将关键列转换为数字
    3. 按 actual_thickness_mm 排序
    """
    df = df.copy()

    if "metric_status" in df.columns:
        df = df[df["metric_status"] == "success"]

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

    print("Cleaned rows:", len(df))

    return df


def plot_mtf_vs_delta(df, output_path):
    """
    绘制 MTF 随 delta 变化的曲线。
    横坐标：delta_mm
    纵坐标：MTF
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(7, 5))

    plt.plot(df["delta_mm"], df["mtf_30_avg"], marker="o", label="MTF@30 lp/mm")
    plt.plot(df["delta_mm"], df["mtf_40_avg"], marker="s", label="MTF@40 lp/mm")
    plt.plot(df["delta_mm"], df["mtf_50_avg"], marker="^", label="MTF@50 lp/mm")

    plt.xlabel("Thickness delta (mm)")
    plt.ylabel("Average MTF")
    plt.title("MTF vs Surface 3 Thickness Delta")
    plt.ylim(0, 1.05)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    plt.savefig(output_path, dpi=300)
    plt.close()

    print("Saved figure:", output_path)


def plot_mtf_vs_thickness(df, output_path):
    """
    绘制 MTF 随实际 Thickness 变化的曲线。
    横坐标：actual_thickness_mm
    纵坐标：MTF
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(7, 5))

    plt.plot(df["actual_thickness_mm"], df["mtf_30_avg"], marker="o", label="MTF@30 lp/mm")
    plt.plot(df["actual_thickness_mm"], df["mtf_40_avg"], marker="s", label="MTF@40 lp/mm")
    plt.plot(df["actual_thickness_mm"], df["mtf_50_avg"], marker="^", label="MTF@50 lp/mm")

    plt.xlabel("Surface 3 Thickness (mm)")
    plt.ylabel("Average MTF")
    plt.title("MTF vs Surface 3 Thickness")
    plt.ylim(0, 1.05)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    plt.savefig(output_path, dpi=300)
    plt.close()

    print("Saved figure:", output_path)


def write_trend_summary(df, output_path):
    """
    写一个简单的趋势总结。
    这里只做初步记录，不做最终最优设计判断。
    D19 才正式做评分函数和最优参数筛选。
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    best_30 = df.loc[df["mtf_30_avg"].idxmax()]
    best_40 = df.loc[df["mtf_40_avg"].idxmax()]
    best_50 = df.loc[df["mtf_50_avg"].idxmax()]

    text = []
    text.append("D18 MTF Trend Summary")
    text.append("=" * 40)
    text.append("")
    text.append(f"Total valid cases: {len(df)}")
    text.append("")
    text.append("Best MTF@30:")
    text.append(f"  delta_mm = {best_30['delta_mm']}")
    text.append(f"  actual_thickness_mm = {best_30['actual_thickness_mm']}")
    text.append(f"  mtf_30_avg = {best_30['mtf_30_avg']}")
    text.append("")
    text.append("Best MTF@40:")
    text.append(f"  delta_mm = {best_40['delta_mm']}")
    text.append(f"  actual_thickness_mm = {best_40['actual_thickness_mm']}")
    text.append(f"  mtf_40_avg = {best_40['mtf_40_avg']}")
    text.append("")
    text.append("Best MTF@50:")
    text.append(f"  delta_mm = {best_50['delta_mm']}")
    text.append(f"  actual_thickness_mm = {best_50['actual_thickness_mm']}")
    text.append(f"  mtf_50_avg = {best_50['mtf_50_avg']}")
    text.append("")
    text.append("Note:")
    text.append("D18 only visualizes the trend. Formal scoring and best design selection will be done in D19.")

    output_path.write_text("\n".join(text), encoding="utf-8")

    print("Saved trend summary:", output_path)


def main():
    print("===== D18 Plot MTF vs Thickness Started =====")

    project_dir = Path(__file__).resolve().parents[2]

    input_csv = project_dir / "results" / "archive" / "D17_metric_extraction" / "sweep_results.csv"
    output_dir = project_dir / "results" / "archive" / "D18_mtf_plots"
    output_dir.mkdir(parents=True, exist_ok=True)

    clean_csv = output_dir / "D18_clean_sweep_results.csv"
    fig_delta = output_dir / "D18_mtf_vs_delta.png"
    fig_thickness = output_dir / "D18_mtf_vs_thickness.png"
    summary_txt = output_dir / "D18_trend_summary.txt"

    df_raw = load_sweep_results(input_csv)
    df_clean = clean_sweep_results(df_raw)

    df_clean.to_csv(clean_csv, index=False, encoding="utf-8-sig")
    print("Saved cleaned CSV:", clean_csv)

    plot_mtf_vs_delta(df_clean, fig_delta)
    plot_mtf_vs_thickness(df_clean, fig_thickness)
    write_trend_summary(df_clean, summary_txt)

    print("===== D18 Plot MTF vs Thickness Finished =====")


if __name__ == "__main__":
    main()