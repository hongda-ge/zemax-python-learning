# modules/error_handler.py

import csv


def run_fake_sweep_with_error_handling(config, paths, sweep_values, logger):
    """
    D26 测试用：模拟参数扫描。
    目的不是跑 Zemax，而是测试：
    1. 某一组失败时是否写入 log；
    2. 程序是否继续跑下一组；
    3. 是否生成 run_status.csv。
    """
    debug_config = config.get("debug", {})
    simulate_failure = debug_config.get("simulate_failure", False)
    fail_at_index = debug_config.get("fail_at_index", 3)

    status_rows = []

    logger.info("开始 D26 模拟参数扫描")
    logger.info(f"总扫描组数: {len(sweep_values)}")
    logger.info(f"simulate_failure = {simulate_failure}")
    logger.info(f"fail_at_index = {fail_at_index}")

    for index, value in enumerate(sweep_values, start=1):
        try:
            logger.info(f"开始第 {index} 组扫描，参数值 = {value}")

            # 故意制造一次失败，用来测试 try/except 是否生效
            if simulate_failure and index == fail_at_index:
                raise RuntimeError(f"模拟失败：第 {index} 组扫描失败，参数值 = {value}")

            # 这里以后会替换成真正的 Zemax 调用
            fake_result = {
                "index": index,
                "parameter_value": value,
                "status": "success",
                "error_message": "",
            }

            status_rows.append(fake_result)
            logger.info(f"第 {index} 组扫描成功")

        except Exception as e:
            logger.exception(f"第 {index} 组扫描失败，但程序会继续下一组")

            failed_result = {
                "index": index,
                "parameter_value": value,
                "status": "failed",
                "error_message": str(e),
            }

            status_rows.append(failed_result)
            continue

    save_run_status_csv(status_rows, paths["status_csv_file"], logger)

    success_count = sum(1 for row in status_rows if row["status"] == "success")
    failed_count = sum(1 for row in status_rows if row["status"] == "failed")

    logger.info("D26 模拟参数扫描结束")
    logger.info(f"成功组数: {success_count}")
    logger.info(f"失败组数: {failed_count}")

    return status_rows


def save_run_status_csv(status_rows, status_csv_file, logger):
    """
    保存每一组扫描的运行状态。
    """
    fieldnames = ["index", "parameter_value", "status", "error_message"]

    with open(status_csv_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(status_rows)

    logger.info(f"运行状态 CSV 已保存: {status_csv_file}")