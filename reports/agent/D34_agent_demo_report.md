# D34 Agent Demo Report

生成时间：2026-07-05 17:22:35

---

## 1. Demo 目标

本 demo 用于展示低配版 AI Agent 工作流：自然语言需求 → YAML 任务 → Schema 校验 → Safety 校验 → D31 工作流配置生成 → D32 结果总结材料生成。

本 demo 默认不直接运行 Zemax，不修改原始模型。

### 自然语言需求

```markdown
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
```

## 2. YAML 任务摘要

- 软件：zemax
- 任务类型：parameter_sweep
- 模型文件：`Double_Gauss_28_degree_field.zmx`
- 扫描表面：Surface 6
- 扫描参数：thickness
- 单位：mm
- 扫描范围：-1.0 到 1.0，步长 0.2
- 输出目录：`results/D30_double_gauss_sweep`
- 最大运行次数：20
- 原始模型只读：True
- 先 dry-run：True

## 3. Schema 校验结果

通过。

## 4. Safety Policy 校验结果

通过。

## 5. D31：YAML 任务转 workflow config

- 返回码：`0`

命令：

```text
C:\Users\20181\Desktop\Zemax\02_zosapi_python\.venv_zosapi38\Scripts\python.exe C:\Users\20181\Desktop\Zemax\02_zosapi_python\scripts\D31_run_from_task_yaml.py --task C:\Users\20181\Desktop\Zemax\02_zosapi_python\examples\D30_task_example.yaml --schema C:\Users\20181\Desktop\Zemax\02_zosapi_python\configs\task_schema.json --out-config C:\Users\20181\Desktop\Zemax\02_zosapi_python\configs\config_D31_from_task.yaml
```

标准输出：

```text
【OK】 Task passed validation.
======================================================================
D31 Dry-run Preview
======================================================================
Software: zemax
Task type: parameter_sweep
Model file: Double_Gauss_28_degree_field.zmx
Target: surface 6 / thickness / mm
Sweep range: -1.0 to 1.0, step = 0.2
Estimated run count: 11
Sweep values: [-1.0, -0.8, -0.6, -0.4, -0.2, -0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
Metrics: MTF_30lpmm, MTF_50lpmm, RMS_Spot
Outputs: csv, figures, best_design, report
Output directory: results/D30_double_gauss_sweep
Read-only original model: True
Dry-run first: True
======================================================================
【OK】 Converted workflow config saved to: C:\Users\20181\Desktop\Zemax\02_zosapi_python\configs\config_D31_from_task.yaml
【INFO】 Dry-run only. No Zemax model was opened or modified.
```

错误输出：

```text
无
```

## 6. D32：生成结果总结输入材料

- 返回码：`0`

命令：

```text
C:\Users\20181\Desktop\Zemax\02_zosapi_python\.venv_zosapi38\Scripts\python.exe C:\Users\20181\Desktop\Zemax\02_zosapi_python\scripts\D32_prepare_result_summary.py --config C:\Users\20181\Desktop\Zemax\02_zosapi_python\configs\config_D31_from_task.yaml --out C:\Users\20181\Desktop\Zemax\02_zosapi_python\reports\D32_result_summary_input.md
```

标准输出：

```text
【OK】 D32 result summary input generated.
Results directory: C:\Users\20181\Desktop\Zemax\02_zosapi_python\results\D30_double_gauss_sweep
Output report: C:\Users\20181\Desktop\Zemax\02_zosapi_python\reports\D32_result_summary_input.md
CSV files found: 0
Image files found: 0
JSON files found: 0
Log files found: 0
```

错误输出：

```text
无
```

## 7. Demo 产物

- `examples/D30_task_example.yaml`：存在
- `configs/config_D31_from_task.yaml`：存在
- `reports/D32_result_summary_input.md`：存在
- `reports/D34_agent_demo_report.md`：存在

## 8. 当前局限

当前 demo 只演示 Agent 工作流骨架。由于尚未运行真实 Zemax 参数扫描，结果目录中可能缺少 CSV、图像、best_design 和日志文件，因此 D32 只能生成缺失信息型总结。

## 9. 下一步

下一步可以在 D35 周复盘中整理 README，并在后续 Project-X 中扩展函数库、多参数 YAML、更多分析指标和真实 Zemax 执行能力。
