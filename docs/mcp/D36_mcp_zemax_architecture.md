# D36 MCP 与 Zemax 自动化脚本关系图

## 1. 当前低配版流程

```text
User
  ↓
ChatGPT
  ↓ 生成 JSON/YAML
task.json / task.yaml
  ↓
run_from_task.py
  ↓
zemax_runner.py
  ↓
ZOS-API
  ↓
Zemax OpticStudio
  ↓
results / figures / report
  ↓
ChatGPT 总结结果

## 2. 未来MCP工具化流程
User
  ↓
Host：AI 应用
  ↓
Client：连接 MCP Server 的组件
  ↓
Server：zemax_mcp_server.py
  ↓
Tools：
  - validate_task
  - dry_run_task
  - run_zemax_sweep
  - analyze_results
  - generate_report
  ↓
Python 自动化脚本：
  - task_loader.py
  - task_validator.py
  - zemax_runner.py
  - result_analyzer.py
  - report_generator.py
  ↓
ZOS-API
  ↓
Zemax OpticStudio
  ↓
Resources：
  - sweep_results.csv
  - best_design.json
  - MTF_vs_parameter.png
  - report.md
  - run_log.txt
  ↓
AI 基于真实结果生成总结