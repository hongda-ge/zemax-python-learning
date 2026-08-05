# Zemax 自动化实验编排与决策支持系统

> 使用 Python 与真实 ZOS-API，把一次性的手动光学试验转化为安全、可重复、可审计的参数研究与候选决策流程。

## 项目定位

传统 Zemax 优化通常给出某套评价函数下的一个低值解，但工程设计还需要回答更多问题：

- 参数在附近变化时，性能规律是什么？
- 最低点是尖锐最优点，还是存在更容易加工和装调的近优平台？
- Spot、MTF 与 Merit Function 给出不同倾向时，应该怎样解释？
- 不同候选是否使用了相同模型、分析设置和评价规则？
- 在没有明确需求时，怎样避免制造一个缺乏依据的“唯一最优解”？

本项目让 Zemax 负责真实光学计算，让 Python 负责实验编排、安全边界、批量执行、证据校验和决策报告。

```text
工程问题与约束
      ↓
YAML 实验配置与执行授权
      ↓
模型副本、哈希校验与 ZOS-API 连接
      ↓
参数扫描 → 重新对焦 → Spot / FFT MTF / Merit Function
      ↓
稳健区间、Pareto 候选与透明决策规则
      ↓
带适用条件的候选建议，而不是无条件的“最优值”
```

## 项目价值

### 1. 从单点优化转向性能规律

Python 可以在受控范围内系统改变光学参数，记录完整性能剖面。这样不仅能看到哪个采样点较好，还能观察趋势、敏感度和近优区域。

### 2. 从数学最优转向工程候选

单个最低点可能对制造误差非常敏感。本项目更关注性能良好、约束合法且局部变化相对平缓的候选区域，为后续公差、加工和装调分析提供依据。

### 3. 从脚本运行转向可审计实验

每次正式运行都保留配置、模型 SHA256、分析设置、原始 Zemax 文本、结构化 JSON/CSV 和连接关闭状态。异常会停止批量任务，而不是静默生成不可信结果。

### 4. 从隐藏总分转向透明决策

项目不使用缺乏依据的隐藏加权分数。候选先经过明确门槛，再按指定指标排序；推荐结果必须说明适用场景、比较规则和局限性。

### 5. 兼顾光学学习与自动化工程

学习过程按照“计划检查 → 单案例验证 → 小批量执行 → 结果解释”推进。每个阶段都有中文学习记录，适合光学背景、编程经验较少的学习者理解 ZOS-API 的真实工作流程。

## 当前 V1 实验

当前主线使用 Zemax 示例 Cooke Triplet，研究 LDE 面 2 的 `Thickness`：

- 物理含义：第一片与第二片透镜之间的空气间隔；
- 基准值：`6.0075511 mm`；
- 三个视场：`0° / 14° / 20°`；
- 三个波长：`0.480 / 0.550 / 0.650 μm`；
- 补偿动作：Quick Focus 调整像面距离；
- 评价证据：Standard Spot、FFT MTF、Zemax Merit Function；
- 数据来源：真实 OpticStudio Standalone ZOS-API，不接受 mock 结果进入正式结论。

选择空气间隔而不是旧实验中的面 3 玻璃中心厚度，是为了避免凹面负透镜在扰动后出现零厚度或负厚度，并使参数更容易解释为装配间隔或隔圈长度。

## 已完成的研究链路

| 阶段 | 主要问题 | 当前成果 |
|---|---|---|
| 环境与连接 | Python 能否稳定连接真实 OpticStudio？ | 固定 Python 3.8 环境，验证许可证与连接生命周期 |
| 基准定义 | 实验对象、参数、视场、波长和安全边界是什么？ | 冻结 YAML 配置、源模型 SHA256 和只读规则 |
| 单案例扰动 | 写入参数时还会触发哪些 Zemax Solve？ | 记录主动参数与依赖表面变化，验证内存写入和副本保存 |
| Quick Focus | 厚度变化后离焦影响有多大？ | 对每个候选重新对焦并审计像面位移 |
| 粗扫描 | 合法范围内的整体趋势是什么？ | 完成 5 点扫描并发现边界拒绝案例 |
| 局部精细扫描 | 最佳采样点附近是否存在近优平台？ | 完成 9 点、0.1 mm 步长扫描与局部敏感度分析 |
| FFT MTF 交叉验证 | Spot 结论是否代表频域成像性能？ | 提取 30/50 cycles/mm 的 T/S MTF，形成 Pareto 候选 |
| Merit Function 验证 | 候选是否使用同一套 Zemax 综合评价规则？ | 冻结并校验 1602 行 `.MF` 配方，完成三候选只读比较 |
| 需求场景决策 | 没有真实探测器时能否宣布唯一最优？ | 建立三种透明教学场景，明确不产生唯一工程赢家 |

## 当前教学结论

在现有模型和分析设置下，三个候选分别适用于不同目标：

| 场景 | 候选厚度 | 解释 |
|---|---:|---|
| 几何像质优先 | `6.0075511 mm` | Spot 与当前 RMS Spot Merit Function 更优 |
| 均衡成像 | `5.9075511 mm` | Spot/Merit 仅损失约 1%，同时获得更高 MTF |
| 精细结构优先 | `5.8075511 mm` | 当前候选中 MTF30/MTF50 更高 |

这些是教学场景结论，不是产品设计结论。由于尚未指定探测器像元、目标空间频率、加工公差和验收门槛，本项目当前不宣称存在唯一工程最优厚度。

