# Weekly Log 05

## D29：Agent 的正确定位

### 今日完成

1. 创建 natural_language_task_template.md，用于描述自然语言仿真任务模板。
2. 创建 agent_boundary.md，用于明确 AI、Python、ZOS-API 和 Zemax 的职责边界。
3. 创建 D29_example_tasks.md，用于保存自然语言任务示例。
4. 创建 D29_agent_positioning.md，总结 AI Agent 在项目中的定位。

### 今日理解

AI Agent 不是直接替代 Zemax，而是作为任务理解层和流程编排层。  
真正执行仿真的仍然是 Python/ZOS-API/Zemax。  
AI 只能根据真实导出的 CSV、图像和日志总结结果，不能凭空编造优化结论。

### 明日计划

开始 D30：自然语言转 JSON。  
下一步需要定义 task_schema.json，用来约束 AI 生成的结构化任务。

## D30：自然语言转 YAML，并使用 JSON Schema 校验

### 今日完成

1. 创建 `configs/task_schema.json`，用于约束 AI 生成的 Zemax 自动化任务。
2. 创建 `examples/D30_task_example.yaml`，将自然语言扫描任务转成结构化 YAML。
3. 创建 `examples/D30_natural_language_request.md`，记录原始自然语言需求。
4. 创建 `docs/D30_natural_language_to_yaml.md`，总结自然语言转 YAML 的流程。
5. 创建 `scripts/D30_validate_task_yaml.py`，实现 YAML 读取、schema 校验和额外安全检查。
6. 测试合法 YAML，可以正常通过校验。
7. 测试错误单位和过小 max_runs，可以被程序拦截。

### 今日理解

D30 的重点不是直接运行 Zemax，而是建立自然语言任务和自动化脚本之间的中间层。

本项目继续使用 YAML 作为任务配置文件，保持和前四周配置体系一致。

JSON Schema 用来校验 YAML 读取后的 Python 字典，限制字段、类型、单位、输出路径和最大运行次数。

### 明日计划

开始 D31：YAML 调用脚本。

下一步需要让 Python 读取 `D30_task_example.yaml`，并把其中的 surface、parameter、start、end、step、metrics、outputs 等信息传给现有的 `zemax_runner.py` 或 `workflow_runner.py`。

## D31：YAML 调用脚本

### 今日完成

1. 创建 `scripts/D31_run_from_task_yaml.py`。
2. 实现读取 `examples/D30_task_example.yaml`。
3. 复用 `configs/task_schema.json` 进行结构校验。
4. 增加额外安全检查，包括最大运行次数、输出路径、只读模型和 dry-run 原则。
5. 实现 dry-run 任务预览，输出扫描参数、预计运行次数和输出目录。
6. 自动生成 `configs/config_D31_from_task.yaml`，为后续接入 `workflow_runner.py` 做准备。

### 今日理解

D31 的重点不是立即运行 Zemax，而是把 AI 生成的 YAML 任务转成 Python 脚本可以稳定读取的输入格式。

当前链路为：

自然语言需求 → YAML 任务 → schema 校验 → dry-run 预览 → workflow config

这样可以避免 AI 生成的任务直接进入仿真执行阶段，提高安全性和可控性。

### 明日计划

继续 D32：结果自动总结。

下一步需要整理一个 `result_summary_prompt.md`，让 AI 根据真实 CSV、图像路径和 best_design 信息生成 200–300 字结果总结。


## D32：结果自动总结

### 今日完成

1. 创建结果总结提示词 `prompts/result_summary_prompt.md`。
2. 创建并运行 `scripts/D32_prepare_result_summary.py`。
3. 成功生成 `reports/D32_result_summary_input.md`。
4. 检查结果目录后发现当前缺少 CSV、图像、JSON 和日志文件。
5. 根据缺失情况生成了不编造数据的结果总结。

### 今日理解

D32 的重点不是让 AI 凭空写优化结论，而是先把真实结果整理成 AI 可读取的材料。  
如果没有 CSV、图像或 best_design 文件，AI 只能说明结果缺失，不能声称 MTF 提升或 Spot 改善。

### 后续补充

等后面真正运行 Zemax 扫描，生成 `sweep_results.csv`、结果图和 `best_design.json` 后，可以重新运行 D32 脚本，生成正式结果总结。

## D33：安全边界

### 今日完成

1. 创建 `configs/safety_policy.yaml`，定义项目级安全策略。
2. 创建 `modules/task_safety.py`，封装路径、参数、运行次数和执行权限检查函数。
3. 创建 `scripts/D33_check_task_safety.py`，作为 D33 安全检查入口。
4. 成功对 `examples/D30_task_example.yaml` 进行安全检查。
5. 测试了不安全输出路径、取消只读保护、过大扫描范围和过小步长等错误情况。
6. 创建 `docs/D33_safety_boundary.md`，记录安全边界设计思路。

