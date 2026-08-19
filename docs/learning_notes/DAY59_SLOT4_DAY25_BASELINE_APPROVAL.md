# Day 59：审批 Slot 4 的 Day25 零偏移控制

## 为什么今天做

Day58 证明 Slot 3 的离线验收正确，但 Day25 会重新连接 Zemax 并运行边界加密案例。为了避免一次批准九个案例，Day59 先只批准零偏移控制。

## 和昨天的关系

Day58 让项目具备申请 Slot 4 的资格；Day59 把申请转化为最小权限审批，但不执行任何光学分析。

## 核心概念

### 1. 高风险分段

先运行控制组，证明模型、分析配方和连接生命周期稳定；控制审核通过后，九个边界实验组仍需单独审批。

### 2. 控制组

`boundary_control_000` 的离焦偏移为 0 mm。它应复现已有 Spot/MTF，并在 Day24 的均衡教学阈值下通过。

### 3. 最小 ZOS-API 权限

Day60 最多使用一个工作副本和一个 Standalone 连接，只允许 Standard Spot 与 FFT MTF，不允许 Quick Focus、优化或 SaveAs。

### 4. 审批不是执行

Day59 生成的是运行许可证。终端中的 `Approved task executed by Day59: False` 表示今天没有连接 Zemax。

## 操作流程

先运行审批规划：

```powershell
python scripts/demos/day59_slot4_day25_baseline_approval_plan.py
```

规划通过后生成审批记录：

```powershell
python scripts/demos/day59_generate_slot4_day25_baseline_approval.py
```

## 完成标准

- Day58、Day42、Day25、聚焦模型和历史控制指纹有效；
- 只释放一次零偏移控制；
- Day59 不连接 ZOS-API；
- 九个边界案例和 Slot 5-6 继续锁定。

## 简历表达参考

设计 ZOS-API 高风险批次的分段授权机制，通过冻结模型与分析配方、零偏移控制复现和单连接约束，在批量边界扫描前建立可审计的基线质量门。
