# Project-X D57 项目审计报告

## 总审计结论

当前项目已经完成了从 ZOS-API 学习脚本、参数扫描 Demo、YAML 任务解析、Agent Demo、Tool Registry 到输入校验和安全检查的基本原型。

当前真实可用的部分包括：

- 配置读取
- YAML / JSON Schema 校验
- Safety Policy 检查
- Tool Registry 框架
- Tool Input Validator
- Output Manager
- Workflow 执行框架
- CSV / 图像 / 报告输出流程

当前主要 Mock 部分包括：

- workflow_runner.py 中的 simulate_optical_metrics()
- tool_registry.py 中的 open_model()
- tool_registry.py 中的 set_parameter()
- tool_registry.py 中的 run_analysis()
- tool_registry.py 中的 run_sweep()
- analyze_results()
- generate_report()
- zemax_runner.py 目前仍为空 Backend 占位

当前最大缺口：

Agent / Tool / Workflow 与真实 ZemaxBackend 之间还没有稳定接线层。

D58 起的核心任务：

不是继续增加新 Demo，而是建立 Backend 抽象层，将 Mock 执行逐步替换为真实 ZemaxBackend。


## 文件处理计划

| 文件 | 当前定位 | D57结论 | D58处理 |
|---|---|---|---|
| main.py | Workflow Demo入口 | 保留思想 | 迁移为 cli.py |
| D31_run_from_task_yaml.py | Task解析器 | 保留核心逻辑 | 拆到 loader / validator |
| D34_agent_demo.py | Agent流程Demo | 保留流程思想 | 后续接 Tool Registry |
| D38_tool_registry_demo.py | Tool测试入口 | 保留为演示脚本 | 不作为主入口 |
| workflow_runner.py | Workflow执行原型 | 保留循环框架 | 接 Backend |
| zemax_runner.py | Zemax占位 | 需要重写 | 改为 ZemaxBackend |
| tool_registry.py | Tool核心 | 保留注册思想 | 拆成 tools/registry.py |
| input_validator.py | Tool输入校验 | 保留 | 升级为 tool_validator.py |
| task_safety.py | 任务安全检查 | 保留 | 升级支持 variables |
| output_manager.py | 输出管理 | 保留 | 升级为 artifact_manager |

当前架构：

Natural Language Request
        |
        v
D34 Agent Demo
        |
        v
D31 Task Parser
        |
        v
Tool Registry
        |
        v
Input Validator / Task Safety
        |
        v
Workflow Runner
        |
        v
Mock Results / Simulated Metrics
        |
        v
Output Manager / Report


目标架构：

CLI
 |
 v
Task Loader
 |
 v
Schema Validator
 |
 v
Safety Validator
 |
 v
Scheduler
 |
 v
Workflow Runner
 |
 v
Backend Interface
 |
 +--> MockBackend
 |
 +--> ZemaxBackend
          |
          v
        ZOS-API
          |
          v
Artifacts / Reports

## 审计目标文件：
第一轮（核心链路）
main.py 
D31_run_from_task_yaml.py 
D34_agent_demo.py
D38_tool_registry_demo.py
第二轮（后台）
modules/workflow_runner.py
modules/zemax_runner.py
modules/tool_registry.py
第三轮
validator
summary
output


# 详细审计结果

## main.py


### 类型

Workflow Demo Entry


### 当前功能

- 读取 workflow 配置文件
- 解析扫描参数
- 创建运行输出目录
- 初始化日志系统
- 备份配置文件
- 调用 workflow_runner 执行流程
- 生成 Markdown 运行报告
- 输出本次运行结果路径


### 是否调用 Zemax

否


main.py 本身不直接调用 ZOS-API。

当前调用链：

main.py

↓

workflow_runner.py

↓

zemax_runner.py

↓

ZOS-API


因此 main.py 主要负责流程调度，不负责 Zemax 操作。


### 是否真实Workflow

部分


Workflow流程真实存在：

- 配置加载
- 参数生成
- 输出管理
- 日志记录
- 报告生成


但是：

当前核心执行函数：

run_demo_workflow()

仍属于 Demo 阶段。

真实 Zemax 自动化流程仍需要继续审计：

workflow_runner.py

zemax_runner.py


### Mock位置

1.

run_demo_workflow()


当前名称仍带有 demo 属性，
需要确认内部是否真正连接 Zemax。


2.

workflow_runner.py 内部可能存在模拟结果输出。


3.

report_generator.py 可能基于模拟结果生成报告。


### 优点

- 形成完整端到端 workflow 框架
- 已实现输入 → 执行 → 输出 → 报告闭环
- 模块职责初步分离
- 具备日志、结果管理、配置备份等工程化思想
- 为后续 Agent Workflow 提供基础


