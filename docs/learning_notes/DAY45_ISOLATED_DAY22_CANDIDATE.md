# Day45：准备隔离的 Day22 候选配置

## 1. 为什么今天要创建候选

Day44 已经批准候选准备，但正式 Day22 配置仍是旧值 `0.010 mm`。为了评估申请中的 `0.012 mm`，需要一个明确、可审核、不会污染正式基线的输入文件。

候选配置位于 `outputs`，不是正式配置，也不能自动替代正式配置。

## 2. 和 Day44 的关系

Day44 只回答“是否允许准备候选”。Day45 负责证明准备过程遵守审批边界：

- 来源文件与 Day44 绑定的 SHA256 一致；
- 候选目录与审批中允许的目录一致；
- 只改变一个声明字段；
- 正式配置在前后保持同一 SHA256；
- 候选完成后仍不能运行 Day22。

## 3. 为什么不直接重新保存整份 YAML

普通 YAML 库重新保存时可能改变缩进、引号、数字表示或注释。虽然语义可能相同，但人工查看差异会变得困难。

Day45 采用：

1. 读取正式文件的原始文本；
2. 精确定位 `positioning_accuracy` 区块；
3. 只替换其中一行数值；
4. 再分别解析来源与候选 YAML；
5. 验证语义差异也只有一个字段。

这样同时获得“文本差异小”和“语义差异正确”。

## 4. 双指纹

执行前清单会同时记录：

- 来源 SHA256：证明候选从哪个正式配置生成；
- 候选 SHA256：证明后续审核和运行使用的是哪一个候选版本。

如果候选文件后来被修改，它的 SHA256 就会变化，后续审批必须拒绝旧指纹。

## 5. 单字段差异

唯一允许的变化是：

```text
teaching_error_sources.positioning_accuracy.symmetric_allowance_mm
0.010 -> 0.012 mm
```

任何其他新增、删除或数值变化都应让脚本停止。

## 6. 第一步运行方式

```powershell
python scripts/demos/day45_isolated_day22_candidate_plan.py
```

PLAN ONLY 只在内存中构造候选，不创建文件。

## 7. 完成标准

- Day44 审批和正式 Day22 指纹通过；
- 内存候选只替换一行；
- YAML 语义差异只有一个声明字段；
- 候选根目录符合 Day44 审批；
- 正式配置、Slot 1 执行和后续槽继续锁定；
- 不连接 ZOS-API，不进行任何离线复核计算。

## 8. 第二步：生成候选和执行前清单

PLAN ONLY 结果确认后，运行：

```powershell
python scripts/demos/day45_generate_isolated_day22_candidate.py
```

该脚本会在 Day44 批准的 `outputs` 根目录下生成：

- 隔离候选 YAML；
- `candidate_pre_execution_manifest.json`；
- `DAY45_CANDIDATE_REVIEW.md`。

它会重新打开写入磁盘的候选，复查唯一语义差异和候选 SHA256。即使全部通过，Slot 1 仍未获得执行许可。
