# D29 Agent Positioning

## 今日目标

理解 AI Agent 在 Zemax 自动化项目中的正确定位，明确 AI、Python、ZOS-API 和 Zemax 各自负责什么。

## 核心理解

AI Agent 不是直接替代 Zemax，也不是直接生成仿真结果。  
在本项目中，AI Agent 主要负责理解自然语言需求，并将用户需求整理成结构化任务配置。

真正执行仿真的仍然是 Python 脚本和 ZOS-API。  
Zemax 负责真实的光学建模、参数修改、分析运行和结果导出。

## 当前项目流程

自然语言需求  
↓  
AI Agent 理解任务  
↓  
生成结构化配置  
↓  
Python 读取配置  
↓  
ZOS-API 调用 Zemax  
↓  
导出 CSV、图像和报告  
↓  
AI 根据真实结果总结趋势

## AI Agent 可以做什么

1. 理解用户的自然语言仿真需求。
2. 提取模型文件、扫描参数、单位、范围和评价指标。
3. 生成 JSON/YAML 形式的任务配置。
4. 检查参数范围、单位和输出路径是否合理。
5. 根据真实 CSV 和图表总结结果。

## AI Agent 不可以做什么

1. 不直接修改原始 Zemax 模型。
2. 不凭空生成 MTF、Spot、Merit Function 等结果。
3. 不绕过 Python/ZOS-API 直接控制 Zemax。
4. 不生成无限范围或危险路径的任务。
5. 不在没有数据支撑的情况下声称性能提升。

## 今日结论

D29 的重点不是写复杂代码，而是明确 Agent 的边界。  
只有先把 Python/ZOS-API 自动化流程封装好，AI Agent 才有真实工具可以调用。