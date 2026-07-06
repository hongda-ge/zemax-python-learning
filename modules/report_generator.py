# modules/report_generator.py

from datetime import datetime


def generate_markdown_report(config, paths, sweep_values, workflow_summary=None):
    """
    根据配置文件、输出路径、扫描参数和 workflow 结果，生成 Markdown 报告草稿。
    """
    project = config["project"]
    zemax = config["zemax"]
    sweep = config["sweep"]
    analysis = config["analysis"]

    reports_dir = paths["reports"]
    reports_dir.mkdir(parents=True, exist_ok=True)

    report_path = reports_dir / "report.md"

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sweep_values_text = ", ".join(str(v) for v in sweep_values)
    metrics_text = "\n".join(f"- {metric}" for metric in analysis["metrics"])

    best_text = "当前未生成最优结果。"
    if workflow_summary is not None and workflow_summary.get("best_row") is not None:
        best = workflow_summary["best_row"]
        best_text = (
            f"当前 dry-run demo 中，score 最高的参数值为 "
            f"`{best['parameter_value']} {sweep['unit']}`，"
            f"对应 MTF_50 = `{best['MTF_50']}`，"
            f"RMS_Spot = `{best['RMS_Spot']}`，"
            f"score = `{best['score']}`。"
        )

    figure_section = ""
    if workflow_summary is not None:
        figure_section = f"""
## 7. 自动生成图表

本次 workflow 自动生成了 MTF_50 随扫描参数变化的曲线：

![MTF_50 曲线](../figures/{paths["figure_file"].name})

"""

    content = f"""# Zemax 参数扫描自动化报告草稿

## 1. 项目信息

| 项目 | 内容 |
|---|---|
| 项目名称 | {project["name"]} |
| 项目说明 | {project["description"]} |
| 生成时间 | {now} |
| Dry Run | {project["dry_run"]} |

## 2. Zemax 模型信息

| 项目 | 内容 |
|---|---|
| Zemax 运行模式 | {zemax["mode"]} |
| 模型文件 | `{zemax["model_file"]}` |
| 是否保存模型 | {zemax["save_model"]} |

## 3. 参数扫描设置

| 项目 | 内容 |
|---|---|
| 扫描表面 | Surface {sweep["surface_id"]} |
| 扫描参数 | {sweep["parameter"]} |
| 单位 | {sweep["unit"]} |
| 起始值 | {sweep["start"]} |
| 终止值 | {sweep["end"]} |
| 步长 | {sweep["step"]} |
| 扫描点数量 | {len(sweep_values)} |

### 扫描值列表

{sweep_values_text}

## 4. 评价指标

{metrics_text}

## 5. 输出文件结构

| 类型 | 路径 |
|---|---|
| 本次运行目录 | `{paths["run_dir"]}` |
| CSV 目录 | `{paths["csv"]}` |
| 图片目录 | `{paths["figures"]}` |
| 模型目录 | `{paths["models"]}` |
| 日志目录 | `{paths["logs"]}` |
| 报告目录 | `{paths["reports"]}` |
| 配置备份 | `{paths["config_backup"]}` |

## 6. 实际输出文件

| 文件类型 | 文件路径 |
|---|---|
| 扫描结果 CSV | `{paths["csv_file"]}` |
| 运行状态 CSV | `{paths["status_csv_file"]}` |
| MTF_50 曲线图 | `{paths["figure_file"]}` |
| 日志文件 | `{paths["log_file"]}` |
| 报告文件 | `{report_path}` |

{figure_section}

## 8. 当前最优结果

{best_text}

## 9. 当前说明

本报告由 `report_generator.py` 自动生成。  
当前 D27 阶段完成的是 dry-run 端到端 demo，还没有真正调用 Zemax ZOS-API。

后续接入真实 Zemax 后，需要把 `workflow_runner.py` 中的模拟指标替换为真实的：

- 参数修改
- MTF 分析
- RMS Spot 提取
- 模型保存
- 图像导出

## 10. 当前结论

当前 D27 阶段已经实现：

1. 一条命令读取配置文件；
2. 自动创建本次运行目录；
3. 自动生成 CSV；
4. 自动绘制 MTF_50 曲线；
5. 自动记录日志；
6. 自动生成 Markdown 报告。

"""

    report_path.write_text(content, encoding="utf-8")

    print(f"Markdown 报告已生成: {report_path}")

    return report_path