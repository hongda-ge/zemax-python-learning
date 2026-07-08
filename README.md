# Zemax Python Learning：光学仿真自动化学习与工程实践

> 基于 **Zemax OpticStudio + Python + ZOS-API** 的光学仿真自动化学习项目。  
> 本仓库记录了从 Zemax 手动建模、ZOS-API 脚本控制、参数扫描、结果导出，到 AI Agent / MCP 工具化工作流的完整学习过程。

---

## 1. 项目简介

本项目最初用于记录个人学习 Zemax OpticStudio 与 Python 自动化的过程，后续逐步扩展为一个面向光学仿真自动化的工程实践项目。

项目主线为：

```text
Zemax 手动建模
    ↓
Python + ZOS-API 自动化
    ↓
参数扫描与结果导出
    ↓
配置文件驱动工作流
    ↓
自然语言任务解析
    ↓
AI Agent / MCP 工具化封装
    ↓
后续扩展：专利镜头复现、自动化分析平台、多软件协同
```

本项目希望解决的问题不是“只学会某个软件按钮怎么点”，而是逐步建立一个可复用的光学仿真自动化流程：

- 能够手动理解 Zemax 光学系统结构；
- 能够用 Python 控制 Zemax；
- 能够自动读取、修改和扫描镜头参数；
- 能够自动导出 MTF、Spot、Ray Fan 等分析结果；
- 能够通过 YAML / JSON 描述仿真任务；
- 能够初步将自然语言需求转化为可执行任务；
- 最终为 AI Agent 辅助光学设计打基础。

---

## 2. 项目定位

本仓库不是一个成熟商业软件，而是一个持续迭代的学习型工程项目。

目前定位为：

> **面向光学工程实习与科研自动化实践的 Zemax + Python + AI Agent 学习项目。**

适合展示以下能力：

- Zemax OpticStudio 顺序模式基础建模能力；
- 光学系统成像质量评价能力；
- Python 自动化脚本开发能力；
- ZOS-API 基础调用能力；
- 参数扫描与结果可视化能力；
- 项目工程结构整理能力；
- AI Agent / MCP 工具封装的初步理解与实现能力。

---

## 3. 当前完成进度

目前已经完成到 **D42：MCP / 工具化基础阶段**。

整体进度如下：

| 阶段 | 时间 | 内容 | 当前状态 |
|---|---|---|---|
| 第 1 周 | D1-D7 | Zemax 手动建模与性能评价 | 已完成 |
| 第 2 周 | D8-D14 | Python + ZOS-API 入门 | 已完成 |
| 第 3 周 | D15-D21 | 参数扫描与自动化优化基础 | 已完成 |
| 第 4 周 | D22-D28 | 项目结构整理与工作流重构 | 已完成 / 部分重构 |
| 第 5 周 | D29-D35 | 自然语言任务、YAML/JSON、Agent Demo | 已完成 |
| 第 6 周 | D36-D42 | 工具注册、输入校验、MCP 雏形 | 已完成 |
| Project-X | D57 起 | 项目审计、架构重构、多参数工程化 | 规划中 |

---

## 4. 技术栈

### 4.1 光学仿真

- Zemax OpticStudio
- Sequential Mode
- Lens Data Editor
- Spot Diagram
- FFT MTF
- Ray Fan
- OPD Fan
- Field Curvature / Distortion
- Merit Function
- Local Optimization

### 4.2 自动化与数据处理

- Python 3.8
- ZOS-API
- pythonnet
- NumPy
- Matplotlib
- CSV 数据处理
- YAML / JSON 配置文件
- JSON Schema 输入校验

### 4.3 工程与版本管理

- VS Code
- Git / GitHub
- Markdown 文档
- requirements.txt
- .gitignore
- 项目日志 weekly_log

### 4.4 AI Agent / MCP

- 自然语言任务描述
- YAML 任务配置
- JSON 参数传递
- 工具注册表
- 工具调用接口
- 输入校验
- MCP 工具化雏形

---

## 5. 项目结构

当前推荐结构如下：