### 今日理解

D33 的重点不是继续增加 Zemax 分析功能，而是给 AI 生成的任务加安全护栏。

JSON Schema 负责检查任务格式，Python Safety Check 负责检查项目级安全规则。

任何 AI 生成任务都不能直接运行，必须经过 schema 校验、安全策略校验和 dry-run 预览。

### 明日计划

开始 D34：Agent demo。

下一步需要把自然语言需求、YAML 任务、任务校验、dry-run、结果总结材料串起来，形成一个可展示的低配版 Agent workflow demo。

## D34：Agent Demo 演示

### 今日完成

1. 成功运行 `scripts/D34_agent_demo.py`。
2. 串联自然语言需求、YAML 任务、Schema 校验、Safety Policy 校验、D31 配置生成和 D32 结果总结材料生成。
3. 自动生成 `reports/D34_agent_demo_report.md`。
4. 修复了 Windows PowerShell 下 emoji 输出导致的 GBK 编码报错，将终端输出标记统一改为 `[OK]` / `[ERROR]` / `[INFO]` / `[WARN]` 或中文方括号标记。
5. 明确当前 demo 不直接运行 Zemax，只展示低配版 AI Agent 工作流骨架。

### 今日理解

D34 的核心不是得到真实优化结果，而是形成一个可解释、可检查、可展示的 Agent demo。

当前流程为：

自然语言需求 → YAML → Schema 校验 → Safety 校验 → workflow config → result summary input → demo report

这说明 AI Agent 的作用不是直接替代 Zemax，而是在已有 Python/ZOS-API 自动化脚本外层进行任务理解、任务校验、流程编排和结果总结。

### 当前局限

当前 demo 尚未运行真实 Zemax 参数扫描，因此没有真实 CSV、MTF 图、Spot 图和 best_design 文件。D32 只能生成缺失信息型总结，不能编造优化结论。

### 明日计划

开始 D35：第 5 周复盘。

下一步需要整理项目 C README，总结 AI Agent 低配版的输入、输出、边界、当前成果和后续 Project-X 扩建方向。
### D34 补充理解：自然语言识别缺口

今天发现 D34 demo 中，自然语言并不是由 Python 自动识别的。

当前流程中，自然语言写在 `examples/D30_natural_language_request.md`，然后由 ChatGPT/人工根据 `prompts/nl_to_yaml_prompt.md` 转换成 `examples/D30_task_example.yaml`。

Python 当前从 YAML 文件开始接管，负责 Schema 校验、Safety Policy 校验、D31 配置生成和 D32 总结材料生成。

因此，当前 demo 应准确表述为：

自然语言需求 → ChatGPT/人工生成 YAML → Python 校验和编排

后续 Project-X 或 MCP 阶段可以再接入 LLM API，实现真正的自动自然语言解析。


# D35 Week 5 Review

## AI Agent 低配版

本周重点不是直接运行复杂 Zemax 优化，而是建立一个安全、可解释、可扩展的 Agent 辅助仿真工作流。

本周主线为：

```text
自然语言需求
        ↓
ChatGPT/人工生成 YAML
        ↓
Python 读取 YAML
        ↓
Schema 校验
        ↓
Safety 校验
        ↓
Workflow Config
        ↓
Result Summary Input
        ↓
Demo Report

本周完成了以下内容：

1. 明确 AI Agent 在 Zemax 自动化项目中的定位。
2. 设计自然语言任务模板和 YAML 任务格式。
3. 使用 JSON Schema 校验 YAML 任务结构。
4. 设计 Safety Policy，限制参数范围、输出路径、运行次数和只读权限。
5. 实现 YAML 任务到 workflow config 的转换。
6. 实现结果目录到 AI 总结材料的整理流程。
7. 串联形成 D34 低配版 Agent demo。
8. 生成 `D34_agent_demo_report.md` 作为阶段展示材料。


主要文件：

- `docs/Project_C_AI_Agent_README.md`：项目 C 完整说明
- `docs/D35_week5_review.md`：第 5 周学习复盘
- `reports/D35_week5_summary.md`：第 5 周总结报告
- `scripts/D34_agent_demo.py`：低配版 Agent demo 总控脚本
- `reports/D34_agent_demo_report.md`：D34 自动生成 demo 报告
- `configs/task_schema.json`：任务结构校验规则
- `configs/safety_policy.yaml`：项目安全策略
- `modules/task_safety.py`：安全检查函数库