## 安全与数据可信性

项目遵循以下执行原则：

1. 源模型只读，所有操作从独立副本开始；
2. 正式批量执行前先运行 `PLAN ONLY`；
3. 先验证单个基准案例，再批准完整批量；
4. 输入模型、工作副本和配方均使用 SHA256 校验；
5. 主动参数、依赖 Solve、焦移和安全边界全部记录；
6. 意外失败立即停止后续案例；
7. `CalculateMeritFunction()` 与执行优化严格区分；
8. 原始输出保存在本地 `outputs/`，不直接提交到 GitHub；
9. mock、placeholder 或无法追溯的数据不得进入正式光学结论；
10. AI/Agent 不能绕过配置授权和安全检查修改模型。

## 项目结构

```text
02_zosapi_python/
├─ configs/                 # 基准、扫描、评价函数和决策规则
│  └─ merit_functions/      # 冻结的 Zemax .MF 配方
├─ modules/zemax/           # 连接、模型、对焦、分析和 MFE 通用操作
├─ scripts/demos/           # 当前真实实验与教学步骤
├─ scripts/legacy/          # 早期 D16–D20 探索脚本，仅作历史参考
├─ docs/project_plan/       # 项目章程、基准定义和功能边界
├─ docs/learning_notes/     # 分阶段中文学习记录
├─ outputs/                 # 本地运行产物，默认不进入 Git
├─ environment-zosapi38.yml # 可复现 Conda 环境
├─ SETUP.md                 # 环境创建与 VS Code 配置
└─ README.md
```

核心模块职责：

- `connection.py`：Standalone ZOS-API 初始化、许可证检查和安全关闭；
- `model_ops.py`：模型副本、表面读写、保存边界和文件哈希；
- `focus_ops.py`：Quick Focus；
- `analysis_ops.py`：Standard Spot 与 FFT MTF 导出、解析；
- `merit_ops.py`：Merit Function 配方加载、定义指纹和只读计算。

## 环境要求

- Windows 11 64-bit；
- Ansys Zemax OpticStudio 2024 R1.03；
- 有效的 ZOS-API 许可证；
- Python 3.8.20 64-bit；
- Python.NET 2.5.2；
- Conda 项目环境：`.conda_zosapi38`。

创建环境：

```powershell
conda env create --prefix .\.conda_zosapi38 --file environment-zosapi38.yml
conda activate .\.conda_zosapi38
python --version
```

详细说明见 [SETUP.md](SETUP.md)。

## 快速验证

所有命令均在项目根目录执行。

### 1. 检查环境

```powershell
python scripts/validation/D59_check_environment.py
```

### 2. 验证真实 ZOS-API 连接

```powershell
python scripts/demos/D59_zemax_connection_demo.py
```

### 3. 查看当前模型安全操作 Demo

```powershell
python scripts/demos/D60_model_operations_demo.py
```

### 4. 查看需求场景计划

```powershell
python scripts/demos/day11_requirement_scenario_plan.py
```

如果使用 VS Code，请选择项目内的 `.conda_zosapi38\python.exe`，之后可以直接打开脚本并点击右上角运行按钮。

## 推荐阅读顺序

1. [项目章程](docs/project_plan/PROJECT_CHARTER.md)
2. [Cooke 基准实验定义](docs/project_plan/BASELINE_DEFINITION.md)
3. [Day 8：局部稳健性](docs/learning_notes/DAY8_LOCAL_ROBUSTNESS.md)
4. [Day 9：Spot/MTF 交叉验证](docs/learning_notes/DAY9_SPOT_MTF_CROSS_VALIDATION.md)
5. [Day 10：Merit Function 验证](docs/learning_notes/DAY10_MERIT_FUNCTION_VALIDATION.md)
6. [Day 11：需求驱动决策](docs/learning_notes/DAY11_REQUIREMENT_DRIVEN_DECISION.md)
7. [Day 12：决策门槛敏感性分析](docs/learning_notes/DAY12_DECISION_SENSITIVITY.md)

## 当前边界

- 当前只完成一个真实模型、一个外层参数的研究链路；
- 当前补偿动作为 Quick Focus，尚未形成受限变量的完整内层再优化实验；
- 5% 近优平台和 2% 均衡门槛均为公开的项目教学规则，不是加工公差；
- MTF 当前从 Zemax 原始文本中解析，而不是直接读取全部 DataSeries；
- 当前尚未加入真实探测器、成本、材料批次、热环境和装调误差；
- 当前结论只对冻结的模型、配置、视场、波长和分析设置有效；
- 仓库不包含 OpticStudio、许可证或 Ansys 专有程序文件。

## 后续路线

1. 引入探测器像元和目标空间频率，将教学门槛升级为工程验收规则；
2. 加入制造公差与 Monte Carlo，验证候选区域的真实稳健性；
3. 在每个外层参数案例中授权少量内层变量再优化，并审计变量边界；
4. 从单参数扩展到经过筛选的少量关键参数，而不是直接进行无约束高维穷举；
5. 建立统一的任务配置、执行器、报告和恢复机制；
6. 让 AI Agent 生成候选实验计划，但始终由 Schema、安全策略和人工授权控制执行。

## 一句话总结

这个项目的意义不是让 Python 取代 Zemax，而是让 Zemax 的真实光学计算变成一套可以重复、比较、追溯并支持工程决策的实验系统。