```text
zemax-python-learning/
│
├── README.md
├── SETUP.md
├── requirements.txt
├── .gitignore
│
├── 01_zemax_manual/
│   ├── figures/
│   ├── README.md
│   └── weekly_log_01.md
│
├── 02_zosapi_python/
│   ├── examples/
│   ├── scripts/
│   ├── models/
│   ├── outputs/
│   ├── logs/
│   ├── .vscode/
│   ├── SETUP.md
│   └── requirements.txt
│
├── configs/
│   ├── config_D15_cooke_thickness.yaml
│   ├── task_examples/
│   └── schema/
│
├── scripts/
│   ├── D31_run_from_task_yaml.py
│   ├── D32_generate_result_summary_input.py
│   ├── D34_agent_demo.py
│   ├── D38_tool_registry_demo.py
│   ├── D39_input_validation_demo.py
│   ├── D40_mcp_tool_demo.py
│   ├── D41_...
│   └── D42_...
│
├── results/
│   ├── sweep_results/
│   ├── mtf_exports/
│   ├── agent_reports/
│   └── validation_outputs/
│
├── figures/
│   ├── D2_layout/
│   ├── D3_analysis/
│   ├── D5_cooke_mtf/
│   ├── week02_zosapi/
│   ├── week03_sweep/
│   └── agent_workflow/
│
├── logs/
│   ├── weekly_log_01.md
│   ├── weekly_log_02.md
│   ├── weekly_log_03.md
│   ├── weekly_log_04.md
│   ├── weekly_log_05.md
│   └── weekly_log_06.md
│
├── docs/
│   ├── Zemax_terms.md
│   ├── ZOS_API_notes.md
│   ├── Agent_workflow_notes.md
│   └── Project_X_roadmap.md
│
└── reports/
    ├── D34_agent_demo_report.md
    └── project_summary.md
```

> 注：不同阶段文件夹可能会逐步整理，当前仓库仍在重构中。

---

## 6. 已完成内容

## 6.1 第 1 周：Zemax 手动建模与性能评价

第一周目标是熟悉 Zemax OpticStudio 的基本界面、顺序模式结构和常用成像质量评价方法。

### 学习内容

- 熟悉 Lens Data Editor；
- 理解 Radius、Thickness、Glass、Semi-Diameter；
- 理解 Stop、Image Surface、Field、Wavelength、Aperture；
- 打开 Double Gauss 与 Cooke Triplet 官方示例；
- 导出 Layout、Spot Diagram、FFT MTF、Ray Fan；
- 手动修改镜头参数并观察成像质量变化；
- 学习 Merit Function、Operand、Variable、Constraint；
- 完成局部优化并对比优化前后 MTF。

### 关键概念

| 概念 | 含义 |
|---|---|
| LDE | 镜头数据编辑器，用于定义每个表面参数 |
| Radius | 曲率半径 |
| Thickness | 相邻表面间距 |
| Glass | 玻璃材料 |
| Stop | 光阑面 |
| Field | 视场 |
| Wavelength | 波长 |
| Spot Diagram | 点列图，观察光线聚焦情况 |
| FFT MTF | 调制传递函数，评价细节传递能力 |
| Ray Fan | 光线像差图，用于分析像差来源 |
| Merit Function | 优化目标函数 |

### 结果图示例

#### Double Gauss 原始光路图

![Double Gauss 原始光路图](figures/D2_layout/D2_DoubleGauss_layout_original.png)

#### Double Gauss 修改后光路图

![Double Gauss 修改后光路图](figures/D2_layout/D2_DoubleGauss_layout_modified_radius_or_thickness.png)

#### Spot Diagram

![Spot Matrix](figures/D3_analysis/D3_DoubleGauss_spotmatrix_allfield_allwave.png)

#### FFT MTF

![FFT MTF](figures/D3_analysis/D3_DoubleGauss_FFTMTF_allfield_allwave_100lpmm.png)

#### Ray Fan

![Ray Fan](figures/D3_analysis/D3_DoubleGauss_rayfan_field0_primarywave.png)

#### Cooke Triplet MTF 对比

![Cooke 原始 MTF](figures/D5_cooke_mtf/D5_01_original_MTF.png)

![Cooke 修改后 MTF](figures/D5_cooke_mtf/D5_02_modified_MTF.png)

![Cooke 优化后 MTF](figures/D5_cooke_mtf/D5_03_after_optimize_MTF.png)

### 阶段总结

第一周主要解决“看得懂 Zemax”的问题。通过 Double Gauss 和 Cooke Triplet 示例，完成了从镜头结构读取、参数修改、分析图导出到优化前后对比的基础闭环。

---

## 6.2 第 2 周：Python + ZOS-API 入门

第二周目标是让 Python 能够连接 Zemax，并完成最基础的自动化操作。

### 环境配置

- Python 3.8.10
- VS Code
- pythonnet
- NumPy
- Matplotlib
- Zemax OpticStudio
- ZOS-API Sample Code

### 完成内容

