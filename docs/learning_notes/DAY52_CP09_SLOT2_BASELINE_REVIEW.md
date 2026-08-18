# Day52：CP09 审核 Slot 2 零离焦基线结果

## 1. 为什么运行成功后还需要审核

Day51 的终端全部显示 `[PASS]`，但程序自己打印成功，并不等于维护流程可以自动进入下一阶段。

Day52 独立检查：

- 输入是否是获批模型；
- 消费的是否是 Day50 那一份审批；
- 是否只运行了 `defocus_004`；
- Spot 和 MTF 原始文件是否真实存在；
- 模型、工作副本和分析结果能否互相印证；
- 连接是否关闭；
- 是否偷偷运行了禁止操作。

这就是 CP09 的作用：把“程序声称成功”转换成“维护者认可这份证据”。

## 2. 和 Day51 的关系

Day51 负责执行，Day52 负责审核。二者不能合并，否则执行脚本相当于自己给自己签字。

Day52 不会重新计算 Spot 或 MTF，只读取并核查 Day51 已经产生的结果。

## 3. 什么是证据完整性

完整结果不只有一个 JSON。至少包括：

- `slot2_baseline_control_result.json`；
- Standard Spot 原始文本；
- FFT MTF 原始文本；
- 隔离工作模型；
- 输入模型 SHA256；
- 工作副本执行前后 SHA256；
- ZOS-API 关闭状态。

Day52 会为两个原始分析文本再次计算 SHA256，并将它们写入审核记录。

## 4. 为什么零差值重要

Day51 得到：

- 最大 Spot 复现差值：`0.000000000 um`；
- 最大 MTF 复现差值：`0.000000000`。

这说明在当前机器、Zemax 版本、模型和分析配方下，维护后的基线与历史证据完全一致。

它证明“测量链没有意外变化”，但不证明 `+/-0.012 mm` 的机构方案已经满足工程要求。

## 5. 审核通过不等于批次放行

Day52 的状态是：

```text
SLOT_02_BASELINE_RESULT_REVIEW_PASSED_WAITING_FOR_RESIDUAL_BATCH_APPROVAL
```

它只允许下一步提出“六个非零残余离焦案例”的审批申请。仍然禁止：

- 重新运行 Day51；
- 直接运行六案例；
- 新建 ZOS-API 连接；
- 修改正式配置或模型；
- 释放 Slot 3-6；
- 宣称工程变更获批。

## 6. 第一步运行方式

```powershell
python scripts/demos/day52_cp09_slot2_baseline_review_plan.py
```

PLAN ONLY 只进行离线审核，不连接 Zemax，也不生成审核记录。

## 7. 完成标准

- Day51 结果和 Day50 审批指纹有效；
- 一次性授权已正确消费；
- 只执行了零离焦案例；
- Spot、MTF 和工作模型文件齐全；
- 基线在冻结容差内复现；
- 模型未修改、连接已关闭；
- 审核为 PASS；
- 六案例仍未释放。

## 8. 第二步：生成审核记录

PLAN ONLY 通过后运行：

```powershell
python scripts/demos/day52_generate_cp09_slot2_baseline_review.py
```

该脚本只生成 JSON 与 Markdown 审核记录，不会重新连接 Zemax。
