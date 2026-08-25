# Codex 项目交接文件

更新日期：2026-08-25

项目：Zemax 自动化实验编排与决策支持系统

仓库：`https://github.com/hongda-ge/zemax-python-learning.git`

主分支：`main`

## 1. 给新电脑上 Codex 的第一条指令

在项目根目录打开 Codex 后，可直接发送：

> 请先完整阅读 `docs/project_handoff.md`、`README.md`、`SETUP.md`、`docs/project_plan/PROJECT_CHARTER.md`、`docs/project_plan/BASELINE_DEFINITION.md` 和 `docs/learning_notes/DAY74_CP09_RECOVERY_RETRY_REVIEW.md`。先检查 Git 状态和本机 ZOS-API 环境，不修改模型、不执行批次。向我汇报当前阶段、可信能力、待办事项、风险和建议的下一步。

本文件是跨电脑继续项目的权威交接入口。聊天记录可以作为补充，但不能替代仓库中的代码、配置、非模型证据和安全边界。Zemax 模型不进入 GitHub，必须通过用户控制的私有介质单独迁移。

## 2. 项目目标

项目不重写 Zemax 的光线追迹、内置优化或公差引擎。Zemax 负责真实光学计算，Python 系统负责：

- 配置驱动的实验计划与执行授权；
- 原始模型保护、工作副本和 SHA256 校验；
- 批量调用真实 ZOS-API；
- Standard Spot、FFT MTF、Merit Function 等统一证据采集；
- Quick Focus、候选比较、稳健性分析和透明验收；
- 失败停止、审批消费、CP09 复核和可追溯报告；
- 后续的参数化优化、多起点编排和正式公差候选比较。

一句话定位：让 Zemax 的真实计算成为可重复、可比较、可恢复、可审计的工程实验系统，而不是做一个比 Zemax 更弱的扫描器。

## 3. 当前真实进度

当前本地工作线已经完成到 **Day 80**。仓库已提交的迁移基线仍为：

```text
42a460c 迁移：补齐项目基线、恢复证据与Codex交接文档
```

Day 80 已完成的迁移与恢复链：

```text
Day70 许可证失败 → Day74 恢复审核通过
→ 新电脑环境与 SP0/SP3 零偏移兼容性回归
→ Day75 七点批次审批
→ Day76 七点真实 ZOS-API 执行
→ Day77 CP09 批次复核
→ Day78 Day27 离线重算审批
→ Day79 合并 16+7 点重算
→ Day80 CP09 科学复核通过
```

当前阶段结论：

- 新电脑 Standalone ZOS-API 许可证、连接和安全关闭已验证；
- OpticStudio 24.1 SP0 与历史 SP3 的零偏移 Spot/FFT MTF 汇总指标零差复现；
- 七个缺失恢复点已完成真实测量，所有连接关闭且模型安全检查通过；
- Day27 已合并 16+7=23 个精确实测点，并按 ±0.012 mm 教学定位误差完成离散包络重算；
- `command_002 (+0.010 mm)` 与 `command_003 (+0.020 mm)` 的三个采样状态通过，另两个候选失败；
- Day80 CP09 通过，只获得 Slot 6 释放申请资格；面试版 V1 在此冻结；
- 模型与工作副本未被修改，连接已关闭；
- 所有执行审批已经消费，禁止复用 Day73、Day76 或 Day79 入口；
- Slot 6、新的 ZOS-API 批次和工程变更仍然锁定；
- 面试版 V1 已整理 Day75—80、迁移验证、面试摘要和文档更新，并选择性保留关键 `outputs/` 非模型证据。

## 4. 下一步任务

面试版 V1 不再扩展新的光学实验。下一步进入稳定化与交付收尾：

建议顺序：

1. 审查 Day75—80 与迁移相关代码；
2. 运行离线单元测试、全量语法编译、环境体检和只读面试摘要；
3. 更新 README、SETUP、交接文件和 `INTERVIEW_DEMO.md`；
4. 选择性提交 Day76、Day79、Day80 与迁移回归的关键非模型证据；
5. 创建干净 Git 提交和面试版 V1 标签；
6. 后续若继续工程化，再单独规划统一 ZemaxBackend，不与面试收尾混合。

