# Day37：维护变化申请

## 1. 今日介绍

### 为什么今天做这个

Day35 建立了维护手册，Day36 又通过正常和失败路线验证了流程。但之前的“Day22 发生变化”是直接给定的，还没有说明维护开始前应当记录哪些信息。Day37 用变化申请单补齐这个入口。

### 和昨天的关系

Day36 的假想变化直接进入了影响分析；Day37 回到更前面，练习 Day35 的 `CP01_change_intake`，并保留 `CP06_scope_approval` 人工门。

### 今天需要掌握的概念

1. 变化申请；
2. 申请人预估影响范围；
3. 证据指纹；
4. 草稿、审核和批准的区别。

### 完成标准

申请目标能够映射到 Day29 注册表；当前文件 SHA256 和字段值匹配；变化原因、风险和回滚方式完整；申请保持 `DRAFT`，不释放任何执行任务。

## 2. 今天登记的假想变化

教学申请假想把 Day22 的定位精度对称误差值从：

```text
±0.010 mm -> ±0.012 mm
```

这不是实际修改。计划脚本只检查“如果有人提出这个变化，申请信息是否完整”。

## 3. 为什么需要当前 SHA256

申请单中的“当前值”只有在对应某个明确文件版本时才有意义。如果 Day22 配置已经变化，而申请仍引用旧值，后续维护可能从错误基线开始。因此先验证文件 SHA256，再讨论影响。

## 4. 为什么申请人的范围不能直接采用

申请人可以预估 Day22-Day28 可能受影响，但这只是风险提示。正式范围必须由 Day30 依赖图和 Day31 变化影响分析重新计算。否则容易漏掉间接下游，或者把无关任务也加入复核。

## 5. 草稿完整不等于批准

这三个状态要分开理解：

```text
DRAFT               信息正在填写或已完成，但尚未审核
WAITING_FOR_APPROVAL 已提交给维护者，等待人工决定
APPROVED             人工批准了复核范围，但仍不等于自动运行
```

Day37 第一步必须保持 `DRAFT` 和 `NOT_REVIEWED`。

## 6. 第一步运行

```powershell
python scripts/demos/day37_change_request_plan.py
```

这一步不会生成正式申请文件，不会修改 Day22，也不会连接 ZOS-API。

## 7. 需要重点阅读的输出

- `Target SHA256`：申请针对的 Day22 文件版本；
- `Teaching value`：当前值和拟议值；
- `Risk hypotheses`：目前只是风险假设；
- `Requester-estimated review Days`：必须显示 `UNVERIFIED`；
- `Approval`：应为 `NOT_REVIEWED`；
- `execution released`：必须为 `False`。

## 8. 常见错误

- 只写“我要改参数”，不写具体文件和字段；
- 不核对当前值和文件指纹；
- 把申请人猜测的影响范围当成最终结论；
- 信息完整后直接自动执行；
- 没有写失败后的回滚方式；
- 把教学数值变化说成真实机构需求。

## 9. 下一步

计划检查通过后，运行：

```powershell
python scripts/demos/day37_generate_change_request.py
```

第二步生成正式 JSON 和 Markdown 变化申请，并把报告状态从 `DRAFT` 推进到 `WAITING_FOR_APPROVAL`。这表示申请已提交审核，仍然不执行影响分析和历史任务。

生成后应重点检查：

- Day22 文件 SHA256 是否保持不变；
- `change_written_to_target` 是否为 `False`；
- `scope_is_unverified` 是否为 `True`；
- `approval_status` 是否仍为 `NOT_REVIEWED`；
- `execution_released` 是否为 `False`。

Day38 可以练习人工审批记录：批准的是“进入影响分析”，而不是批准自动修改或自动重跑。