- 建立 Python 3.8 虚拟环境；
- 解决 PowerShell 执行策略问题；
- 解决 Clash 系统代理导致 pip 安装失败问题；
- 安装并验证 numpy、matplotlib、pythonnet；
- 运行 ZOS-API 官方示例；
- 理解 Interactive Extension 与 Standalone Application 的区别；
- 编写 debug_zosapi_connection.py 连接测试脚本；
- 完成 Python 读取 Zemax 系统信息的准备工作。

### 关键经验

- ZOS-API 依赖 pythonnet 连接 .NET 接口；
- Zemax 19.x 环境下 Python 3.8 + pythonnet 2.5.2 更稳定；
- 虚拟环境需要固定到 VS Code 项目；
- pip 安装库时应注意系统代理影响；
- `.venv_zosapi38` 不应上传 GitHub，应通过 `requirements.txt` 复现环境。

### 阶段总结

第二周主要解决“Python 能不能控制 Zemax”的问题。完成后，项目从纯手动仿真进入了 API 自动化阶段。

---

## 6.3 第 3 周：参数扫描与自动化优化基础

第三周目标是让 Python 不只是连接 Zemax，而是能够批量修改参数、导出结果并进行可视化。

### 完成内容

- 编写表面参数读取脚本；
- 编写 Thickness / Radius 修改函数；
- 使用 YAML 文件定义参数扫描任务；
- 批量修改指定 Surface 的 Thickness；
- 自动导出 MTF 数据；
- 保存 CSV 结果；
- 使用 Matplotlib 绘制参数扫描曲线；
- 根据 MTF 结果筛选较优参数。

### 典型流程

```text
读取 YAML 配置
    ↓
打开 Zemax 模型
    ↓
读取指定 Surface 参数
    ↓
按扫描范围修改 Thickness / Radius
    ↓
运行 MTF 分析
    ↓
导出 CSV
    ↓
绘制曲线
    ↓
保存结果
```

### 项目意义

这一阶段是本项目从“调用 API”迈向“工程化自动化”的关键一步。  
后续无论是镜头优化、专利复现，还是 AI Agent 控制 Zemax，都需要以参数读取、参数修改和结果导出为基础。

---

## 6.4 第 4 周：项目结构整理与工作流重构

第四周主要围绕项目结构、脚本组织和工作流清晰化展开。

### 完成内容

- 整理项目文件夹结构；
- 区分 examples、scripts、configs、results、logs；
- 初步建立主程序入口；
- 将单一脚本整理为可复用函数；
- 理解 workflow、dry-run、config-driven simulation 等概念；
- 为后续 AI Agent 工作流做准备。

### 阶段定位

这一阶段不一定直接产生非常炫的结果图，但它对后续项目持续开发非常重要。  
没有良好的项目结构，后续 D29-D42 的 Agent、Schema、Tool Registry 和 MCP 都会变得混乱。

---

## 6.5 第 5 周：自然语言任务、YAML/JSON 与 Agent Demo

第五周目标是将自然语言任务逐步转化为机器可执行配置。

### 完成内容

- 设计自然语言任务模板；
- 设计 YAML 任务文件；
- 将 YAML 转换为 Python workflow config；
- 生成结果总结输入；
- 编写 Agent Demo；
- 实现一个从任务读取、配置生成到报告输出的最小工作流。

### 典型文件

```text
configs/
├── task_example.yaml
├── config_generated.yaml
└── summary_input.json

scripts/
├── D31_run_from_task_yaml.py
├── D32_generate_result_summary_input.py
└── D34_agent_demo.py

results/
└── D34_agent_demo_report.md
```

### Agent Demo 流程

```text
自然语言任务
    ↓
YAML 任务文件
    ↓
Schema 校验
    ↓
安全策略检查
    ↓
生成 workflow config
    ↓
生成 summary input
    ↓
输出 demo report
```

### 阶段总结

第五周完成了 AI Agent 的低配版本雏形。  
虽然此时还不能完全实现自然语言自动设计镜头，但已经具备了将自然语言需求转为结构化任务的基础。

---

## 6.6 第 6 周：工具注册、输入校验与 MCP 雏形

第六周目标是将已有功能封装为“工具”，并为 MCP 工作流打基础。

### 完成内容

- 设计工具说明文档；
- 定义工具输入参数；
- 编写工具注册表；
- 实现 list_tools；
- 实现 get_tool_spec；
- 实现 call_tool；
- 增加 JSON Schema 输入校验；
- 模拟 run_analysis、modify_surface、export_result 等工具调用；
- 初步理解 MCP 中“工具暴露”和“标准化调用”的意义。

