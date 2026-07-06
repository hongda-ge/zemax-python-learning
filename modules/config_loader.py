# modules/config_loader.py

from pathlib import Path
import yaml


def get_project_root():
    """
    获取项目根目录。
    当前文件在 modules 文件夹中，所以 parents[1] 是 02_ZOSAPI_PYTHON。
    """
    return Path(__file__).resolve().parents[1]


def load_config(config_path):
    """
    读取 YAML 配置文件。
    """
    config_path = Path(config_path)

    if not config_path.is_absolute():
        config_path = get_project_root() / config_path

    if not config_path.exists():
        raise FileNotFoundError(f"找不到配置文件: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config


def generate_sweep_values(start, end, step):
    """
    根据 start、end、step 生成扫描参数列表。
    例如 -1 到 1，步长 0.2。
    """
    values = []
    current = start

    # 加一个很小的容差，避免浮点数导致最后一个点丢失
    while current <= end + 1e-9:
        values.append(round(current, 6))
        current += step

    return values


def summarize_config(config):
    """
    打印配置摘要，方便检查 YAML 是否读取正确。
    """
    project = config["project"]
    zemax = config["zemax"]
    sweep = config["sweep"]
    analysis = config["analysis"]
    output = config["output"]

    values = generate_sweep_values(
        sweep["start"],
        sweep["end"],
        sweep["step"]
    )

    print("========== D23/D24 配置文件读取测试 ==========")
    print("项目名称:", project["name"])
    print("项目说明:", project["description"])
    print("是否 dry_run:", project["dry_run"])
    print()
    print("Zemax 模型文件:", zemax["model_file"])
    print("Zemax 运行模式:", zemax["mode"])
    print()
    print("扫描表面:", sweep["surface_id"])
    print("扫描参数:", sweep["parameter"])
    print("单位:", sweep["unit"])
    print("扫描范围:", sweep["start"], "到", sweep["end"])
    print("扫描步长:", sweep["step"])
    print("扫描点数量:", len(values))
    print("扫描值:", values)
    print()
    print("评价指标:", analysis["metrics"])
    print()
    print("输出根目录:", output["root_dir"])
    print("任务名称:", output["task_name"])
    print("CSV 文件名:", output["csv_name"])
    print("============================================")

    return values