# Day53：Slot 2 六案例残余离焦批次审批

## 1. 为什么今天不直接运行六个案例

Day52 已确认零离焦基线能够复现，但“基线审核通过”只说明测量链路可靠，不等于剩余六个案例已经获得执行许可。Day53 的作用是把批次范围、运行顺序和安全边界写成一份明确授权。

## 2. 和 Day52 的关系

Day52 的状态是“基线结果审核通过，等待残余批次审批”。Day53 只消费这项申请资格，批准 Day54 运行六个非零偏移；它不会再次连接 Zemax。

## 3. 获批的六个案例

```text
defocus_001  -0.050 mm
defocus_002  -0.020 mm
defocus_003  -0.010 mm
defocus_005  +0.010 mm
defocus_006  +0.020 mm
defocus_007  +0.050 mm
```

`defocus_004 = 0.000 mm` 已在 Day51 执行，因此被明确排除，防止重复消费基线证据。

## 4. 什么是“批次契约”

批次契约相当于实验前写好的操作规程：

- 六个案例按固定顺序串行执行；
- 同一时刻最多一个 Standalone ZOS-API 连接；
- 每个案例使用独立工作副本；
- 每个案例导出相同的 Standard Spot 和 FFT MTF；
- 不允许 Quick Focus、优化或 SaveAs；
- 完成后立即停在 CP09，不自动进入 Day24。

## 5. “程序失败”和“光学性能差”不同

如果连接失败、文件指纹改变、分析导出失败，属于意外执行失败，应停止批次。某个偏移的 Spot 变大或 MTF 变低，则是实验结果，应记录下来继续运行后续案例，不能把它误当成程序故障。

## 6. 第一步运行方式

```powershell
python scripts/demos/day53_slot2_residual_batch_approval_plan.py
```

PLAN ONLY 只检查条件，不连接 Zemax，也不生成审批文件。

## 7. 完成标准

- Day52 CP09 审核记录和 Day51 基线结果有效；
- Day23 配置、聚焦模型和历史六案例证据指纹不变；
- 只批准六个非零偏移、一次批次；
- 串行、独立副本、连接关闭和指纹审计要求完整；
- 基线重跑、Quick Focus、优化、SaveAs 和 Slot3-6 继续锁定。

## 8. 第二步

PLAN ONLY 通过后运行：

```powershell
python scripts/demos/day53_generate_slot2_residual_batch_approval.py
```

它只生成审批 JSON 和 Markdown。真正的六案例 ZOS-API 批次由 Day54 的专用入口执行。
