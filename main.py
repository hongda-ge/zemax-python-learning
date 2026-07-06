# main.py

import argparse

from modules.config_loader import load_config, summarize_config
from modules.output_manager import (
    create_output_dirs,
    backup_config,
    print_output_paths,
)
from modules.report_generator import generate_markdown_report
from modules.logger_setup import setup_logger
from modules.workflow_runner import run_demo_workflow


def main():
    logger = None

    try:
        print("========== D27 一键运行 workflow 开始 ==========")

        parser = argparse.ArgumentParser(description="D27 一键运行端到端 demo")
        parser.add_argument(
            "--config",
            default="configs/config_zemax.yaml",
            help="配置文件路径，默认使用 configs/config_zemax.yaml"
        )

        args = parser.parse_args()

        print("1. 正在读取配置文件...")
        config = load_config(args.config)

        print("2. 正在生成扫描参数...")
        sweep_values = summarize_config(config)

        print("3. 正在创建输出目录...")
        paths = create_output_dirs(config)

        print("4. 正在初始化日志系统...")
        logger = setup_logger(paths["log_file"])
        logger.info("========== D27 一键运行 workflow 开始 ==========")

        print("5. 正在备份配置文件...")
        backup_config(args.config, paths)
        logger.info("配置文件备份完成")

        print("6. 正在打印输出路径...")
        print_output_paths(paths)

        print("7. 正在运行 dry-run 参数扫描 workflow...")
        workflow_summary = run_demo_workflow(config, paths, sweep_values, logger)

        print("8. 正在生成 Markdown 报告...")
        report_path = generate_markdown_report(
            config=config,
            paths=paths,
            sweep_values=sweep_values,
            workflow_summary=workflow_summary,
        )
        logger.info(f"报告生成完成: {report_path}")

        logger.info("========== D27 一键运行 workflow 结束 ==========")

        print()
        print("========== D27 测试完成 ==========")
        print(f"本次运行目录: {paths['run_dir']}")
        print(f"扫描结果 CSV: {paths['csv_file']}")
        print(f"运行状态 CSV: {paths['status_csv_file']}")
        print(f"图片文件: {paths['figure_file']}")
        print(f"日志文件: {paths['log_file']}")
        print(f"报告文件: {report_path}")

    except Exception:
        if logger is not None:
            logger.exception("主程序发生严重错误，程序终止")
        else:
            print("主程序在日志系统初始化前发生错误")
        raise


if __name__ == "__main__":
    main()