# Project-X 面试演示指南

## 一句话介绍

我没有用 Python 重写 Zemax，而是把真实 ZOS-API 计算组织成一套带模型保护、批量实验、失败停止、审批消费、结果复核和数据血缘的工程流程。

## 建议演示时长

### 3 分钟版本

1. **问题（30 秒）**：手工 Zemax 适合单案例，但多案例容易出现设置漂移、模型误改、失败后重复执行和结果不可追溯。
2. **方案（60 秒）**：Zemax 负责真实 Spot/MTF/Merit Function；Python 负责独立副本、SHA256、串行编排、一次性审批、异常停止和 CP09 复核。
3. **结果（60 秒）**：完成七个真实恢复点，与历史 16 点合并成 23 点；在 `±0.012 mm` 离散定位误差下，四个候选中两个通过、两个失败。
4. **边界（30 秒）**：结果是离散教学证据，不是连续制造公差；统一 `ZemaxBackend` 尚未完成。

### 10 分钟版本

在 3 分钟版本基础上依次展示：

- `modules/zemax/connection.py`：连接生命周期和许可证检查；
- `modules/zemax/model_ops.py`：源模型边界、独立副本和 SHA256；
- `scripts/demos/day76_execute_approved_seven_point_recovery_batch.py`：审批消费、串行执行、失败即停；
- Day 79 结果：23 点证据池和四个命令包络；
- Day 80 复核：程序成功、教学验收和科学边界分层。

## 演示前准备

在仓库根目录使用项目环境：

```powershell
conda activate .\.conda_zosapi38
python --version
```

预期为 Python 3.8.20。若 OpticStudio 不在自动发现目录，可设置：

```powershell
$env:ZEMAX_INSTALL_DIR = "D:\Program Files\Zemax OpticStudio"
```

## 推荐的安全演示命令

### 1. 运行离线测试

```powershell
python -m unittest discover -s tests -v
```

说明：验证安装路径选择，以及“零偏移控制必须全部通过”和“批次验收 FAIL 只记录”两种不同语义。

### 2. 环境体检

```powershell
python scripts/validation/D59_check_environment.py
```

说明：只检查 Python、依赖和 DLL，不启动 OpticStudio，不占用许可证。

### 3. 展示冻结结果

```powershell
python scripts/validation/interview_demo_summary.py
```

预期重点输出：

```text
Real seven-point batch: 7/7 cases
Combined measured evidence: 23 points
Sampled-envelope PASS: command_002, command_003
Sampled-envelope FAIL: command_001, command_004
Day80 CP09: PASS
```

这个入口会先校验四份关键证据的 SHA256，再打印摘要；它不会连接 Zemax或写入输出。

### 4. 可选：真实连接生命周期

仅在许可证和演示环境稳定时运行：

```powershell
python scripts/demos/D59_zemax_connection_demo.py
```

该入口只建立 Standalone 连接、读取版本/许可证状态并安全关闭，不加载模型或运行分析。

## 结果怎么讲

冻结四指标门槛为：

- Spot mean RMS `≤ 11.3 μm`；
- Spot worst RMS `≤ 16.5 μm`；
- MTF30 minimum `≥ 0.16`；
- MTF50 minimum `≥ 0.05`。

在 `±0.012 mm` 的三个精确采样状态下：

| 命令位置 | 结果 | 解释 |
|---:|---|---|
| `0.000 mm` | FAIL | `-0.012 mm` 的 MTF30、MTF50 未通过 |
| `+0.010 mm` | PASS | 三个精确状态全部通过 |
| `+0.020 mm` | PASS | 三个精确状态全部通过 |
| `+0.030 mm` | FAIL | `+0.042 mm` 的 MTF30 未通过 |

正确表述是：`+0.010 mm` 和 `+0.020 mm` 的三个离散实测状态通过。不能说二者之间形成连续合格区间，也不能在没有探测器、制造和装调要求时指定唯一赢家。

## 一个值得讲的故障案例

Day 76 首次尝试复用了零偏移控制的验收函数，使非零端点的教学验收 FAIL 被错误当成程序异常。系统按策略停止后续案例并保留审批消费和模型安全证据。

修复时没有放宽阈值，而是拆分语义：

- `evaluate_balanced_checks()` 返回四项检查，供批次记录 PASS/FAIL；
- `evaluate_balanced()` 保留零偏移控制的严格全通过要求。

随后签发新的单次审批，完整执行 7/7 案例。这个例子能展示失败停止、根因定位、权限不可复用和回归测试，而不只是“脚本最后跑通了”。

## 常见追问

### 为什么不直接手工使用 Zemax？

单案例可以手工完成。项目价值在多案例统一设置、独立副本、失败恢复、数据血缘、公平比较和可重复交付。

### 为什么不用 Python 自己算 Spot 和 MTF？

Zemax 是可信光学内核。Python 只编排调用、保护模型和校验证据，正式结论不接受 mock 或自制近似指标。

### 是否找到了全局最优？

没有。当前结论只适用于冻结模型、视场、波长、分析设置和离散采样点。

### 这是正式制造公差吗？

不是。`±0.012 mm` 是教学定位误差，三点包络不能替代 Zemax 原生 Monte Carlo 公差分析。

### 统一 Backend 完成了吗？

没有。真实能力已经在 `modules/zemax/` 和受控执行脚本中验证，但 `modules/backends/zemax_backend.py` 仍是占位实现。这是下一阶段工程化方向，不属于面试版 V1 已完成能力。

## 不要在演示中运行

- 已消费的一次性 Day 73、Day 76、Day 79 执行入口；
- 七点批次或新的光学扫描；
- 修改源模型的任何脚本；
- MockBackend 结果作为正式光学证据。

面试演示默认使用只读摘要；真实连接只作为可选加分项。
