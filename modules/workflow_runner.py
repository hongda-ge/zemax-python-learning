# modules/workflow_runner.py

import csv
import math

import matplotlib.pyplot as plt


def run_demo_workflow(config, paths, sweep_values, logger):
    """
    D27 端到端 dry-run workflow。

    当前阶段还不真正调用 Zemax。
    这里用模拟数据代替真实 MTF / RMS Spot，目的是先验证：
    1. main.py 一键运行；
    2. 自动生成 sweep_results.csv；
    3. 自动生成 run_status.csv；
    4. 自动生成趋势图；
    5. 报告里能引用这些输出。
    """
    logger.info("========== D27 dry-run workflow 开始 ==========")

    debug_config = config.get("debug", {})
    simulate_failure = debug_config.get("simulate_failure", False)
    fail_at_index = debug_config.get("fail_at_index", 3)

    results = []
    status_rows = []

    for index, value in enumerate(sweep_values, start=1):
        try:
            logger.info(f"开始第 {index} 组任务，参数值 = {value}")

            if simulate_failure and index == fail_at_index:
                raise RuntimeError(f"模拟失败：第 {index} 组任务失败，参数值 = {value}")

            metrics = simulate_optical_metrics(value)

            row = {
                "index": index,
                "parameter_value": value,
                "MTF_30": metrics["MTF_30"],
                "MTF_50": metrics["MTF_50"],
                "RMS_Spot": metrics["RMS_Spot"],
                "score": metrics["score"],
            }
            results.append(row)

            status_rows.append({
                "index": index,
                "parameter_value": value,
                "status": "success",
                "error_message": "",
            })

            logger.info(
                f"第 {index} 组成功："
                f"MTF_50={metrics['MTF_50']}, "
                f"RMS_Spot={metrics['RMS_Spot']}, "
                f"score={metrics['score']}"
            )

        except Exception as e:
            logger.exception(f"第 {index} 组失败，但程序继续下一组")

            status_rows.append({
                "index": index,
                "parameter_value": value,
                "status": "failed",
                "error_message": str(e),
            })

            continue

    save_sweep_results_csv(results, paths["csv_file"], logger)
    save_status_csv(status_rows, paths["status_csv_file"], logger)
    plot_mtf50_curve(results, paths["figure_file"], logger)

    best_row = find_best_result(results)

    logger.info("========== D27 dry-run workflow 结束 ==========")

    return {
        "results": results,
        "status_rows": status_rows,
        "best_row": best_row,
        "csv_file": paths["csv_file"],
        "status_csv_file": paths["status_csv_file"],
        "figure_file": paths["figure_file"],
    }


def simulate_optical_metrics(parameter_value):
    """
    模拟一个光学性能变化趋势。

    这里不是物理真实结果，只是为了生成一组可用于测试流程的假数据：
    - 参数接近 0.2 时，MTF_50 稍好；
    - 偏离太远时，MTF 降低；
    - RMS Spot 与参数偏离程度相关。
    """
    x = float(parameter_value)

    mtf_50 = 0.65 + 0.25 * math.exp(-((x - 0.2) ** 2) / 0.25)
    mtf_30 = mtf_50 + 0.08
    rms_spot = 8.0 + 10.0 * abs(x - 0.2)

    score = mtf_50 - 0.02 * rms_spot

    return {
        "MTF_30": round(mtf_30, 4),
        "MTF_50": round(mtf_50, 4),
        "RMS_Spot": round(rms_spot, 4),
        "score": round(score, 4),
    }


def save_sweep_results_csv(results, csv_file, logger):
    """
    保存模拟扫描结果。
    """
    fieldnames = [
        "index",
        "parameter_value",
        "MTF_30",
        "MTF_50",
        "RMS_Spot",
        "score",
    ]

    with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    logger.info(f"sweep_results.csv 已保存: {csv_file}")


def save_status_csv(status_rows, status_csv_file, logger):
    """
    保存每组任务运行状态。
    """
    fieldnames = ["index", "parameter_value", "status", "error_message"]

    with open(status_csv_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(status_rows)

    logger.info(f"run_status.csv 已保存: {status_csv_file}")


def plot_mtf50_curve(results, figure_file, logger):
    """
    绘制 MTF_50 随参数变化的曲线。
    """
    if not results:
        logger.warning("没有成功结果，无法绘制 MTF_50 曲线")
        return

    x = [row["parameter_value"] for row in results]
    y = [row["MTF_50"] for row in results]

    plt.figure()
    plt.plot(x, y, marker="o")
    plt.xlabel("Thickness change (mm)")
    plt.ylabel("MTF_50")
    plt.title("MTF_50 vs Thickness")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(figure_file, dpi=300)
    plt.close()

    logger.info(f"MTF_50 曲线已保存: {figure_file}")


def find_best_result(results):
    """
    根据 score 找到最优结果。
    """
    if not results:
        return None

    return max(results, key=lambda row: row["score"])