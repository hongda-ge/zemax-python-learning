# Natural Language Task Template for Zemax Agent

## 1. 任务目标

请根据用户的自然语言需求，提取 Zemax 自动化仿真的关键信息，并整理成结构化任务描述。

AI 只负责理解需求、整理参数和生成配置，不直接修改 Zemax 原始模型，不直接编造仿真结果。

## 2. 用户需要提供的信息

用户应尽量说明以下内容：

- 仿真软件：Zemax / COMSOL
- 任务类型：参数扫描 / 单次分析 / 优化前后对比 / 报告生成
- 模型文件：例如 Double_Gauss_28_degree_field.zmx
- 扫描对象：表面编号、参数名称、单位
- 参数范围：起点、终点、步长
- 评价指标：MTF、RMS Spot、Ray Fan、Merit Function 等
- 输出内容：CSV、图像、报告、最优参数 JSON
- 安全要求：是否允许修改原始模型，是否只读，输出路径限制

## 3. AI 输出要求

AI 应输出：

- 任务摘要
- 参数提取结果
- 需要确认的问题
- 后续可转换成 JSON 的结构化内容

AI 不应输出：

- 未经仿真得到的性能提升结论
- 虚构的 MTF / Spot / Merit Function 数值
- 超出安全范围的扫描参数
- 覆盖原始模型的操作建议