禁止为了面试演示重新运行已经消费的一次性入口。默认使用只读摘要展示冻结证据。

## 5. 当前主实验基线

### 5.1 原始模型（不提交 GitHub）

```text
models/Cooke 40 degree field.zmx
SHA256: A3F4BAA1433F36C7F363BBB1C7721D972854F2EC842E916EFC17DE2FF9A77585
```

### 5.2 当前聚焦候选模型（不提交 GitHub）

```text
models/baselines/cooke_surface2_6p008_focused.zmx
SHA256: 9B01CC4E0F6C02961E332D635DC18A76F4663D791F346535083339F65BA439FF
```

该模型原先位于本地 `outputs/day8_local_fine_scan/...`。当前工作区已将它复制到稳定路径 `models/baselines/`，Day 23—74 相关后续配置均改为引用该路径。**两个模型都不会上传 GitHub**；迁移时需使用移动硬盘、加密压缩包或其他私有方式，将它们放回上述精确路径，并再次校验 SHA256。

### 5.3 实验口径

- 模型：Zemax 示例 Cooke Triplet；
- 外层参数：LDE 面 2 `Thickness`，物理上为第一片与第二片之间的空气间隔；
- 当前基准值：约 `6.0075511 mm`；
- 视场：`0° / 14° / 20°`；
- 波长：`0.480 / 0.550 / 0.650 μm`；
- 补偿：Quick Focus；
- 指标：Standard Spot、FFT MTF 30/50 cycles/mm、Zemax Merit Function；
- 正式结论只接受真实 OpticStudio Standalone ZOS-API 输出。

## 6. 代码结构与可信边界

### 6.1 当前真实可用能力

真实 ZOS-API 能力主要位于：

```text
modules/zemax/connection.py
modules/zemax/model_ops.py
modules/zemax/focus_ops.py
modules/zemax/analysis_ops.py
modules/zemax/merit_ops.py
scripts/demos/day*.py
```

它们已经支撑真实连接、模型副本、参数操作、Quick Focus、Spot/MTF 导出、Merit Function 计算及多阶段证据复核。

### 6.2 尚未完成的统一工程接口

```text
modules/backends/zemax_backend.py
```

目前仍是 D58 占位实现。通用 `workflow_runner` 的旧路径仍可能使用模拟指标。不得因为存在大量真实 Day 脚本，就宣称统一 ZemaxBackend 已完成。

后续工程化重点是将 `modules/zemax/` 中已验证的真实能力迁移到统一 Backend、Analysis Adapter 和 Experiment Engine，而不是继续无限增加孤立 Demo。

### 6.3 数据真实性规则

- `MockBackend` 只用于纯逻辑测试；
- `simulate_optical_metrics()` 不得进入正式光学报告；
- 正式结果必须携带模型哈希、配置、分析设置、原始输出和 Backend 来源；
- 源模型只读，所有修改从独立工作副本开始；
- 无法追溯的数据不能用于候选推荐。

## 7. 迁移时保留的运行证据

`outputs/` 默认被 Git 忽略，因为绝大多数结果可以重新生成。迁移基线已提交 Day 68—74 恢复链直接依赖的少量非模型证据；面试版 V1 也选择性保留迁移回归、Day76、Day79 和 Day80 的关键 JSON/CSV/原始 Spot/MTF、审批消费标记和审核记录。恢复链中的 `.zmx` 工作副本始终不提交。

这些文件是**迁移检查点证据**，不是以后把全部 `outputs/` 提交 Git 的先例。后续运行仍应默认保存在本地；只有不可替代、被下一审批链直接引用的冻结证据才选择性提交。

## 8. 新电脑环境恢复

### 8.1 软件基线

- Windows 11 64-bit；
- Ansys Zemax OpticStudio 2024 R1.03，或经过回归确认的兼容版本；
- 有效 ZOS-API 许可证；
- Python 3.8.20 64-bit；
- Python.NET 2.5.2；
- Conda。

不要复制旧电脑的 `.conda_zosapi38/`，应重新创建：

