# D30 Natural Language to YAML

## 今日目标

D30 的目标是把自然语言仿真需求转化为结构化 YAML 任务文件，并使用 JSON Schema 对 YAML 内容进行校验。

## 为什么使用 YAML

本项目在前四周已经使用 YAML 作为配置文件格式，例如：

- config_zemax.yaml
- config_D15_cooke_thickness.yaml
- config_D16_cooke_thickness_sweep.yaml

为了保持项目风格统一，D30 继续使用 YAML 作为任务配置文件。

## 为什么仍然使用 JSON Schema

YAML 文件被 Python 读取后，会变成普通的 dict/list/str/number/bool 数据结构。

JSON Schema 可以对这些数据结构进行字段、类型、范围和枚举值校验。

因此，本项目采用：

自然语言 → YAML → Python dict → JSON Schema 校验 → Zemax 自动化脚本

## AI 的职责

AI 负责：

1. 理解自然语言任务。
2. 提取模型文件、表面编号、扫描参数、单位、范围和步长。
3. 生成 YAML 任务文件。
4. 检查信息是否缺失。

AI 不负责：

1. 不直接运行 Zemax。
2. 不直接修改原始模型。
3. 不凭空生成 MTF 或 Spot 结果。
4. 不绕过 schema 校验。

## D30 产物

- configs/task_schema.json
- examples/D30_task_example.yaml
- examples/D30_natural_language_request.md
- scripts/D30_validate_task_yaml.py