### 问题

1.

项目存在多个入口文件：

main.py

D31_run_from_task_yaml.py

D34_agent_demo.py

D38_tool_registry_demo.py


尚未形成唯一 CLI 入口。


2.

main.py 职责偏重

同时负责：

- 参数解析
- 文件管理
- 日志管理
- Workflow调用
- 报告生成


未来需要进一步拆分。


3.

Workflow名称仍保留 Demo 属性

当前：

run_demo_workflow()


未来需要升级为：

run_workflow()

或：

execute_plan()


4.

缺少 Backend 抽象层


当前结构：

main.py

↓

workflow_runner.py

↓

zemax_runner.py


未来需要：

main.py

↓

workflow

↓

backend interface

↓

ZemaxBackend / MockBackend


5.

与具体模块耦合较强

未来需要通过接口调用，
减少 Controller 对具体实现的依赖。


### D57处理

保留:

- Workflow整体流程思想
- 配置加载机制
- 输出管理机制
- 日志管理机制
- 报告生成机制


重构:

- main.py职责拆分
- Demo流程升级为正式Workflow
- 统一项目入口


升级:

main.py

↓

cli.py


Workflow:

↓

Workflow Engine


Zemax执行:

↓

Backend

↓

ZemaxBackend / MockBackend



## D31_run_from_task_yaml.py


### 类型
Task Parser / Validator


### 当前能力

- YAML任务读取
- JSON Schema校验
- 参数范围检查
- Dry-run预览
- Legacy workflow config生成


### 是否真实调用 Zemax

否


### 是否Mock

部分

Mock位置:

try_execute_workflow()

当前只打印提示，没有执行workflow。


### 当前问题

1. 任务模型只支持单变量target
2. 直接生成legacy config，耦合旧workflow
3. 缺少Scheduler
4. 缺少Backend接口


### D57处理

保留:

- loader思想
- validator思想
- safety check


重构:

workflow.loader

workflow.validator

workflow.scheduler


删除:

legacy config依赖



## D34_agent_demo.py


### 类型

Agent Workflow Demo


### 当前流程

Natural Language Request
+
YAML Task

↓

Schema Validation

↓

Safety Validation

↓

D31 Config Generation

↓

D32 Summary Preparation

↓

Report


### 是否真实调用 Zemax

否


### 是否真实Agent

部分

原因：

当前YAML任务已经提前生成，
不存在LLM任务解析过程。


### Mock位置

1.
自然语言→YAML

2.
Agent决策过程

3.
Zemax执行


### 优点

- 完成Agent工作流骨架
- 验证模块连接关系
- 有完整report输出


### 缺陷

- subprocess调用脚本
- 缺少统一Backend
- 缺少真实任务生成
- 未连接Zemax


### D57处理

保留：

workflow思想

重构：

subprocess链路

升级：

Task Loader + Validator + Scheduler + Backend


## D38_tool_registry_demo.py



### 类型

Tool Registry Demo


### 当前功能

- 展示工具列表
- 查询工具描述
- 调用注册工具
- 测试未知工具异常


### 是否调用 Zemax

否


### 是否真实Tool

部分

Registry真实存在，
但是具体执行仍为Mock。


### Mock位置

1.
run_sweep(dry_run)

2.
run_analysis


### 优点

- 引入Tool Registry思想
- 接近MCP工具发现机制
- 工具接口开始统一


### 问题

1.
Demo直接依赖modules

2.
缺少Tool输入Schema

3.
缺少Backend抽象

4.
Tool执行和Zemax耦合不足


### D57处理

保留:

tool registry思想

重构:

tool interface

升级:

Tool -> Backend -> Zemax


## modules/workflow_runner.py


### 类型

Workflow Execution Demo


### 当前功能

- 执行 D27 端到端 dry-run workflow
- 遍历扫描参数列表
- 模拟每组参数对应的光学指标
- 生成扫描结果 CSV
- 生成任务状态 CSV
- 绘制 MTF_50 趋势图
- 根据 score 寻找最佳参数


当前流程：

main.py

↓

workflow_runner.py

↓

simulate_optical_metrics()

↓

CSV / Figure / Report


### 是否调用 Zemax

否


当前代码没有调用：

- ZOSAPI
- TheApplication
- TheSystem
- OpticStudio


实际执行的数据来源：

python
simulate_optical_metrics()



## modules/zemax_runner.py


### 类型

Zemax Runner Placeholder


### 当前功能

- 测试模块是否可以正常导入
- 获取项目根目录
- 显示项目常用路径
- 检查项目目录结构是否正确