```powershell
conda env create --prefix .\.conda_zosapi38 --file environment-zosapi38.yml
conda activate .\.conda_zosapi38
python --version
```

### 8.2 ZOS-API 路径

旧电脑基线曾使用：

```text
L:\Program Files\Zemax2024 R1.03\ZOSAPI_NetHelper.dll
L:\Program Files\Zemax2024 R1.03\ZOSAPI.dll
L:\Program Files\Zemax2024 R1.03\ZOSAPI_Interfaces.dll
```

新电脑安装路径可能不同。应集中修改环境/连接配置，禁止在多个脚本中分别硬编码新路径。

## 9. 新电脑首次验证顺序

在新的电脑或面试环境执行任何可选真实连接演示前，按以下顺序验证：

```powershell
git status
python --version
python scripts/validation/D59_check_environment.py
python scripts/demos/D59_zemax_connection_demo.py
python scripts/demos/D60_model_operations_demo.py --model "models/Cooke 40 degree field.zmx"
```

随后执行只读检查：

1. 校验两个基准模型 SHA256；
2. 确认 OpticStudio 许可证有效；
3. 确认 Standalone 连接能建立并安全关闭；
4. 用新工作副本复现一个零偏移 Spot/MTF 控制；
5. 比较新结果与 Day 73 历史控制；
6. 面试默认运行只读摘要，不重新消费任何历史审批。

新电脑路径、OpticStudio小版本或文本导出格式发生变化时，不得直接放宽容差来“让测试通过”。应先定位差异来源。

## 10. Git 与文件管理规则

### 应提交

- `modules/`、`scripts/` 中可复用源代码；
- `configs/` 中正式配置、Schema 和安全策略；
- `docs/`、`README.md`、`SETUP.md`；
- 冻结 Merit Function 配方；
- 少量不可替代、被后续审批直接引用的检查点证据。

### 默认不提交

- `.conda_zosapi38/`、`.venv*`、`__pycache__/`；
- 普通 `outputs/`、日志、缓存和临时工作副本；
- `artifacts/`、`generated_docs/` 和 Word 渲染中间文件；
- 重复的批量候选模型、可重新生成的图片和旧扫描文本；
- 所有 Zemax `.zmx`、`.zos`、`.ZDA` 模型及工作副本；
- Codex 的 `auth.json`、SQLite/WAL、安装ID、沙箱密钥和缓存；
- 意外产生的嵌套 `02_zosapi_python/` 工作区副本。

## 11. 当前项目边界

- 当前已形成一个真实模型、一个外层参数的完整研究与复核链；
- Day 22—28 的定位误差和验收余量属于离散教学证据，不等同于正式制造 Monte Carlo 公差；
- 当前尚未完成“外层参数固定 + 内层 Zemax 优化”的统一参数化优化引擎；
- 当前尚未把真实能力收敛进统一 ZemaxBackend；
- 尚未加入真实探测器、成本、材料批次、热环境和完整装调误差模型；
- 项目不能宣称找到数学全局最优，也不能把教学阈值包装成产品指标。

## 12. 面试表达主线

> Zemax 是可信的光学计算、优化和公差内核。我的项目不重写这些算法，而是通过 ZOS-API 将模型保护、批量实验、调焦补偿、多指标提取、审批消费、失败恢复和候选复核组织成可追溯流程。当前已经完成真实 Cooke 模型的参数研究与许可证恢复审计链；下一步是把验证过的能力迁入统一 Backend，并扩展到参数化优化和多候选公差比较。

如果被问到“为什么不直接使用 Zemax”，重点回答：单案例可以直接操作 Zemax；项目价值出现在多案例统一设置、重复执行、失败恢复、数据血缘、多个候选的公平比较和自动化交付。

## 13. 交接完成检查

新电脑达到以下条件，才算迁移成功：

- Git 仓库克隆完成且工作区干净；
- 两个基准模型存在且 SHA256 一致；
- Conda 环境重建成功；
- ZOS-API 环境体检通过；
- Standalone 许可证与连接通过；
- 源模型保护测试通过；
- 零偏移 Spot/MTF 回归通过；
- Codex 能准确复述 Day 80 检查点、面试版冻结范围和统一 Backend 尚未完成的边界。
