# 真实 / Mock 能力矩阵

## 判断规则

- REAL：实际调用 OpticStudio 和 ZOS-API，结果可追溯到真实模型。
- MOCK：人为生成结果，只用于测试软件流程。
- PLACEHOLDER：已经定义接口，但尚未实现真实功能。
- LEGACY REAL：历史脚本能够真实运行，但尚未接入统一架构。

| 能力 | 当前实现 | 数据性质 | 当前用途 | 正式报告能否使用 |
|---|---|---|---|---|
| OpticStudio 连接 | `modules/zemax/connection.py` | REAL | D59 连接和释放 | 可以，但只证明连接 |
| 模型复制与参数读写 | `modules/zemax/model_ops.py` | REAL | D60 模型操作 | 可以，但只证明模型操作 |
| 主工作流指标 | `modules/workflow_runner.py` | MOCK | 测试 CSV、图表和报告流程 | 不可以 |
| MockBackend | `modules/backends/mock_backend.py` | MOCK | 无 Zemax 环境下测试流程 | 不可以 |
| ZemaxBackend | `modules/backends/zemax_backend.py` | PLACEHOLDER | 等待接入真实能力 | 不可以 |
| 历史厚度扫描 | `scripts/legacy/D16_sweep_thickness.py` | LEGACY REAL | 真实厚度扫描演示 | 核对设置后可以 |
| 历史 MTF/Spot 导出 | `scripts/legacy/zemax_runner.py` | LEGACY REAL | 真实分析导出 | 核对设置后可以 |
| Tool Registry 分析工具 | `modules/tool_registry.py` | MOCK | D38 Agent 工具演示 | 不可以 |

## 当前结论

项目已经具备真实连接和真实模型操作能力，但这些能力尚未接入统一
ZemaxBackend。当前 `main.py` 仍调用模拟指标，因此不能作为正式光学实验入口。

## 正式数据门禁

正式实验结果必须满足：

1. `backend` 明确等于 `zemax`；
2. `data_source` 明确等于 `real_zemax`；
3. 保存源模型和工作副本哈希；
4. 保存分析类型及视场、波长、频率和采样设置；
5. Mock、Placeholder 和未核实的历史结果不得进入正式结论。