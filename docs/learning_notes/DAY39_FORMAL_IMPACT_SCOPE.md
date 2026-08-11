# Day39：正式核验变化影响范围

## 1. 今日介绍

### 为什么今天做这个

Day38 只完成了权限审批，还没有实际计算变化会影响哪些任务。Day39 从冻结依赖图出发，独立计算 Day22 的全部下游，并检查 Day37 申请人的预估是否有遗漏或多报。

### 和昨天的关系

Day38 将权限推进到 `APPROVED_FOR_IMPACT_ANALYSIS`。Day39 使用这项有限权限读取 Day30 依赖图和 Day29 注册表，但不修改 Day22，也不运行任何复核任务。

### 今天需要掌握的概念

1. 直接下游；
2. 传递下游；
3. 正式复核集合；
4. 拓扑顺序；
5. 集合遗漏与多报。

### 完成标准

Day38 审批、Day30 依赖图、Day29 注册表和 Day22 指纹全部有效；正式集合包含变化源和所有传递下游；申请人预估的遗漏与多报被分别检查；没有执行任何任务。

## 2. 直接下游和传递下游

Day22 在依赖图中直接指向：

```text
Day22 -> Day23
Day22 -> Day26
Day22 -> Day27
```

但 Day23 又会影响 Day24、Day25，Day25 又会影响 Day26、Day27，Day27 还会影响 Day28。因此只检查直接下游是不够的，必须继续沿依赖边追踪，直到再也找不到新节点。

## 3. 正式复核集合怎样形成

计算规则是：

```text
正式复核集合 = 变化源本身 + 全部传递下游
```

然后按照 Day30 的拓扑顺序排列。拓扑顺序保证上游证据总是在引用它的下游证据之前复核。

## 4. 为什么不能只比较数量

假设正式集合是：

```text
[22, 23, 24, 25, 26, 27, 28]
```

另一个集合即使也有七个节点，也可能漏掉 Day24、错误加入 Day21。因此必须分别计算：

- `Omitted by requester`：正式集合有、申请人没有；
- `Overreported by requester`：申请人有、正式集合没有。

只有两个列表都为空，才是集合完全一致。

## 5. “受影响”不等于“必须立即重跑”

正式影响范围表示这些节点的证据需要复核。复核之后可能出现不同处理：

- 离线任务可能只需重新计算报告；
- ZOS-API 任务可能需要检查输入是否真的变化；
- 某些节点可能经过人工判断后无需执行。

Day39 只分类，不自动运行。

## 6. 第一步怎样运行

在 VS Code 打开：

```text
scripts/demos/day39_formal_impact_scope_plan.py
```

点击运行按钮，或者在项目终端运行：

```powershell
python scripts/demos/day39_formal_impact_scope_plan.py
```

## 7. 重点阅读哪些输出

- `Direct downstream`：Day22 的直接依赖对象；
- `All transitive descendants`：追踪到的全部下游；
- `Formal review order`：正式复核顺序；
- `ZOS-API review class` 与 `Offline review class`：任务分类；
- `Omitted by requester`：申请人遗漏；
- `Overreported by requester`：申请人多报；
- `Exact set match`：两个集合是否完全一致。

## 8. 常见错误

- 只检查 Day22 的直接下游；
- 只比较节点数量，不比较节点身份；
- 把祖先 Day21 也放进复核集合；
- 把“受影响”直接解释成“必须自动重跑”；
- 不按拓扑顺序排列复核节点；
- 正式分析前没有验证 Day38 审批和 Day30 图的 SHA256。

## 9. 下一步

计划检查通过后，运行：

```powershell
python scripts/demos/day39_generate_formal_impact_scope.py
```

该脚本生成 Day39 正式影响范围的 JSON、CSV 和 Markdown 报告。报告只确认需要复核的集合和任务类别，不批准 Day22 修改，也不批准任何任务执行。

运行后重点确认：

- 正式复核顺序为 `[22, 23, 24, 25, 26, 27, 28]`；
- 申请人遗漏和多报均为 `[]`；
- `Requester estimate exact match` 为 `True`；
- Day23、Day25 被归入 ZOS-API 复核类；
- 报告明确说明任务尚未批准、尚未执行。
