# Day 70：执行获批的证据恢复零偏移控制

## 为什么今天做

Day69 已经签发一次零偏移控制授权。Day70 需要消费它，在七点补测之前确认模型、像面位置和 Spot/FFT MTF 配方仍然稳定。

## 和昨天的关系

Day69 只批准一个控制案例。Day70 必须严格使用该审批绑定的模型、输出目录和专用入口，不能顺带运行七个恢复点。

## 核心概念

### 1. 一次性授权消费

程序在连接 Zemax 之前写入消费标记。即使之后出现异常，同一审批也不能静默重用。

### 2. 基线复现

零偏移状态应复现历史 Spot RMS、MTF30 和 MTF50。冻结容差为 Spot `1e-6 um`、MTF `1e-6`。

### 3. 双重验证

除了数值复现，还要重新检查均衡教学场景的四项独立指标，确保控制仍然通过。

### 4. 安全收尾

执行后必须确认输入模型、磁盘工作副本和所有冻结输入未变，并关闭 Standalone 连接。

## 操作流程

先运行只读计划：

```powershell
python scripts/demos/day70_approved_recovery_baseline_control_plan.py
```

计划通过后执行一次控制：

```powershell
python scripts/demos/day70_execute_approved_recovery_baseline_control.py
```

## 完成标准

- Day69 审批只消费一次；
- 只运行 `recovery_control_000`；
- Spot/MTF 完整复现并通过均衡规则；
- 连接关闭且模型指纹不变；
- 七点批次、Day27 重算和 Slot 6 继续锁定；
- 结果停在 CP09 等待审核。

## 简历表达参考

实现 ZOS-API 一次性授权消费与恢复批次基线控制，通过独立工作副本、Spot/FFT MTF 回归复现、四指标验收和连接生命周期审计，在补测批次前建立可追溯质量门。

## 本次实际执行结果

本次 Day70 没有完成光学控制。一次性授权已在连接前正确消费，但 Standalone 连接建立失败：

```text
ZemaxConnectionError: The current OpticStudio license is not valid for ZOS-API.
```

失败发生在 Spot 和 FFT MTF 之前，因此没有产生新的光学指标。安全审计确认：

- 冻结输入模型 SHA256 未改变；
- 隔离工作副本 SHA256 未改变；
- 没有运行 Quick Focus、优化或 SaveAs；
- 异常窗口关闭后没有残留 Python 或 OpticStudio 进程；
- 七点恢复批次、Day27 重算和 Slot 6 仍然锁定。

失败报告：

`outputs/day69_day27_recovery_baseline_execution/execution_20260819_211252/recovery_control_000/recovery_baseline_control_result.json`

由于 Day69 是一次性授权，许可证恢复后也不能直接重跑 Day70。必须先审核失败证据，再签发新的恢复执行授权。
