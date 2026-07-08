# Week 06 Log

## D36 - 理解 MCP 架构

日期：2026-07-06

### 今日目标

理解 MCP / 工具化进阶的基本架构，弄清楚 Host、Client、Server、Tools、Resources、Prompts 分别是什么，并把这些概念对应到自己的 Zemax-Agent 自动化项目中。

### 今天看了什么资料

- 学习了 MCP 的基本概念：MCP 是让 AI 应用连接外部工具和数据源的一套标准接口。
- 了解了 MCP 架构中 Host、Client、Server 的关系。
- 重点理解了 Tools、Resources、Prompts 三个概念：
  - Tools：AI 可以调用的可执行函数；
  - Resources：AI 可以读取的上下文数据；
  - Prompts：可复用的任务模板。

### 今天理解了什么

1. MCP 不是直接控制 Zemax 的工具，它是 AI 和外部工具之间的连接协议。
2. 在我的项目中，真正控制 Zemax 的仍然是 Python / ZOS-API 脚本。
3. MCP 的作用是把已有的 Zemax 自动化脚本包装成 AI 可以调用的工具。
4. Host 可以理解为 ChatGPT、Claude、VS Code 等 AI 应用。
5. Server 可以理解为后续要写的 `zemax_mcp_server.py` 或低配版 `tool_registry.py`。
6. Tools 可以对应到 `validate_task`、`dry_run_task`、`run_zemax_sweep`、`analyze_results`、`generate_report` 等函数。
7. Resources 可以对应到 `task_schema.json`、`config.yaml`、`sweep_results.csv`、`best_design.json`、运行日志和结果图。
8. Prompts 可以对应到“自然语言转 YAML 模板”“结果总结模板”“安全检查模板”。

### 今天跑通了什么

今天没有运行新的 Zemax 仿真程序，主要完成 MCP 架构理解和项目关系梳理。

已完成：

- 梳理 MCP 六个核心概念；
- 理解 MCP 与 ZOS-API 的区别；
- 明确第 6 周学习重点是“把已有脚本工具化”，而不是重新写一套仿真流程；
- 完成 MCP 与 Zemax-Agent 项目的对应关系整理。

### 今天导出了什么图/表/脚本

今天没有导出 Zemax 图表。

计划整理或已整理的文档：

- `docs/D36_mcp_architecture_notes.md`
- `docs/D36_mcp_zemax_architecture.md`
- `weekly_log_06.md`

### 今天的架构理解

当前低配版流程：

```text
用户自然语言需求
↓
ChatGPT 生成 JSON / YAML
↓
run_from_task.py 读取任务
↓
zemax_runner.py 调用 ZOS-API
↓
Zemax OpticStudio 执行仿真
↓
导出 CSV / 图 / 报告
↓
AI 根据结果总结



未来 MCP 工具化流程：

用户自然语言需求
↓
Host：AI 应用
↓
Client：连接 MCP Server
↓
Server：zemax_mcp_server.py
↓
Tools：validate_task / dry_run_task / run_sweep / analyze_results
↓
Python / ZOS-API 脚本
↓
Zemax OpticStudio
↓
Resources：CSV / 图 / 日志 / 报告
↓
AI 基于真实结果总结
```

## D37 - 工具函数设计

### 今日目标

完成 Zemax-Agent 工具函数设计，把前面 D29-D35 已经跑通的自然语言任务、YAML 校验、安全检查、仿真执行和结果总结流程拆成更清晰的工具接口。

### 今天完成的内容

1. 完成了文件命名规范整理：
   - `docs/D37_file_naming_rules.md`

2. 完成了工具函数设计说明书：
   - `docs/D37_tools_spec.md`

3. 整理了工具学习记录 Word：
   - `docs/D37_tools_learning_notes.docx`

4. 初步设计了 10 个工具：
   - `load_task`
   - `validate_task`
   - `check_safety`
   - `open_model`
   - `set_parameter`
   - `run_analysis`
   - `run_sweep`
   - `analyze_results`
   - `prepare_summary_input`
   - `generate_report`

### 今天理解了什么

1. 输入名字就是工具调用时需要传入的参数名。
2. 输出名字就是工具运行结束后返回给下一步使用的结果字段。
3. 类型用于说明这个字段应该是什么数据，例如 `string`、`int`、`bool`、`list`、`dict`。
4. D37 不是为了马上实现所有工具代码，而是先把工具接口设计清楚。
5. 后续 D38 可以基于这些工具说明写 `tool_registry.py`，让工具可以被统一注册和调用。

### 今天没有做的内容

今天没有重新跑 Zemax，也没有实现完整 MCP Server。D37 的重点是工具接口设计和项目文件命名规范。

### 明天第一件事

开始 D38：伪 MCP Server / tool registry。

目标是写一个简单的工具注册器，先实现：

- `list_tools()`
- `get_tool_spec()`
- `call_tool()`

先用模拟函数跑通工具调用逻辑，不急着真正调用 Zemax。

### 今日总结