### 工具化思路

```text
普通 Python 函数
    ↓
工具规范描述
    ↓
工具注册表
    ↓
统一调用入口
    ↓
输入校验
    ↓
Agent / MCP 调用
```

### 阶段总结

第六周的核心意义不是“让 AI 立刻完成光学设计”，而是为后续 AI Agent 控制 Zemax 建立可扩展工具接口。  
MCP 在本项目中更像是一个标准接口层，用来让不同工具被统一描述、统一调用和统一校验。

---

## 7. 核心项目能力

当前项目已经具备以下能力：

### 7.1 Zemax 手动分析能力

- 打开并分析官方示例镜头；
- 读取 LDE 中的基础参数；
- 理解系统孔径、视场、波长；
- 导出 Spot、MTF、Ray Fan；
- 对比优化前后系统性能。

### 7.2 ZOS-API 自动化能力

- 使用 Python 连接 Zemax；
- 读取镜头表面参数；
- 修改指定 Surface 的 Radius / Thickness；
- 运行基础分析；
- 导出分析结果；
- 保存输出文件。

### 7.3 参数扫描能力

- 使用配置文件定义扫描任务；
- 批量修改参数；
- 自动保存 CSV；
- 绘制 MTF 变化曲线；
- 根据结果进行初步筛选。

### 7.4 Agent 工作流能力

- 将自然语言任务拆分为结构化配置；
- 使用 YAML / JSON 表达仿真任务；
- 通过 Schema 进行输入校验；
- 通过工具注册表统一管理功能；
- 初步实现 Agent Demo 和 MCP 工具调用雏形。

---

## 8. 环境配置

### 8.1 推荐环境

| 项目 | 推荐版本 |
|---|---|
| OS | Windows 10 / Windows 11 |
| Python | 3.8.10 |
| Zemax OpticStudio | 19.x 或更高 |
| pythonnet | 2.5.2 |
| numpy | 1.24.4 |
| matplotlib | 3.7.5 |
| IDE | VS Code |

### 8.2 创建虚拟环境

```powershell
py -3.8 -m venv .venv_zosapi38
```

### 8.3 激活虚拟环境

PowerShell：

```powershell
.\.venv_zosapi38\Scripts\Activate.ps1
```

如果 PowerShell 禁止脚本运行，可临时执行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

CMD：

```cmd
.venv_zosapi38\Scripts\activate.bat
```

### 8.4 安装依赖

```powershell
pip install -r requirements.txt
```

### 8.5 验证环境

```powershell
python --version
python -c "import numpy, matplotlib, clr; print('environment ok')"
```

### 8.6 常见问题

#### 问题 1：Python 版本不对

如果终端显示 Python 3.12，而不是 Python 3.8，需要检查 VS Code 解释器是否选择了：

```text
.venv_zosapi38\Scripts\python.exe
```

#### 问题 2：PowerShell 无法激活虚拟环境

执行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

然后重新激活。

#### 问题 3：pip 安装库失败

如果开启 Clash / VPN，可能导致 pip 代理异常。  
可先关闭系统代理，再安装依赖。

#### 问题 4：pythonnet 版本不兼容

Zemax 19.x 建议使用：

```text
pythonnet==2.5.2
```

---

## 9. 运行方式

### 9.1 运行连接测试

```powershell
python examples/debug_zosapi_connection.py
```

### 9.2 运行官方 Standalone 示例

```powershell
python examples/PythonStandalone_01_new_file_and_quickfocus.py
```

### 9.3 运行 Agent Demo

```powershell
python scripts/D34_agent_demo.py
```

### 9.4 运行工具注册 Demo

```powershell
python scripts/D38_tool_registry_demo.py
```

---

## 10. 结果与展示

### 10.1 手动分析结果

- Layout 图；
- Spot Diagram；
- FFT MTF；
- Ray Fan；
- Cooke Triplet 优化前后 MTF 对比。

### 10.2 自动化结果

- LDE 参数读取结果；
- 参数扫描 CSV；
- MTF 曲线；
- 自动生成结果报告。

### 10.3 Agent / MCP 结果

- YAML 任务文件；
- JSON 配置文件；
- 工具说明文档；
- 工具调用结果；
- 输入校验报告；
- Agent Demo 报告。

---

## 11. Project-X：后续扩展计划

当前 D1-D42 主要完成了基础学习、自动化脚本和 MCP 工具化雏形。  
后续将进入 Project-X 阶段，目标是把项目从“学习脚本”升级为“可复用的光学自动化工作流”。

