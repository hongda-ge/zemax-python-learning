# D30 Natural Language Request

## 用户自然语言需求

请基于 Double Gauss 示例镜头，对第 6 面 thickness 进行参数扫描。

扫描范围为 -1 mm 到 1 mm，步长为 0.2 mm。

每一组参数都需要导出 MTF 和 RMS Spot 指标。

最后保存 CSV、结果图、最优参数文件和报告草稿。

安全要求：

1. 不要覆盖原始 Zemax 模型。
2. 输出文件必须保存到 results 目录。
3. 运行前先 dry-run，确认扫描次数。
4. 最大运行次数不能超过 20 次。

## AI 应生成的 YAML 文件

见：

examples/D30_task_example.yaml