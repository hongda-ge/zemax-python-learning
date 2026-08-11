# Day38：只批准进入影响分析

## 1. 今日介绍

### 为什么今天做这个

Day37 已经生成了一份完整的变化申请，但“申请完整”只说明信息足够审查，并不意味着可以立刻修改配置。Day38 的任务是练习分级授权：维护者可以先批准开展影响分析，再根据分析结果决定是否批准修改和复核运行。

### 和昨天的关系

Day37 的输出状态是 `WAITING_FOR_APPROVAL`。Day38 将审查这份固定版本的申请，并计划把状态推进到 `APPROVED_FOR_IMPACT_ANALYSIS`。申请人填写的 Day22–Day28 仍然只是预估，不能代替正式依赖分析。

### 今天需要掌握的概念

1. 分级授权；
2. 审批对象与证据指纹；
3. 最小权限原则；
4. “批准分析”和“批准修改”的区别。

### 完成标准

Day37 申请、Day22 配置和 Day35 人工审批门均通过验证；批准能力只有读取依赖证据、计算正式复核范围、生成影响分析报告；修改 Day22、连接 ZOS-API 和执行历史任务仍然为禁止状态。

## 2. 为什么要分成三次批准

维护工作中至少有三种不同决定：

```text
批准影响分析  -> 允许计算“哪些任务可能受影响”
批准源文件修改 -> 允许真正改变目标配置
批准复核执行  -> 允许按审核后的范围重新运行任务
```

如果把它们合并为一次“同意”，审批者可能只想了解影响范围，系统却已经修改文件甚至启动 Zemax。这就是权限边界不清造成的风险。

## 3. 今天批准了什么

计划中的状态是：

```text
APPROVED_FOR_IMPACT_ANALYSIS
```

它只允许：

- 读取冻结的依赖证据；
- 正式计算复核范围；
- 生成影响分析报告。

它不允许：

- 修改 Day22 配置；
- 连接 ZOS-API；
- 计算新光学指标；
- 自动执行 Day22–Day28；
- 把申请人的预估范围直接当成结论。

## 4. 为什么审批也需要 SHA256

审批不是只针对“Day37”这个名字，而是针对某一份具体申请文件。若申请内容在审批后被悄悄改变，原审批就不应继续有效。因此计划同时核对：

- Day37 申请报告 SHA256；
- Day22 目标配置 SHA256；
- 申请编号 `CR-DAY37-001`；
- 当前申请状态 `WAITING_FOR_APPROVAL`。

这叫做让审批与证据版本绑定。

## 5. 第一步怎样运行

在 VS Code 中打开：

```text
scripts/demos/day38_impact_analysis_approval_plan.py
```

然后点击右上角运行按钮，或者在项目终端运行：

```powershell
python scripts/demos/day38_impact_analysis_approval_plan.py
```

这一步只检查审批计划，不生成审批记录，也不会修改 Day22。

## 6. 你需要重点阅读的输出

- `Decision`：应为 `APPROVED_FOR_IMPACT_ANALYSIS`；
- `Requester estimate`：仍须显示 `UNVERIFIED`；
- `Approved capabilities`：只能有三项影响分析能力；
- `Still forbidden`：必须明确列出修改、ZOS-API、光学计算和历史执行禁令；
- 最后的六条 `[PASS]`：说明申请版本、人工门和权限边界都正确。

## 7. 常见错误

- 把批准影响分析写成笼统的 `APPROVED`；
- 审批时不验证申请文件 SHA256；
- 把 Day22–Day28 的申请人预估当作正式范围；
- 一批准就自动修改 Day22；
- 一批准就自动运行所有下游任务；
- 没有写明下一道人工审批门。

## 8. 下一步

计划检查通过后，运行：

```powershell
python scripts/demos/day38_generate_impact_analysis_approval.py
```

该脚本生成正式的 JSON 和 Markdown 审批记录，把权限推进到“允许影响分析”，但仍不会执行影响分析。生成后重点确认：

- `Impact-analysis permission released` 为 `True`；
- `Source modification released` 为 `False`；
- `Historical task execution released` 为 `False`；
- 申请人预估范围仍显示 `UNVERIFIED`；
- Day22 的 SHA256 保持不变。

之后的 Day39 才可以基于 Day30/Day31 方法，正式核验本次 Day22 变化的影响范围。
