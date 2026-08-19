# Day 69：审批 Day27 证据恢复零偏移控制

## 为什么今天做

Day68 已经把七个缺失点和完整恢复路线规划清楚。因为后续批次需要重新连接 Zemax，Day69 先只批准一个零偏移控制，避免一次性放行全部恢复工作。

## 和昨天的关系

Day68 只允许申请控制审批。Day69 将这项资格转换为一次、单连接、单副本的执行许可，但自身不执行任何分析。

## 核心概念

### 1. 控制优先

在新七点补测前，先用 0 mm 状态复现历史 Spot 和 FFT MTF，可以确认模型、像面位置和分析设置没有漂移。

### 2. 单阶段授权

Day69 只释放恢复路线的 `stage_01_zero_control`。七点批次、Day27 离线重算和 Slot 6 仍是独立审批阶段。

### 3. 最小 ZOS-API 权限

Day70 最多使用：

- 一个隔离工作副本；
- 一个 Standalone 连接；
- 一次 Standard Spot；
- 一次 FFT MTF。

Quick Focus、优化和 SaveAs 均禁止。

### 4. 审批与执行分离

Day69 生成执行许可证，不消费许可证。只有 Day70 专用入口可以执行一次控制。

## 操作流程

先运行审批计划：

```powershell
python scripts/demos/day69_day27_recovery_baseline_approval_plan.py
```

确认后生成审批记录：

```powershell
python scripts/demos/day69_generate_day27_recovery_baseline_approval.py
```

## 完成标准

- Day68 计划与七点清单指纹有效；
- Day25 配方、聚焦模型和历史控制有效；
- 只释放一次零偏移控制；
- Day69 不连接 ZOS-API；
- 七点批次、Day27 重算和 Slot 6 继续锁定。

## 简历表达参考

为 ZOS-API 证据恢复批次设计控制优先的最小权限审批，冻结模型、分析配方、执行入口和资源上限，将零偏移复现与七点补测分段放行，降低错误传播风险。
