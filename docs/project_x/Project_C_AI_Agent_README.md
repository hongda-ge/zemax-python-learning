# Project C：AI Agent 辅助 Zemax 自动化工作流

## 1. 项目定位

本项目是一个低配版 AI Agent 辅助 Zemax 自动化工作流。

它的目标不是让 AI 直接替代 Zemax，也不是让 AI 凭空生成光学优化结果，而是让 AI 参与到以下环节：

1. 理解自然语言仿真需求。
2. 辅助生成结构化 YAML 任务文件。
3. 通过 JSON Schema 检查任务格式。
4. 通过 Safety Policy 检查任务安全边界。
5. 将 YAML 任务转换为 Python 工作流配置。
6. 整理仿真结果目录，生成 AI 可总结的 Markdown 材料。
7. 形成可展示的 Agent demo 报告。

当前版本是半自动工作流：自然语言到 YAML 的转换暂时由 ChatGPT/人工完成，Python 从 YAML 文件开始接管。

---

## 2. 当前真实流程

当前流程为：

```text
自然语言需求
        ↓
ChatGPT / 人工生成 YAML 任务
        ↓
Python 读取 YAML
        ↓
JSON Schema 校验
        ↓
Safety Policy 校验
        ↓
D31 生成 workflow config
        ↓
D32 生成结果总结材料
        ↓
D34 生成 demo 报告