### 11.1 Project-X 总目标

> 构建一个以 Zemax 为核心、Python 为控制层、AI Agent 为交互层的光学仿真自动化平台。

核心方向：

- 多参数扫描；
- 多分析类型导出；
- 自动报告生成；
- 任务配置模板；
- 工具库扩展；
- 人机交互界面；
- 专利镜头复现；
- AI Agent / MCP 工程化。

---

## 12. 后续重点项目：DJI 七片式镜头专利复现

后续计划将公开专利镜头作为完整工程案例。

### 项目设想

> 基于公开专利参数，在 Zemax 中复现 DJI 七片式光学系统，并使用 Python + ZOS-API 完成自动化分析。

### 计划内容

- 根据公开专利参数建立 Zemax 模型；
- 输入曲率半径、厚度、玻璃材料等数据；
- 完成光路结构复现；
- 输出 Spot Diagram；
- 输出 FFT MTF；
- 输出 Ray Fan；
- 输出 Field Curvature / Distortion；
- 对比不同实施例的像差表现；
- 分析镜头结构设计思路；
- 使用 Python 自动导出分析图和 CSV 数据；
- 最终生成一份完整的复现与分析报告。

### 项目定位

该项目不只是“输入专利参数”，而是作为自动化工具链的实际验证案例。

目标是形成：

```text
Patent Lens Analyzer
    ↓
导入专利镜头模型
    ↓
自动输出光学分析结果
    ↓
自动生成对比图
    ↓
自动生成分析报告
```

---

## 13. 未来 Roadmap

### 短期目标

- 完成 D1-D42 文件上传；
- 整理 README、SETUP、requirements、weekly_log；
- 完善 D29-D42 的代码注释；
- 补充 Agent Demo 运行截图；
- 补充工具注册表文档；
- 整理 GitHub v2.0 版本。

### 中期目标

- 完成多参数扫描；
- 扩展 run_analysis 工具；
- 支持 Spot / MTF / Ray Fan / OPD 自动导出；
- 增加结果报告自动生成；
- 完成一个可交互命令行工具；
- 完成 DJI 七片式镜头专利复现。

### 长期目标

- 构建 Patent Lens Analyzer；
- 加入更多公开专利镜头案例；
- 支持自然语言任务输入；
- 将 AI Agent 与 MCP 工具链整合；
- 后续再扩展 COMSOL、FDTD、AutoCAD 等多软件协同。


## 14. 当前项目状态

当前项目仍处于学习与重构阶段，主要目标是逐步形成一套完整、清晰、可复现的光学自动化工作流。

已完成：

- Zemax 手动基础；
- ZOS-API 环境搭建；
- Python 连接 Zemax；
- 参数读取与修改；
- 基础参数扫描；
- YAML / JSON 配置；
- Agent Demo；
- 工具注册表；
- 输入校验；
- MCP 工具化雏形。

进行中：

- D29-D42 文件整理；
- GitHub 仓库结构优化；
- README v2.0；
- Project-X 任务规划。

后续：

- 多参数工程化扫描；
- 自动分析报告；
- 专利镜头复现；
- AI Agent / MCP 深度整合。

---

## 15. 注意事项

本项目中部分 Zemax 示例文件、模型文件和截图来自学习过程，仅用于个人学习和工程实践展示。

上传 GitHub 前请注意：

- 不上传 Zemax 授权信息；
- 不上传个人隐私路径截图；
- 不上传大型虚拟环境文件；
- 不上传不必要的中间缓存；
- 不上传敏感实验数据；
- `.venv_zosapi38/` 应加入 `.gitignore`；
- `__pycache__/` 应加入 `.gitignore`；
- 大型结果文件应按需上传。

---

## 16. 致谢

本项目基于个人科研与求职目标展开，主要围绕光学工程、Zemax 自动化、Python 编程与 AI Agent 工具化能力进行系统训练。

感谢 Zemax OpticStudio、Python、GitHub、VS Code 等工具为光学仿真自动化学习提供的支持。

---

## 17. License

本仓库主要用于个人学习、作品集展示与非商业交流。

如后续公开更多代码，可考虑加入 MIT License 或其他开源许可证。

---

## 18. 一句话总结

> 本项目记录了从 Zemax 手动光学分析，到 Python + ZOS-API 自动化，再到 AI Agent / MCP 工具化工作流的完整学习过程。目标不是简单学习软件，而是逐步构建一个可复用、可扩展、可展示的光学仿真自动化平台。
