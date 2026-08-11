# Day40：批准正式复核范围用于规划

## 1. 今日介绍

### 为什么今天做这个

Day39 已经计算出 Day22–Day28 的正式复核集合，但分析报告本身不能替代人工决策。Day40 练习由维护者确认该集合是否可以成为后续复核方案的输入。

### 和昨天的关系

Day39 回答“哪些节点受到影响”；Day40 回答“是否接受这份范围，并允许开始制定复核波次、资源槽和失败门”。今天仍然不批准任务执行。

### 今天需要掌握的概念

1. 正式范围审批；
2. 用途限定；
3. 规划许可与执行许可分离；
4. 下一道人工审批门。

### 完成标准

Day39 报告、Day22 配置和 Day35 `CP06_scope_approval` 均通过验证；审批只允许制定复核方案；修改源文件、连接 ZOS-API 和执行复核任务继续锁定。

## 2. 今天审批的是什么

审批对象是：

```text
正式复核顺序：[22, 23, 24, 25, 26, 27, 28]
ZOS-API 复核类：[23, 25]
离线复核类：[22, 24, 26, 27, 28]
```

审批状态定义为：

```text
REVIEW_SCOPE_APPROVED_FOR_PLANNING
```

名字中的 `FOR_PLANNING` 很重要，表示只能用于规划，不能直接执行。

## 3. 为什么 Day39 通过后还要人工审批

算法可以确认依赖关系，但维护者仍需要检查：

- 变化描述是否与真实意图一致；
- 依赖图是否适用于当前维护事件；
- ZOS-API 与离线分类是否合理；
- 是否需要额外的人工观察项目；
- 后续复核成本和风险是否可以接受。

因此“算法算完”与“组织允许继续”是两件事。

## 4. 批准后允许做什么

- 规划依赖安全波次；
- 规划资源可行的顺序槽；
- 规划失败传播和停止门。

这些都只是方案设计，不会启动任务。

## 5. 批准后仍不能做什么

- 修改 Day22 中的 `0.010 mm`；
- 把它改成申请中的 `0.012 mm`；
- 连接 ZOS-API；
- 重新计算 Spot 或 MTF；
- 执行 Day22–Day28；
- 声称工程变更已经批准。

## 6. 第一步怎样运行

在 VS Code 打开：

```text
scripts/demos/day40_review_scope_approval_plan.py
```

点击右上角运行按钮，或者在项目终端运行：

```powershell
python scripts/demos/day40_review_scope_approval_plan.py
```

## 7. 重点阅读哪些输出

- `Decision`：必须是 `REVIEW_SCOPE_APPROVED_FOR_PLANNING`；
- `Approved scope`：必须为 Day22–Day28；
- `Approved capabilities`：只能是波次、资源槽和失败门规划；
- `Still forbidden`：必须继续禁止修改、ZOS-API 和执行；
- 最后的五条 `[PASS]`：确认范围、人工门和权限边界。

## 8. 常见错误

- 使用模糊的 `APPROVED`，没有写清批准用途；
- 把范围审批误认为任务执行审批；
- 没有核对 Day39 报告 SHA256；
- 审批范围与 Day39 正式范围不一致；
- 忘记保留下一道人工审批门；
- 在规划阶段提前修改 Day22。

## 9. 下一步

计划检查通过后，运行：

```powershell
python scripts/demos/day40_generate_review_scope_approval.py
```

该脚本生成 Day40 JSON 和 Markdown 审批记录。运行后重点确认：

- `Review-plan generation released` 为 `True`；
- `Source modification released` 为 `False`；
- `Review-task execution released` 为 `False`；
- 七个节点仍被分成 Day23/Day25 两个 ZOS-API 复核类和五个离线复核类。

随后可以基于这份记录制定本次 Day22 变化专用的复核波次和资源方案，但仍不执行任务。
