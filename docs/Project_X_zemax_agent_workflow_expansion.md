# Project-X：Zemax Agent Workflow Expansion

## 中文名称

项目 X：Zemax-Agent 自动化工作流扩建计划

## 项目定位

当前项目已经完成了 Zemax + Python/ZOS-API 自动化的基础链路，包括：

1. Python 连接 Zemax。
2. 读取和修改部分 LDE 参数。
3. 基于 YAML 配置运行简单参数扫描。
4. 导出 CSV、图像和阶段性报告。
5. 使用 JSON Schema 校验 AI 生成的 YAML 任务文件。

但是当前项目仍然只是一个最小可行原型，主要支持某一表面的 thickness 固定步长扫描，距离完整的光学系统优化还有明显差距。

Project-X 的目标不是立即重写项目，而是在完成第 5 周和第 6 周任务之后，对整个项目进行系统扩建和查漏补缺。

## 为什么暂时不做

当前阶段的重点是完成：

- 第 5 周：AI Agent 低配版
- 第 6 周：MCP / 工具化进阶

先把自然语言到 YAML、YAML 校验、脚本调用、工具函数边界、dry-run、安全检查等基础流程跑通。

等这些内容上手之后，再进入 Project-X，对函数库、YAML schema、优化策略和结果分析能力进行全面升级。

## 扩建方向一：函数库扩建

后续需要将当前零散脚本逐步整理成稳定函数库。

建议模块包括：

```text
modules/
├─ zemax_runner.py
├─ analysis_runner.py
├─ result_analyzer.py
├─ optimizer.py
├─ task_loader.py
├─ task_validator.py
└─ report_generator.py