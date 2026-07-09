# D32 Result Auto Summary

## 今日目标

D32 的目标是建立结果自动总结流程。

本阶段不直接运行 Zemax，而是把已有仿真结果整理成 AI 可以读取和总结的材料。

## D32 的输入

可能包括：

- YAML 任务文件
- workflow 配置文件
- sweep_results.csv
- best_design.json
- MTF 图像
- Spot 图像
- before-after 对比图
- 运行日志

## D32 的输出

生成：

- reports/D32_result_summary_input.md

该文件会包含任务配置摘要、结果文件路径、CSV 列名、CSV 前几行数据和需要 AI 总结的要求。

## 当前流程

仿真结果文件  
↓  
Python 脚本收集 CSV、图像、JSON、日志  
↓  
整理成 Markdown  
↓  
把 Markdown 内容交给 AI  
↓  
AI 生成 200–300 字结果总结

## 注意事项

AI 不能凭空编造结果。

如果 CSV 中没有具体数值，AI 不能写具体提升百分比。

如果只提供图像路径，AI 只能说明图像已生成，不能假装已经看过图像细节。

结果总结必须基于真实数据。