D37 已完成。当前已经把 Zemax-Agent 自动化流程拆成了多个标准工具接口，为 D38 的 tool registry 和后续 MCP 工具化调用打基础。


## D38 - 伪 MCP Server / Tool Registry

### 今日目标

实现一个低配版 tool registry，用 CLI 的方式模拟 MCP 工具调用流程。今天不追求完整 MCP 协议，也不直接连接 Zemax，重点是让工具可以被统一注册、查看和调用。

### 今天完成的内容

1. 新建工具注册模块：
   - `modules/tool_registry.py`

2. 新建 D38 演示脚本：
   - `scripts/D38_tool_registry_demo.py`

3. 实现了三个核心接口：
   - `list_tools()`
   - `get_tool_spec(tool_name)`
   - `call_tool(tool_name, args)`

4. 初步注册了 10 个工具：
   - `load_task`
   - `validate_task`
   - `check_safety`
   - `open_model`
   - `set_parameter`
   - `run_analysis`
   - `run_sweep`
   - `analyze_results`
   - `prepare_summary_input`
   - `generate_report`

### 今天跑通了什么

运行：

```powershell
python scripts/D38_tool_registry_demo.py

终端成功输出：

工具列表；
run_sweep 的工具说明；
load_task、validate_task、check_safety、run_sweep、run_analysis 的模拟调用结果；
unknown_tool 的错误处理结果。
```

### 今天遇到的问题

一开始运行时报错：
TypeError: unsupported operand type(s) for |: '_GenericAlias' and 'NoneType'
原因是代码中使用了 Python 3.10 才支持的类型写法：

Dict[str, Any] | None

当前环境是 .venv_zosapi38，更适合 Python 3.8 写法，所以改成：

Optional[Dict[str, Any]]

并在文件顶部加入：
from typing import Optional
修改后 D38 demo 成功运行。

## D39 - 参数校验

今日运行 `python scripts/D39_validation_demo.py` 成功。

验证结果：
- 合法的 `run_analysis` 输入可以通过；
- 不支持的 `analysis_type = ray_fan` 被拒绝；
- `set_parameter` 缺少 `value` 被拒绝；
- `surface = 0` 被拒绝；
- `parameter = glass` 被拒绝；
- `max_runs = 999` 被拒绝；
- 多余字段 `dangerous_extra_field` 被拒绝；
- 项目目录外路径 `../../secret_config.yaml` 被拒绝。

结论：D39 参数校验已成功接入 tool registry。当前工具调用已经从 D38 的“能统一调用”，升级为 D39 的“调用前先校验，非法参数拒绝执行”。


# D40 长任务管理学习笔记

## 今日目标

D40 的目标是为 Zemax-Agent 工具化流程加入长任务管理机制。

今天重点不是新增 Zemax 仿真功能，而是让每次任务运行都能被追踪。

## 为什么需要长任务管理

真实 Zemax 参数扫描可能耗时较长，如果只在终端打印结果，任务失败后很难知道：

- 跑到哪一步；
- 哪一步失败；
- 输出文件在哪里；
- 是否已经完成；
- 是否可以继续或重试。

因此需要为每次运行加入：

- run_id；
- 独立运行目录；
- status.json；
- events.jsonl。

## 核心文件

```text
modules/run_manager.py
scripts/D40_long_task_demo.py
results/runs/<run_id>/status.json
results/runs/<run_id>/events.jsonl


## D41 - 整合演示：Agent Tool Demo

### 今日目标

把 D38、D39、D40 串成一个完整的工具调用演示流程。通过 3 个典型案例展示 tool registry、输入校验和长任务管理如何协同工作。

### 今天完成的内容

1. 新增 D41 学习笔记：
   - `docs/D41_integrated_tool_demo_notes.md`

2. 新增 D41 整合演示脚本：
   - `scripts/D41_agent_tool_demo.py`

3. 设计并运行了 3 个典型案例：
   - Case 1：正常工具化仿真流程；
   - Case 2：非法参数被输入校验拦截；
   - Case 3：危险路径被安全检查拦截。

### 今天跑通了什么

运行：

```powershell
python scripts/D41_agent_tool_demo.py
终端成功输出 3 个案例，并为每个案例生成独立运行目录：

results/runs/<D41_run_id>/status.json
results/runs/<D41_run_id>/events.jsonl


# D42 第 6 周复盘与最终包装

## 1. 今日目标

D42 的目标是整理第 6 周 MCP / 工具化进阶阶段的所有成果，补齐说明文档、运行截图、README 内容和阶段总结，为 GitHub 展示和面试讲解做准备。

D42 不是新增功能，而是项目整理和成果包装。

---

## 2. 第 6 周主线

第 6 周的主线是从“Agent 低配版”升级到“工具化调用雏形”。

整体路线：

```text
D36：理解 MCP 架构
↓
D37：设计工具函数
↓
D38：实现 tool registry
↓
D39：加入输入参数校验
↓
D40：加入长任务状态管理
↓
D41：整合成 Agent Tool Demo
↓
D42：整理资料、截图、README 和总结报告