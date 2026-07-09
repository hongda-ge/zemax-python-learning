# D33 Safety Boundary

## 今日目标

D33 的目标是为 AI 生成的 Zemax 自动化任务增加安全边界。

本阶段重点不是运行 Zemax，而是在任务进入仿真执行前进行安全检查。

## 为什么需要安全边界

AI 生成的 YAML 任务可能存在以下风险：

1. 参数范围过大。
2. 步长过小，导致扫描次数过多。
3. 输出路径不安全。
4. 直接覆盖原始 Zemax 模型。
5. 未经过 dry-run 就执行。
6. 生成了当前函数库不支持的参数类型。

## 安全检查分层

### 第一层：JSON Schema

用于检查字段结构、类型、枚举值和基本格式。

例如：

- software 必须是 zemax
- unit 必须是 mm
- output_dir 必须以 results/ 开头
- surface 必须是正整数

### 第二层：Python Safety Check

用于检查更具体的项目安全规则。

例如：

- 输出路径必须真的位于 results/ 目录内
- model_file 不能包含 ..
- 预计扫描次数不能超过 max_runs
- 扫描次数不能超过 hard limit
- 原始模型必须只读
- 必须先 dry-run
- 参数值不能超过 safety_policy.yaml 规定的范围

## 新增文件

- configs/safety_policy.yaml
- modules/task_safety.py
- scripts/D33_check_task_safety.py
- docs/D33_safety_boundary.md

## 今日理解

D33 的核心是：AI 只能生成任务，不能绕过安全边界直接控制 Zemax。

任何 AI 生成的任务，都必须先经过：

YAML 读取 → Schema 校验 → Safety Policy 校验 → Dry-run 预览 → 人工确认 → 执行

## 后续方向

后续 Project-X 中，可以把 safety_policy.yaml 扩展到：

- 多参数扫描
- material 修改
- semi-diameter 修改
- field / wavelength 修改
- 多变量组合扫描
- Zemax Merit Function 优化任务