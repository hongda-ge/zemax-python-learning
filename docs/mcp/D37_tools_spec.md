# D37 工具函数设计说明书

> 文件位置建议：`docs/D37_tools_spec.md`  
> 所属阶段：第 6 周 MCP / 工具化进阶  
> 今日任务：把 Zemax-Agent 自动化流程拆成可复用工具函数，并明确每个工具的输入、输出、安全边界和可能错误。  
> 注意：D37 只做工具接口设计，不要求今天实现完整 MCP Server。

---

## 目录

1. [D37 今日目标](#1-d37-今日目标)
2. [当前项目结构参考](#2-当前项目结构参考)
3. [工具化设计核心思想](#3-工具化设计核心思想)
4. [D37 文件命名规范](#4-d37-文件命名规范)
5. [工具设计原则](#5-工具设计原则)
6. [D37 工具总表](#6-d37-工具总表)
7. [Tool 01：load_task](#tool-01load_task)
8. [Tool 02：validate_task](#tool-02validate_task)
9. [Tool 03：check_safety](#tool-03check_safety)
10. [Tool 04：open_model](#tool-04open_model)
11. [Tool 05：set_parameter](#tool-05set_parameter)
12. [Tool 06：run_analysis](#tool-06run_analysis)
13. [Tool 07：run_sweep](#tool-07run_sweep)
14. [Tool 08：analyze_results](#tool-08analyze_results)
15. [Tool 09：prepare_summary_input](#tool-09prepare_summary_input)
16. [Tool 10：generate_report](#tool-10generate_report)
17. [推荐调用流程](#7-推荐调用流程)
18. [MCP 对应关系](#8-mcp-对应关系)
19. [D37 不做的事情](#9-d37-不做的事情)
20. [D38 衔接任务](#10-d38-衔接任务)
21. [D37 检查清单](#11-d37-检查清单)
22. [参考资料](#12-参考资料)

---

## 1. D37 今日目标

D37 的目标是把前面已经跑通的 Zemax-Agent 自动化流程拆成一组清晰、可复用、可校验的工具函数。

今天重点不是继续新增 Zemax 仿真结果，也不是直接实现完整 MCP Server，而是先把“工具接口”设计清楚，为后续 D38 的 `tool_registry.py` / 伪 MCP Server 做准备。

今天建议完成的文件：

```text
02_ZOSAPI_PYTHON/
└─ docs/
   └─ D37_tools_spec.md
```

如果需要同步记录日志，则写入：

```text
02_ZOSAPI_PYTHON/
└─ logs/
   └─ weekly_log_06.md
```

---

## 2. 当前项目结构参考

根据目前根目录截图，当前项目大致结构如下：

```text
02_ZOSAPI_PYTHON/
├─ .venv_zosapi38/
├─ .vscode/
├─ configs/
│  ├─ config_D15_cooke_thickness.yaml
│  ├─ config_D16_cooke_thickness_sweep.yaml
│  ├─ config_D31_from_task.yaml
│  ├─ config_zemax.yaml
│  ├─ safety_policy.yaml
│  └─ task_schema.json
│
├─ docs/
│  ├─ D29_agent_positioning.md
│  ├─ D30_natural_language_to_yaml.md
│  ├─ D32_result_auto_summary.md
│  ├─ D33_safety_boundary.md
│  ├─ D34_agent_demo.md
│  ├─ D36_mcp_architecture_notes.md
│  ├─ D36_mcp_zemax_architecture.md
│  ├─ D37_file_naming_rules.md
│  └─ D37_tools_spec.md
│
├─ examples/
├─ figures/
├─ logs/
│  ├─ weekly_log_02.md
│  ├─ weekly_log_03.md
│  ├─ weekly_log_04.md
│  ├─ weekly_log_05.md
│  └─ weekly_log_06.md
│
├─ models/
├─ modules/
├─ notes/
├─ outputs/
├─ prompts/
│  ├─ nl_to_yaml_prompt.md
│  └─ result_summary_prompt.md
│
├─ reports/
│  ├─ D32_result_summary_input.md
│  └─ D34_agent_demo_report.md
│
├─ results/
├─ scripts/
│  ├─ D30_validate_task_yaml.py
│  ├─ D31_run_from_task_yaml.py
│  ├─ D32_prepare_result_summary.py
│  ├─ D33_check_task_safety.py
│  └─ D34_agent_demo.py
│
├─ scripts_old/
├─ .gitignore
├─ main.py
├─ README.md
├─ requirements.txt
└─ SETUP.md
```

本文件会尽量贴合以上已有结构，不额外引入 `src/zemax_agent/` 这类当前项目中没有的目录。

---

## 3. 工具化设计核心思想

前面 D29-D35 已经形成了一个低配版 Agent 流程：

```text
用户自然语言需求
↓
AI 生成 YAML / JSON 任务
↓
scripts/D30_validate_task_yaml.py 校验任务格式
↓
scripts/D33_check_task_safety.py 检查安全边界
↓
scripts/D31_run_from_task_yaml.py 调用自动化脚本
↓
Python / ZOS-API 控制 Zemax
↓
输出结果、图表和报告
↓
scripts/D32_prepare_result_summary.py 准备结果总结输入
↓
AI 基于真实结果总结
```

D37 要做的是把这条流程拆成更清晰的工具函数：

```text
load_task
↓
validate_task
↓
check_safety
↓
open_model
↓
set_parameter
↓
run_analysis
↓
run_sweep
↓
analyze_results
↓
prepare_summary_input
↓
generate_report
```

后续 D38 的 `tool_registry.py` 可以统一注册和调用这些工具。

---

## 4. D37 文件命名规范

### 4.1 文档文件

文档文件放在 `docs/` 中，命名方式：

```text
docs/D编号_主题.md
```

示例：

```text
docs/D37_tools_spec.md
docs/D37_file_naming_rules.md
docs/D38_tool_registry.md
```

### 4.2 脚本文件

每日任务或演示脚本放在 `scripts/` 中，命名方式：

```text
scripts/D编号_功能说明.py
```

示例：

```text
scripts/D30_validate_task_yaml.py
scripts/D31_run_from_task_yaml.py
scripts/D34_agent_demo.py
scripts/D38_tool_registry_demo.py
```

### 4.3 配置文件

每日任务配置文件放在 `configs/` 中，命名方式：

```text
configs/config_D编号_功能说明.yaml
```

示例：

```text
configs/config_D31_from_task.yaml
configs/config_D38_tool_registry_demo.yaml
```

长期通用配置可以不加 D 编号：

```text
configs/config_zemax.yaml
configs/task_schema.json
configs/safety_policy.yaml
```

### 4.4 提示词文件

提示词文件放在 `prompts/` 中，命名方式：

```text
prompts/功能说明_prompt.md
```

示例：

```text
prompts/nl_to_yaml_prompt.md
prompts/result_summary_prompt.md
```

### 4.5 报告文件

报告文件放在 `reports/` 中，命名方式：

```text
reports/D编号_报告说明.md
```

示例：

```text
reports/D32_result_summary_input.md
reports/D34_agent_demo_report.md
reports/D38_tool_registry_demo_report.md
```

### 4.6 日志文件

每周日志统一放在 `logs/` 中：

```text
logs/weekly_log_06.md
```

不要再把 `weekly_log_06.md` 放在根目录。

### 4.7 长期复用模块

长期复用模块建议放到 `modules/` 中，不加 D 编号。

示例：

```text
modules/task_loader.py
modules/task_validator.py
modules/safety_checker.py
modules/zemax_runner.py
modules/analysis_runner.py
modules/result_analyzer.py
modules/report_generator.py
modules/tool_registry.py
```

这些模块不是某一天的临时作业，而是后续整个项目都会反复调用的核心代码。

---

## 5. 工具设计原则

1. 每个工具只做一类事情，不要一个函数包办所有流程。
2. 每个工具必须写清楚输入、输出、安全边界和可能错误。
3. 所有任务配置必须先经过 `configs/task_schema.json` 校验。
4. 所有安全限制必须参考 `configs/safety_policy.yaml`。
5. 原始 Zemax 模型默认只读，不直接覆盖源文件。
6. 所有输出结果统一放到 `results/`、`outputs/`、`reports/` 或 `figures/` 中。
7. 所有日志统一放到 `logs/` 中。
8. AI 只能生成任务配置或调用工具，不能绕过工具直接修改模型。
9. 工具的结论必须基于真实 CSV、图表、报告或日志，不能凭空写“性能显著提升”。
10. D37 只做工具接口设计，不要求所有工具今天都写成可运行代码。

---

## 6. D37 工具总表

| 工具名称 | 作用 | 当前对应已有文件 | 后续建议模块 |
|---|---|---|---|
| `load_task`             | 读取 YAML 任务配置          | `configs/config_D31_from_task.yaml`                               | `modules/task_loader.py` |
| `validate_task`         | 检查任务格式是否合法         | `scripts/D30_validate_task_yaml.py`、`configs/task_schema.json`   | `modules/task_validator.py` |
| `check_safety`          | 检查参数范围、路径和输出安全  | `scripts/D33_check_task_safety.py`、`configs/safety_policy.yaml`  | `modules/safety_checker.py` |
| `open_model`            | 打开 Zemax 模型             | D31 / D34 流程中已有相关逻辑                                        | `modules/zemax_runner.py` |
| `set_parameter`         | 修改 Zemax LDE 参数         | D31 / D34 流程中已有相关逻辑                                        | `modules/zemax_runner.py` |
| `run_analysis`          | 运行 MTF / Spot 等分析      | 当前属于后续扩展重点                                                 | `modules/analysis_runner.py` |
| `run_sweep`             | 执行参数扫描                | `configs/config_D16_cooke_thickness_sweep.yaml`                    | `modules/zemax_runner.py` 或 `modules/optimizer.py` |
| `analyze_results`       | 读取结果并提取关键指标       | `reports/D32_result_summary_input.md`                              | `modules/result_analyzer.py` |
| `prepare_summary_input` | 准备 AI 总结输入            | `scripts/D32_prepare_result_summary.py`                            | `modules/report_generator.py` |
| `generate_report`       | 生成报告                    | `reports/D34_agent_demo_report.md`                                 | `modules/report_generator.py` |

---

# Tool 01：load_task

## 工具名称

```text
load_task
```

## 功能说明
读取 YAML 任务文件，并把任务内容转换成 Python 可以使用的数据结构。
这个工具只负责“读取任务”，不负责判断任务是否合法，也不负责运行 Zemax。
## 当前已有基础
```text
configs/config_D31_from_task.yaml
configs/config_zemax.yaml
configs/config_D15_cooke_thickness.yaml
configs/config_D16_cooke_thickness_sweep.yaml
```
## 建议后续模块
```text
modules/task_loader.py
```
## 输入
| 参数名 | 类型 | 是否必须 | 示例 | 说明 |
|---|---|---|---|---|
| `task_file` | string | 是 | `configs/config_D31_from_task.yaml` | YAML 任务文件路径 |
## 输出
| 输出名 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `status` | string | `success` | 是否读取成功 |
| `task` | dict | `{...}` | 解析后的任务内容 |
| `task_file` | string | `configs/config_D31_from_task.yaml` | 实际读取的文件路径 |

## 安全边界

- 只能读取项目目录内的 YAML 文件。
- 不允许读取系统目录、桌面隐私文件或项目外路径。
- 如果文件不存在，直接返回错误，不继续执行。

## 可能错误

| 错误类型 | 原因 | 处理方式 |
|---|---|---|
| `task_file_not_found` | YAML 文件不存在 | 提示检查路径 |
| `yaml_parse_failed` | YAML 格式错误 | 返回具体行号或错误信息 |
| `path_not_allowed` | 文件路径超出项目目录 | 拒绝读取 |

---

# Tool 02：validate_task

## 工具名称

```text
validate_task
```

## 功能说明

根据 `configs/task_schema.json` 检查任务配置是否合法。

这个工具只检查“格式和字段”，例如有没有 `software`、`task_type`、`model_file`、`target`、`metrics`、`outputs` 等字段。

## 当前已有基础

```text
scripts/D30_validate_task_yaml.py
configs/task_schema.json
```

## 建议后续模块

```text
modules/task_validator.py
```

## 输入

| 参数名 | 类型 | 是否必须 | 示例 | 说明 |
|---|---|---|---|---|
| `task` | dict | 是 | `{...}` | 从 YAML 读取到的任务内容 |
| `schema_file` | string | 否 | `configs/task_schema.json` | JSON Schema 文件路径 |

## 输出

| 输出名 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `status` | string | `success` | 校验流程是否完成 |
| `valid` | bool | `true` | 任务是否符合 schema |
| `errors` | list | `[]` | 错误列表 |

## 安全边界

- schema 文件必须来自 `configs/task_schema.json` 或项目内允许的 schema。
- 校验不通过时，不允许继续运行 Zemax。
- 不能自动补全危险字段，例如超大范围扫描。

## 可能错误

| 错误类型 | 原因 | 处理方式 |
|---|---|---|
| `schema_not_found` | 找不到 schema 文件 | 检查 `configs/task_schema.json` |
| `validation_failed` | YAML 字段不符合 schema | 返回错误字段 |
| `unsupported_task_type` | 任务类型不支持 | 拒绝执行 |

---

# Tool 03：check_safety

## 工具名称

```text
check_safety
```

## 功能说明

根据 `configs/safety_policy.yaml` 检查任务是否安全，包括参数范围、单位、扫描次数、输入输出路径等。

这个工具解决的问题是：即使 YAML 格式正确，也不能保证任务安全。例如扫描范围太大、输出路径危险、覆盖原始模型等。

## 当前已有基础

```text
scripts/D33_check_task_safety.py
configs/safety_policy.yaml
```

## 建议后续模块

```text
modules/safety_checker.py
```

## 输入

| 参数名 | 类型 | 是否必须 | 示例 | 说明 |
|---|---|---|---|---|
| `task` | dict | 是 | `{...}` | 已通过 schema 校验的任务 |
| `safety_policy_file` | string | 否 | `configs/safety_policy.yaml` | 安全策略文件 |
| `dry_run` | bool | 否 | `true` | 是否只检查不执行 |

## 输出

| 输出名 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `status` | string | `success` | 检查流程是否完成 |
| `safe` | bool | `true` | 任务是否安全 |
| `estimated_runs` | int | `21` | 预计运行次数 |
| `warnings` | list | `[]` | 警告信息 |
| `errors` | list | `[]` | 错误信息 |

## 安全边界

- 扫描次数必须有限制，不能无限循环。
- 输出路径必须在 `results/`、`outputs/`、`figures/` 或 `reports/` 中。
- 原始模型不能被覆盖，必须另存为新文件或输出副本。
- 所有参数必须有单位。
- AI 生成的任务必须先经过 safety check，再进入仿真流程。

## 可能错误

| 错误类型 | 原因 | 处理方式 |
|---|---|---|
| `too_many_runs` | 扫描次数过多 | 拒绝执行 |
| `value_out_of_range` | 参数超出允许范围 | 拒绝执行 |
| `unit_missing` | 缺少单位 | 要求补充单位 |
| `unsafe_output_path` | 输出路径不安全 | 拒绝写入 |
| `overwrite_source_model` | 可能覆盖源模型 | 强制另存为副本 |

---

# Tool 04：open_model

## 工具名称

```text
open_model
```

## 功能说明

通过 Python / ZOS-API 打开指定 Zemax 模型文件。

这个工具是 Zemax 自动化流程的入口。它只负责打开模型和返回模型基本信息，不负责修改参数。

## 当前已有基础

```text
debug_zosapi_connection.py
scripts/D31_run_from_task_yaml.py
scripts/D34_agent_demo.py
```

## 建议后续模块

```text
modules/zemax_runner.py
```

## 输入

| 参数名 | 类型 | 是否必须 | 示例 | 说明 |
|---|---|---|---|---|
| `model_file` | string | 是 | `models/Double_Gauss_28_degree_field.zmx` | Zemax 模型文件路径 |
| `mode` | string | 否 | `standalone` | 连接模式，当前优先使用 standalone |
| `make_copy` | bool | 否 | `true` | 是否复制一份模型作为工作副本 |

## 输出

| 输出名 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `status` | string | `success` | 是否成功 |
| `model_file` | string | `models/Double_Gauss_28_degree_field.zmx` | 原始模型路径 |
| `working_model_file` | string | `outputs/working_model.zmx` | 实际运行的模型副本 |
| `surface_count` | int | `12` | 表面数量 |
| `message` | string | `model opened` | 运行说明 |

## 安全边界

- 只允许打开 `models/` 或项目允许路径中的模型。
- 默认不修改、不覆盖原始模型。
- 如果 `make_copy = true`，后续操作应该基于副本进行。
- 模型文件不存在时，直接返回错误。

## 可能错误

| 错误类型 | 原因 | 处理方式 |
|---|---|---|
| `model_not_found` | 模型文件不存在 | 检查 `models/` 路径 |
| `invalid_file_type` | 文件类型不是 Zemax 模型 | 拒绝执行 |
| `zemax_connection_failed` | ZOS-API 连接失败 | 检查 Zemax、Python 环境和授权 |
| `open_model_failed` | 模型打开失败 | 返回错误信息并停止流程 |

---

# Tool 05：set_parameter

## 工具名称

```text
set_parameter
```

## 功能说明

修改 Zemax Lens Data Editor 中指定表面的参数，例如 thickness、radius 等。

这个工具只负责修改一个明确参数，不负责完整扫描。

## 建议后续模块

```text
modules/zemax_runner.py
```

## 输入

| 参数名 | 类型 | 是否必须 | 示例 | 说明 |
|---|---|---|---|---|
| `surface` | int | 是 | `6` | LDE 表面编号 |
| `parameter` | string | 是 | `thickness` | 参数名称 |
| `value` | number/string | 是 | `1.25` | 新参数值 |
| `unit` | string | 否 | `mm` | 参数单位 |
| `save_after_change` | bool | 否 | `false` | 修改后是否立即保存 |

## 当前阶段建议支持的 parameter

```text
thickness
radius
```

暂时不要一开始就支持太多参数，例如 glass、material、semi-diameter、conic 等，可以后续 Project-X 再扩展。

## 输出

| 输出名 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `status` | string | `success` | 是否成功 |
| `surface` | int | `6` | 被修改的表面 |
| `parameter` | string | `thickness` | 被修改的参数 |
| `old_value` | number/string | `2.0` | 修改前的值 |
| `new_value` | number/string | `1.25` | 修改后的值 |
| `unit` | string | `mm` | 单位 |
| `message` | string | `parameter updated` | 运行说明 |

## 安全边界

- surface 必须在当前模型表面数量范围内。
- parameter 必须在允许列表中。
- value 必须在安全范围内。
- 不允许修改未明确支持的参数。
- 默认不直接覆盖原始模型。

## 可能错误

| 错误类型 | 原因 | 处理方式 |
|---|---|---|
| `invalid_surface` | 表面编号不存在 | 拒绝执行 |
| `unsupported_parameter` | 参数暂不支持 | 拒绝执行 |
| `value_out_of_range` | 参数值超出安全范围 | 拒绝执行 |
| `unit_mismatch` | 单位不一致 | 提示修改单位 |
| `parameter_update_failed` | 参数修改失败 | 返回错误信息 |

---

# Tool 06：run_analysis

## 工具名称

```text
run_analysis
```

## 功能说明

运行指定 Zemax 分析，并导出结果文件。

D37 阶段只做工具接口设计，不承诺所有分析都已经实现。当前优先规划 MTF 和 Spot Diagram，Ray Fan、Distortion、Field Curvature 后续再扩展。

## 建议后续模块

```text
modules/analysis_runner.py
```

## 输入

| 参数名 | 类型 | 是否必须 | 示例 | 说明 |
|---|---|---|---|---|
| `analysis_type` | string | 是 | `fft_mtf` | 分析类型 |
| `output_dir` | string | 否 | `results/D37_analysis_test` | 输出目录 |
| `output_format` | string/list | 否 | `txt` | 输出格式 |
| `settings` | dict | 否 | `{"frequency": 30}` | 分析设置 |

## 当前优先支持的 analysis_type

```text
fft_mtf
spot_diagram
```

## 后续可扩展的 analysis_type

```text
ray_fan
distortion
field_curvature
```

## 输出

| 输出名 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `status` | string | `success` | 是否成功 |
| `analysis_type` | string | `fft_mtf` | 分析类型 |
| `output_files` | list | `["results/mtf_result.txt"]` | 输出文件 |
| `message` | string | `analysis completed` | 运行说明 |

## 安全边界

- 输出目录必须在 `results/`、`outputs/` 或 `figures/` 中。
- 分析类型必须在允许列表中。
- 文件名应该自动生成，避免覆盖旧结果。
- 如果分析失败，不允许伪造结果。

## 可能错误

| 错误类型 | 原因 | 处理方式 |
|---|---|---|
| `unsupported_analysis` | 分析类型暂不支持 | 拒绝执行 |
| `analysis_failed` | Zemax 分析运行失败 | 返回错误信息 |
| `export_failed` | 结果导出失败 | 记录日志 |
| `unsafe_output_path` | 输出路径不安全 | 拒绝写入 |

---

# Tool 07：run_sweep

## 工具名称

```text
run_sweep
```

## 功能说明

按照任务配置对某个参数进行扫描。它本质上是一个组合工具，内部会反复调用：

```text
set_parameter
↓
run_analysis
↓
保存结果
```

## 当前已有基础

```text
configs/config_D16_cooke_thickness_sweep.yaml
scripts/D31_run_from_task_yaml.py
scripts/D34_agent_demo.py
```

## 建议后续模块

```text
modules/zemax_runner.py
```

或者后续 Project-X 中单独扩展为：

```text
modules/optimizer.py
```

## 输入

| 参数名 | 类型 | 是否必须 | 示例 | 说明 |
|---|---|---|---|---|
| `task` | dict | 是 | `{...}` | 已通过校验的任务 |
| `dry_run` | bool | 否 | `true` | 是否只预估运行次数 |
| `max_runs` | int | 否 | `50` | 最大运行次数 |

## 输出

| 输出名 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `status` | string | `success` | 是否成功 |
| `run_count` | int | `21` | 实际运行次数 |
| `results_dir` | string | `results/D37_sweep_test` | 结果目录 |
| `results_csv` | string | `results/D37_sweep_test/sweep_results.csv` | 结果表 |
| `message` | string | `sweep completed` | 运行说明 |

## 安全边界

- 必须先通过 `validate_task`。
- 必须先通过 `check_safety`。
- 默认先执行 dry-run，确认扫描次数。
- 扫描次数不能超过安全限制。
- 每轮输出应该有独立文件名或独立子目录。
- 不允许覆盖源模型。

## 可能错误

| 错误类型 | 原因 | 处理方式 |
|---|---|---|
| `validation_not_passed` | 任务未通过 schema 校验 | 停止执行 |
| `safety_check_failed` | 安全检查失败 | 停止执行 |
| `too_many_runs` | 扫描次数过多 | 拒绝执行 |
| `sweep_failed` | 扫描过程失败 | 记录失败点并返回日志 |
| `partial_success` | 部分参数成功、部分失败 | 输出成功和失败列表 |

---

# Tool 08：analyze_results

## 工具名称

```text
analyze_results
```

## 功能说明

读取仿真结果文件，例如 CSV、TXT 或报告输入文件，提取关键指标并生成简单结论。

这个工具只基于真实结果分析，不允许凭空总结。

## 当前已有基础

```text
reports/D32_result_summary_input.md
reports/D34_agent_demo_report.md
results/
```

## 建议后续模块

```text
modules/result_analyzer.py
```

## 输入

| 参数名 | 类型 | 是否必须 | 示例 | 说明 |
|---|---|---|---|---|
| `results_file` | string | 是 | `results/sweep_results.csv` | 结果文件 |
| `metrics` | list | 否 | `["MTF_30lpmm", "RMS_Spot"]` | 需要分析的指标 |
| `score_method` | string | 否 | `weighted_sum` | 评分方法 |

## 输出

| 输出名 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `status` | string | `success` | 是否成功 |
| `best_result` | dict | `{...}` | 最优结果 |
| `summary` | string | `MTF increases when thickness...` | 简要趋势 |
| `output_file` | string | `reports/D37_result_analysis.md` | 分析输出 |

## 安全边界

- 只能读取项目内结果文件。
- 不能伪造不存在的指标。
- 如果结果文件缺少必要列，应该返回错误。
- 不能写没有数据支撑的结论。

## 可能错误

| 错误类型 | 原因 | 处理方式 |
|---|---|---|
| `results_not_found` | 结果文件不存在 | 检查 results 目录 |
| `missing_metric` | 缺少指标列 | 提示缺少哪些列 |
| `invalid_results_format` | 文件格式不支持 | 拒绝分析 |
| `no_valid_data` | 数据为空或无效 | 返回错误 |

---

# Tool 09：prepare_summary_input

## 工具名称

```text
prepare_summary_input
```

## 功能说明

把仿真结果、图像路径、日志和任务配置整理成 AI 可以总结的输入文件。

这个工具对应之前 D32 的结果总结准备流程。

## 当前已有基础

```text
scripts/D32_prepare_result_summary.py
reports/D32_result_summary_input.md
prompts/result_summary_prompt.md
```

## 建议后续模块

```text
modules/report_generator.py
```

## 输入

| 参数名 | 类型 | 是否必须 | 示例 | 说明 |
|---|---|---|---|---|
| `task_file` | string | 否 | `configs/config_D31_from_task.yaml` | 任务文件 |
| `results_file` | string | 是 | `results/sweep_results.csv` | 结果文件 |
| `figures_dir` | string | 否 | `figures/` | 图片目录 |
| `log_file` | string | 否 | `logs/weekly_log_06.md` | 日志文件 |

## 输出

| 输出名 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `status` | string | `success` | 是否成功 |
| `summary_input_file` | string | `reports/D37_result_summary_input.md` | 给 AI 的总结输入 |
| `included_files` | list | `[...]` | 被整理进去的文件 |

## 安全边界

- 只整理项目内文件。
- 不要把私密路径、授权信息、个人账户信息写入总结输入。
- 如果图片或日志不存在，可以标记缺失，但不要报假结果。

## 可能错误

| 错误类型 | 原因 | 处理方式 |
|---|---|---|
| `results_not_found` | 结果文件不存在 | 停止生成 |
| `figure_missing` | 图片缺失 | 标记缺失并继续 |
| `write_failed` | 写入报告失败 | 检查 reports 目录 |

---

# Tool 10：generate_report

## 工具名称

```text
generate_report
```

## 功能说明

根据任务配置、运行结果、图像路径和分析结论生成 Markdown 报告。

D37 阶段只做接口设计，后续可以和 D32 / D34 的报告生成逻辑合并。

## 当前已有基础

```text
reports/D34_agent_demo_report.md
reports/D32_result_summary_input.md
```

## 建议后续模块

```text
modules/report_generator.py
```

## 输入

| 参数名 | 类型 | 是否必须 | 示例 | 说明 |
|---|---|---|---|---|
| `report_title` | string | 否 | `D37 Tool Design Report` | 报告标题 |
| `task_file` | string | 否 | `configs/config_D31_from_task.yaml` | 任务文件 |
| `results_file` | string | 否 | `results/sweep_results.csv` | 结果文件 |
| `analysis_summary` | string | 否 | `...` | 分析结论 |
| `output_file` | string | 否 | `reports/D37_tools_report.md` | 输出报告路径 |

## 输出

| 输出名 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `status` | string | `success` | 是否成功 |
| `report_file` | string | `reports/D37_tools_report.md` | 报告路径 |
| `message` | string | `report generated` | 运行说明 |

## 安全边界

- 报告必须基于真实任务、结果、日志或人工说明。
- 不允许凭空写“性能提升显著”。
- 输出路径必须在 `reports/` 中。
- 不允许覆盖已有重要报告，建议自动加版本号或日期。

## 可能错误

| 错误类型 | 原因 | 处理方式 |
|---|---|---|
| `missing_input` | 缺少必要输入 | 提示缺少内容 |
| `report_write_failed` | 报告写入失败 | 检查 reports 目录 |
| `unsafe_report_path` | 报告路径不安全 | 拒绝写入 |

---

## 7. 推荐调用流程

### 7.1 当前低配版流程

```text
load_task
↓
validate_task
↓
check_safety
↓
run_sweep
↓
prepare_summary_input
↓
AI 根据 reports/D32_result_summary_input.md 总结
```

对应当前已有脚本：

```text
scripts/D30_validate_task_yaml.py
scripts/D33_check_task_safety.py
scripts/D31_run_from_task_yaml.py
scripts/D32_prepare_result_summary.py
```

### 7.2 后续工具化流程

```text
load_task
↓
validate_task
↓
check_safety
↓
open_model
↓
set_parameter
↓
run_analysis
↓
run_sweep
↓
analyze_results
↓
prepare_summary_input
↓
generate_report
```

### 7.3 后续伪 MCP / tool registry 流程

```text
用户自然语言需求
↓
AI 生成 YAML
↓
tool_registry.py 调用工具
↓
validate_task
↓
check_safety
↓
run_sweep
↓
analyze_results
↓
generate_report
↓
AI 基于真实结果总结
```

---

## 8. MCP 对应关系

| MCP 概念 | 当前项目对应内容 |
|---|---|
| Host | ChatGPT、Claude、VS Code 等 AI 应用 |
| Client | AI 应用中连接工具服务的部分 |
| Server | 后续可能实现的 Zemax 工具服务，例如 tool registry 或 MCP Server |
| Tools | `load_task`、`validate_task`、`check_safety`、`open_model`、`set_parameter`、`run_analysis`、`run_sweep`、`analyze_results` |
| Resources | `configs/`、`results/`、`reports/`、`figures/`、`logs/`、`prompts/` 中的文件 |
| Prompts | `prompts/nl_to_yaml_prompt.md`、`prompts/result_summary_prompt.md` |

---

## 9. D37 不做的事情

D37 暂时不做以下事情：

1. 不重写整个项目结构。
2. 不把所有旧文件立刻重命名。
3. 不直接实现完整 MCP Server。
4. 不承诺所有 Zemax 分析类型都已经可运行。
5. 不直接支持多参数复杂优化。
6. 不删除已有可运行脚本。
7. 不覆盖原始 Zemax 模型。

D37 只完成“工具函数设计说明书”。

---

## 10. D38 衔接任务

D38 可以开始写一个简单的工具注册器：

```text
modules/tool_registry.py
```

或者先写演示脚本：

```text
scripts/D38_tool_registry_demo.py
```

D38 的目标是让工具可以被统一管理，例如：

```text
list_tools()
call_tool("validate_task", ...)
call_tool("check_safety", ...)
call_tool("run_sweep", ...)
```

这样后面才能逐步升级成伪 MCP Server 或真正 MCP Server。

---

## 11. D37 检查清单

完成 D37 后，用下面清单检查：

- [ ] `docs/D37_tools_spec.md` 已创建。
- [ ] 工具名称统一使用英文小写和下划线。
- [ ] 每个工具都有功能说明。
- [ ] 每个工具都有输入表格。
- [ ] 每个工具都有输出表格。
- [ ] 每个工具都有安全边界。
- [ ] 每个工具都有可能错误。
- [ ] 文档没有写不存在的 `src/zemax_agent/` 目录。
- [ ] 文档中的日志路径使用 `logs/weekly_log_06.md`。
- [ ] 文档没有说 D37 已经完成完整 MCP Server。
- [ ] 文档能解释 D38 为什么要做 `tool_registry.py`。

---

## 12. 参考资料

- Model Context Protocol 官方文档：MCP 是连接 AI 应用与外部工具、数据和工作流的开放标准。
- Model Context Protocol Tools 规范：Tools 是 MCP Server 暴露给语言模型调用的函数，每个工具需要名称、说明和输入结构。
- Ansys OpticStudio ZOS-API Python 文档：ZOS-API 支持通过 Python 与 OpticStudio 通信，用于执行自动化操作。

---

## 13. 今日总结

D37 的重点不是新增仿真结果，而是把前面已经跑通的 Zemax-Agent 流程拆成一组标准工具函数。

当前项目中，已有：

```text
任务配置：configs/
执行脚本：scripts/
提示词：prompts/
报告：reports/
日志：logs/
模块目录：modules/
```

所以后续工具函数应该逐步整理到 `modules/` 中，而不是重新创建 `src/zemax_agent/` 目录。

一句话总结：

D37 是从“脚本能跑”走向“工具可调用”的过渡步骤。只有先把 `load_task`、`validate_task`、`check_safety`、`open_model`、`set_parameter`、`run_analysis`、`run_sweep`、`analyze_results` 等接口设计清楚，后续 AI Agent / MCP 才能安全、稳定、可追踪地调用 Zemax 自动化流程。
