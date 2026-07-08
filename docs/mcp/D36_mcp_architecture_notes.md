# D36 理解 MCP 架构

## 今日目标

理解 MCP 中 Host、Client、Server、Tools、Resources、Prompts 的含义，并把它们对应到我的 Zemax-Agent 自动化项目中。

## 1. MCP 是什么

MCP 是 Model Context Protocol，可以理解为 AI 应用连接外部工具和数据源的一套标准接口。

在我的项目中，MCP 的作用不是直接做光学仿真，而是把已有的 Python/ZOS-API 脚本包装成 AI 可以调用的工具。

## 2. Host

Host 是用户直接使用的 AI 应用，例如 ChatGPT、Claude、Cursor、VS Code 等。

在我的项目中，Host 负责接收用户的自然语言需求。

## 3. Client

Client 是 Host 内部负责连接 MCP Server 的组件。

它负责发现 Server 提供了哪些工具，并把 AI 的调用请求发送给 Server。

## 4. Server

Server 是暴露工具的程序。

在我的项目中，未来可以写成 zemax_mcp_server.py，负责暴露 Zemax 自动化相关工具。

## 5. Tools

Tools 是 AI 可以调用的函数。

我项目中可能的 Tools 包括：

- validate_task：检查任务配置是否合法
- dry_run_task：预估扫描任务数量
- run_zemax_sweep：执行 Zemax 参数扫描
- analyze_results：分析 CSV 并筛选最优结果
- generate_report：生成报告

## 6. Resources

Resources 是 AI 可以读取的上下文数据。

我项目中的 Resources 包括：

- task_schema.json
- config_zemax.yaml
- sweep_results.csv
- best_design.json
- result_summary.md
- run_log.txt

## 7. Prompts

Prompts 是可复用的任务模板。

我项目中的 Prompts 包括：

- 自然语言转 YAML 模板
- 结果总结模板
- 安全检查模板
- 面试讲解模板

## 8. MCP 与 ZOS-API 的关系

ZOS-API 是真正控制 Zemax 的接口，负责打开模型、修改参数、运行分析和导出结果。

MCP 不直接替代 ZOS-API。MCP 是更上层的工具调用协议，它让 AI 能够通过标准方式调用我封装好的 ZOS-API 脚本。

## 9. 今日总结

今天我理解了 MCP 的基本架构。我的项目中，MCP Server 可以理解为 Zemax 自动化工具盒子，Tools 是里面的具体函数，Resources 是结果文件和配置文件，Prompts 是任务模板。后续 D37 会开始把仿真功能拆成更清晰的工具函数。