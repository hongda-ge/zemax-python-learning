# Day46：候选执行前审核

## 1. 为什么今天还不能运行 Day22

Day45 已经生成了 `0.012 mm` 候选，但“文件成功生成”只说明准备动作完成，不能证明：

- 现在读取的候选仍是 Day45 生成的版本；
- 正式配置没有被后来修改；
- 候选仍然只有一个声明差异；
- Day45 保留的执行锁没有被意外打开。

所以 Day46 要从磁盘重新计算指纹并重新比较 YAML，而不是直接相信 Day45 的终端输出。

## 2. 和 Day45 的关系

Day45 回答“候选是什么”；Day46 回答“这个候选是否具备申请执行许可的资格”。

今天读取：

- Day44 候选准备审批；
- Day45 执行前清单；
- 正式 Day22 配置；
- Day45 候选配置。

四项证据必须同时匹配。

## 3. 执行前审核

执行前审核发生在计算许可之前。它检查输入身份和边界，但不产生新的 Day22 数值结果。

本次审核重新验证：

1. 正式配置 SHA256；
2. 候选配置 SHA256；
3. 候选位于 Day44 批准的 `outputs` 根目录；
4. YAML 只有一个语义差异；
5. 差异为定位精度 `0.010 -> 0.012 mm`；
6. Slot 1、ZOS-API 和下游槽仍未释放。

## 4. “具备资格”不等于“获得授权”

Day46 的计划决策状态是：

```text
CANDIDATE_VERIFIED_WAITING_FOR_SLOT_01_EXECUTION_APPROVAL
```

它表示候选可以提交下一道审批，但以下权限仍为 `False`：

- 修改正式 Day22 配置；
- 执行 Slot 1；
- 连接 ZOS-API；
- 计算新的光学指标；
- 释放 Slot 2-6；
- 宣称工程变化获批。

## 5. 第一步运行方式

```powershell
python scripts/demos/day46_candidate_pre_execution_review_plan.py
```

该脚本只进行只读审核并打印计划，不生成审核记录，也不运行 Day22。

## 6. 完成标准

- Day44 和 Day45 证据指纹有效；
- 双指纹能够从磁盘独立复现；
- 只有一个声明的 YAML 语义差异；
- 候选仍在批准目录；
- 审核结论只允许申请下一道执行审批；
- Slot 1、ZOS-API 和 Slot 2-6 仍锁定。

## 7. 第二步：生成审核记录

PLAN ONLY 结果确认后运行：

```powershell
python scripts/demos/day46_generate_candidate_pre_execution_review.py
```

该脚本只生成 JSON 和 Markdown 审核记录。它不会运行 Day22，也不会批准 Slot 1 执行。
