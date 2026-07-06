# modules/output_manager.py

from pathlib import Path
from datetime import datetime
import shutil


def get_project_root():
    """
    获取项目根目录。
    当前文件在 modules 文件夹中，所以 parents[1] 是 02_ZOSAPI_PYTHON。
    """
    return Path(__file__).resolve().parents[1]


def get_today_string():
    """
    返回今天日期，例如 20260703。
    """
    return datetime.now().strftime("%Y%m%d")


def build_run_folder_name(config):
    """
    根据配置文件生成本次运行的文件夹名称。
    例如：20260703_zemax_thickness_sweep_demo
    """
    output_config = config["output"]

    task_name = output_config["task_name"]
    use_date_prefix = output_config.get("use_date_prefix", True)

    if use_date_prefix:
        return f"{get_today_string()}_{task_name}"
    else:
        return task_name


def create_output_dirs(config):
    """
    根据配置文件自动创建输出目录。

    返回一个 paths 字典，后续 main.py、result_analyzer.py、zemax_runner.py
    都可以使用这些路径。
    """
    root = get_project_root()
    output_config = config["output"]

    root_dir = root / output_config["root_dir"]
    run_folder_name = build_run_folder_name(config)
    run_dir = root_dir / run_folder_name

    subfolders = output_config["subfolders"]

    paths = {
        "project_root": root,
        "run_dir": run_dir,
    }

    # 创建主结果文件夹
    run_dir.mkdir(parents=True, exist_ok=True)

    # 创建子文件夹
    for key, folder_name in subfolders.items():
        folder_path = run_dir / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)
        paths[key] = folder_path

    # 常用文件路径
    paths["csv_file"] = paths["csv"] / output_config["csv_name"]
    paths["status_csv_file"] = paths["csv"] / output_config.get("status_csv_name", "run_status.csv")
    paths["figure_file"] = paths["figures"] / output_config.get("figure_name", "mtf50_vs_thickness.png")
    paths["log_file"] = paths["logs"] / output_config["log_name"]
    paths["config_backup"] = run_dir / output_config["config_backup_name"]


    return paths


def backup_config(config_path, paths):
    """
    把本次使用的配置文件复制到结果文件夹中。
    这样以后你就知道这次结果是用什么参数跑出来的。
    """
    config_path = Path(config_path)

    if not config_path.is_absolute():
        config_path = get_project_root() / config_path

    shutil.copy2(config_path, paths["config_backup"])


def print_output_paths(paths):
    """
    打印本次输出路径，方便检查。
    """
    print("========== D24 输出目录检查 ==========")
    print("本次运行目录:", paths["run_dir"])
    print("CSV目录:", paths["csv"])
    print("图片目录:", paths["figures"])
    print("模型目录:", paths["models"])
    print("日志目录:", paths["logs"])
    print("报告目录:", paths["reports"])
    print("CSV文件:", paths["csv_file"])
    print("状态CSV文件:", paths["status_csv_file"])
    print("图片文件:", paths["figure_file"])
    print("日志文件:", paths["log_file"])
    print("配置备份:", paths["config_backup"])
    print("=====================================")