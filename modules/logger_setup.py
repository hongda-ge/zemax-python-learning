# modules/logger_setup.py

import logging
from pathlib import Path


def setup_logger(log_file):
    """
    创建日志记录器，同时输出到终端和 log 文件。
    """
    log_file = Path(log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("zemax_auto")
    logger.setLevel(logging.INFO)

    # 避免重复添加 handler，导致日志重复打印
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info("日志系统初始化完成")
    logger.info(f"日志文件路径: {log_file}")

    return logger