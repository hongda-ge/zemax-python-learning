# Example Natural Language Tasks

## 示例 1：参数扫描任务

用户需求：

请基于 Double Gauss 示例镜头，对第 6 面 thickness 进行参数扫描，范围为 -1 mm 到 1 mm，步长为 0.2 mm。每一组参数都导出 MTF 和 RMS Spot，最后保存 CSV，并筛选出综合表现最好的参数。

AI 应理解为：

- software: Zemax
- task_type: parameter_sweep
- model_file: Double_Gauss_28_degree_field.zmx
- surface: 6
- parameter: thickness
- unit: mm
- start: -1.0
- end: 1.0
- step: 0.2
- metrics:
  - MTF
  - RMS_Spot
- outputs:
  - csv
  - figures
  - best_design
  - report

限制条件：

- 不修改原始模型
- 每组结果另存为新文件
- 输出路径限制在 results/ 下
- AI 不能提前声称性能提升，必须等 CSV 和图表生成后再总结