当前主要功能：

```python
get_project_root()

show_project_paths()

用于：

configs路径检查
models路径检查
results路径检查
figures路径检查
logs路径检查
```
### 是否调用 Zemax

否

当前文件不存在：

ZOSAPI
TheApplication
TheSystem
OpticStudio Application连接
Zemax模型加载
LDE访问
Analysis调用

因此：

该文件当前没有任何 Zemax 自动化能力。

### 是否真实Zemax Backend

否



## modules/tool_registry.py


### 类型

Tool Registry Core


### 当前功能

- 注册所有可用工具
- 提供工具列表查询
- 提供工具详细描述查询
- 根据工具名称调用对应 Handler
- 执行工具输入参数验证
- 返回统一格式 JSON 结果


当前核心接口：

```python
list_tools()

get_tool_spec(tool_name)

call_tool(tool_name, args)

当前工具包括：

load_task
validate_task
check_safety
open_model
set_parameter
run_analysis
run_sweep
analyze_results
prepare_summary_input
generate_report
```
### 是否调用 Zemax

否

当前文件没有调用：

ZOSAPI
TheApplication
TheSystem
OpticStudio

所有 Zemax相关操作均为模拟。


## modules/input_validator.py



### 类型

Tool Input Validation Module


### 当前功能

- 加载 Tool 输入 JSON Schema
- 校验 Tool 输入参数类型
- 校验必需字段
- 校验枚举范围
- 校验输入格式
- 检查路径安全
- 在 Tool 执行前拒绝非法输入


当前核心接口：

```python
validate_tool_input(tool_name, args)

执行流程：

Tool Call

↓

Input Validator

↓

JSON Schema Validation

↓

Path Safety Check

↓

Tool Handler
```

### 是否调用 Zemax

否

当前模块不涉及：

ZOSAPI
TheApplication
TheSystem
OpticStudio

它只负责：

### Tool 参数检查。

因此属于：

Tool Middleware Layer

而不是：

Zemax Execution Layer

是否真实Validator:

是

与前面的 Mock Tool 不同，

该模块是真实工作的。

真实功能包括：

JSON Schema读取
Draft7Validator校验
类型检查
字段检查
路径安全检查



## modules/task_safety.py


### 类型

Task Safety Policy Validator


### 当前功能

- 安全读取 YAML 文件
- 估算参数扫描取值列表
- 检查模型文件扩展名
- 检查模型路径是否使用绝对路径
- 检查模型路径是否包含 `..`
- 检查输出目录是否位于允许目录内
- 检查 Surface 编号范围
- 检查参数类型是否允许
- 检查参数单位是否正确
- 检查 start / end / step 是否在安全范围内
- 检查预计运行次数是否超过限制
- 检查是否强制 dry-run first
- 检查是否强制 read-only original model


当前核心接口：

```python
run_all_safety_checks(task, policy, project_root)

执行流程：
Task YAML
↓
Safety Policy YAML
↓
check_model_file()
↓
check_output_dir()
↓
check_target_range()
↓
check_run_count()
↓
check_execution_flags()
↓
errors list
```
### 是否调用 Zemax

否

当前模块没有调用：
ZOSAPI
TheApplication
TheSystem
OpticStudio

它只负责任务执行前的安全检查。

因此属于：

Task Safety Layer

不是：

Zemax Execution Layer
是否真实Safety

是

这个模块是真实工作的，不是 Mock。

真实功能包括：

根据 safety_policy.yaml 检查任务边界
根据 target.start / end / step 估算运行次数
根据 allowed_parameters 限制参数范围
根据 path_rules 限制路径行为
根据 execution 规则强制 dry-run 和只读模型


## modules/output_manager.py


### 类型

Output / Artifact Manager


### 当前功能

- 获取项目根目录
- 生成日期字符串
- 根据配置生成本次运行文件夹名称
- 自动创建本次运行输出目录
- 自动创建 CSV、figures、models、logs、reports 等子目录
- 生成常用输出文件路径
- 备份本次使用的配置文件
- 打印本次运行输出路径


当前核心接口：

```python
create_output_dirs(config)

backup_config(config_path, paths)

print_output_paths(paths)

config.yaml

↓

output_manager.py

↓

build_run_folder_name()

↓

create_output_dirs()

↓

paths 字典

↓

main.py / workflow_runner.py / report_generator.py 使用 paths
```

### 是否调用 Zemax

否

当前模块没有调用：

ZOSAPI
TheApplication
TheSystem
OpticStudio

它只负责输出目录和文件路径管理。

因此属于：

Runtime Output Layer

不是：

Zemax Execution Layer
是否真实Output Manager

是






