# Day50：Slot 2 / Day23 零离焦基线控制审批

## 1. 为什么今天要先审批基线控制

Day49 已经确认 Slot 1 的离线复核任务执行正确，也允许我们申请 Slot 2。但 Slot 2 的 Day23 会连接 Zemax、复制模型并运行 Spot 与 FFT MTF，风险明显高于离线计算。

因此 Day50 不直接运行整个 Day23，而是只批准一个最小实验：`defocus_004` 零离焦基线控制。

这个步骤的目的，是在采用新 Day22 教学假设后，先证明旧的光学基线仍可复现，再考虑六个非零残余离焦案例。

## 2. 和 Day49 的关系

Day49 得到的是：

- Slot 1 任务审核为 `PASS`；
- 新定位精度为 `+/-0.012 mm`；
- 两种误差组合策略仍只有 `4/6` 教学案例通过；
- 可以申请 Slot 2，但 Slot 2 尚未释放。

Day50 消费的不是“工程结论”，而是“允许申请下一槽”的资格。

## 3. 为什么不能直接复用旧 Day23 入口

旧 Day23 流程是围绕原 Day22 的 `0.010 mm` 定位精度证据建立的。新变化证据现在包含 `0.010、0.012、0.020 mm` 三种分量值。

如果原样调用旧校验逻辑，它可能把新的 `0.012 mm` 识别为“不符合旧证据”，即使光学模型本身没有变化。

所以 Day50 冻结了一个专用 Day51 入口：

```text
scripts/demos/day51_execute_approved_day23_baseline_control.py
```

这个入口必须显式验证新 Day22 结果，同时沿用原 Day23 的模型、Spot 配方和 FFT MTF 配方。

## 4. 什么是“基线控制”

基线控制是零偏移案例：

- 案例：`defocus_004`；
- 残余离焦：`0.000 mm`；
- 输入：Day8 已聚焦模型；
- 分析：Standard Spot 和 FFT MTF；
- Quick Focus：禁止；
- 优化：禁止；
- SaveAs：禁止。

它的任务不是寻找更好的设计，而是检查相同输入和相同分析配方能否复现原来的参考值。

## 5. 为什么要把基线和批次分开

若基线都无法复现，直接运行六个非零点只会生成一批来源可疑的数据。分段后：

1. Day50 批准一次基线；
2. Day51 执行一次基线并停止；
3. 人工审核模型指纹、连接关闭和数值复现；
4. 只有审核通过，才考虑非零残余离焦批次。

这就是“先证明测量尺没有变，再测量新案例”。

## 6. 第一步运行方式

```powershell
python scripts/demos/day50_slot2_day23_baseline_approval_plan.py
```

PLAN ONLY 只验证审批条件，不连接 Zemax，不复制模型，也不生成审批文件。

## 7. 完成标准

- Day49 的 CP09 记录有效；
- Day48 的 `0.012 mm` 变化证据有效；
- Day42 的 Slot 2 只包含 Day23；
- Day23 配置、聚焦模型和历史基线指纹不变；
- 只批准 `defocus_004` 一次执行；
- 六个非零案例、Quick Focus、优化和 SaveAs 继续锁定；
- Day50 本身不连接 ZOS-API、不运行光学分析。

## 8. 第二步：生成审批记录

PLAN ONLY 通过后运行：

```powershell
python scripts/demos/day50_generate_slot2_day23_baseline_approval.py
```

它只写审批 JSON 和 Markdown。真正的 ZOS-API 基线控制将在 Day51 通过专用入口执行。
