# Day 15：保留 Solve 与冻结曲率的双分支验证

## 今天解决的问题

Day 14 确认面6曲率带有 `MarginalRayAngle` 依赖型 Solve。当面2空气间隔发生变化时，面6曲率会自动重新求值。因此，Day 15 不急着计算 Spot 或 MTF，而是先回答一个更基础的因果问题：

> 面6曲率的变化究竟来自面2厚度本身，还是来自仍然生效的 Zemax Solve？

为避免把多个作用混在一起，本次只比较模型结构响应，不执行 Quick Focus、光学分析或优化。

## 实验参数

本次使用冻结的 Cooke 基准模型：

```text
面2空气间隔：6.0075511 → 5.9075511 mm
变化量：      -0.1 mm

面6初始曲率半径：-18.3953326030 mm
面6初始曲率 Solve：MarginalRayAngle
目标边缘光线角度：-0.100000001
```

面2厚度的物理含义是第一片与第二片镜片之间的空气间隔。

## 为什么使用两个独立分支

如果先在同一个模型中保留 Solve，再把它冻结，第二次实验可能继承第一次实验的内存状态，导致比较不公平。因此脚本从同一个原始模型创建两个独立的磁盘工作副本：

1. `preserve_solve`：保留面6曲率的 `MarginalRayAngle`；
2. `freeze_radius`：先把面6曲率转为 `Fixed`，再改变面2空气间隔。

两个分支唯一有意设置的区别是面6曲率 Solve 是否保留。随后，两个分支都写入相同的面2目标厚度。

## 实验流程

```text
同一个冻结基准模型
        │
        ├── 保留 Solve 分支
        │     保留 MarginalRayAngle
        │     改变面2厚度
        │     读取面6曲率与 Solve
        │
        └── 冻结曲率分支
              MarginalRayAngle → Fixed
              改变面2厚度
              读取面6曲率与 Solve
```

脚本的安全步骤如下：

1. 验证原始模型 SHA256；
2. 验证 Day 14 的 Solve 审计报告；
3. 创建两个不同路径的工作副本；
4. 使用 Standalone ZOS-API 依次打开两个副本；
5. 只在 Zemax 内存中修改 Solve 和面2厚度；
6. 不使用 Quick Focus、Spot、MTF、优化或 SaveAs；
7. 关闭连接后重新计算三个磁盘模型的 SHA256；
8. 将结构比较结果写入 JSON 报告。

## 最终结果

### 分支一：保留 MarginalRayAngle

```text
面6曲率：-18.3953326030 → -18.3911980887 mm
Solve：  MarginalRayAngle → MarginalRayAngle
变化量：+0.0041345144 mm
```

面2空气间隔改变后，Solve 仍然生效，并自动重新计算了面6曲率。

### 分支二：冻结面6曲率

```text
面6曲率：-18.3953326030 → -18.3953326030 mm
Solve：  MarginalRayAngle → Fixed
变化量：0 mm
```

当曲率被固定后，同样的面2空气间隔变化没有再引起面6曲率变化。

### 分支差异

相同的面2厚度变化产生了：

```text
两个分支最终面6曲率之差：+0.0041345144 mm
```

因此，Day 14 观察到的面6曲率联动可以明确归因于 `MarginalRayAngle` Solve，而不是 ZOS-API 写入面2厚度时无缘无故修改了另一个曲率。

## 如何理解 0.0041345144 mm

`0.0041345144 mm` 在单位换算上约等于 `4.13 μm`，但它表示的是**曲率半径数值的变化量**。它不能直接当作：

- 镜片表面矢高变化；
- 面形误差；
- 加工公差；
- 光斑尺寸变化。

若要得到这些工程含义，还必须结合口径、表面几何和后续光学分析进行计算。

## 对 Day 8 和 Day 13 的修正认识

Day 8/13 的真实执行链路是：

```text
改变面2空气间隔
        ↓
MarginalRayAngle 自动重算面6曲率
        ↓
Quick Focus 调整面6厚度
        ↓
计算 Spot
```

所以原有结果仍然是真实、可复现的 Zemax 响应，但应描述为：

> 当前 Solve 规则和 Quick Focus 补偿策略下的系统响应。

不能把它描述成“除面2空气间隔外，所有曲率都冻结”的纯单变量制造公差实验。

## 为什么本日没有计算 Spot 和 MTF

Day 15 的目的不是选出更好的方案，而是隔离结构因果关系。如果同时运行 Quick Focus 和 Spot，就会同时出现：

- 面6曲率 Solve 的影响；
- 像面补偿的影响；
- 成像质量的变化。

这样就很难判断差异首先发生在哪里。先验证结构、再分析性能，是更可靠的实验顺序。

## 安全审计结果

- ZOS-API 正常关闭；
- 原始模型 SHA256 未变化；
- 保留 Solve 分支的磁盘副本 SHA256 未变化；
- 冻结曲率分支的磁盘副本 SHA256 未变化；
- 所有模型修改只存在于 Zemax 内存；
- 未使用 Quick Focus、光学分析、优化或 SaveAs。

输出报告位于 `outputs/day15_solve_branch_validation`。该目录用于本地实验审计，不作为源代码提交到 GitHub。

## 今天掌握的核心概念

- 依赖型 Solve 会让一次参数写入产生联动响应；
- 严格的对照实验要求两个分支从相同初始状态独立开始；
- “只改一行 Python”不等于“光学模型只改变一个自由度”；
- 在比较 Spot/MTF 之前，应先确认模型结构到底发生了什么；
- SHA256 不只保护原始模型，也能证明工作副本没有被内存实验写回磁盘。

## 下一步

Day 16 可以在两个分支中采用相同的补偿和分析设置：

1. 分别执行 Quick Focus；
2. 分别导出 Standard Spot；
3. 比较面6曲率、焦移和三个视场的 RMS Spot；
4. 继续保持原始模型和工作副本不可覆盖。

这样才能回答真正的性能问题：

> 保留设计 Solve 与冻结制造后曲率，对最终成像质量的影响有多大？

该比较已在 [Day 16：Solve 双分支的 Quick Focus 与 Spot 比较](DAY16_SOLVE_BRANCH_SPOT_COMPARISON.md) 中完成。单个 `−0.1 mm` 案例显示：冻结曲率会增加所需焦移，但在允许 Quick Focus 后，两个分支的最终 RMS Spot 非常接近。

## 运行入口

### 1. 只检查实验计划

```powershell
python scripts/demos/day15_solve_branch_plan.py
```

### 2. 执行内存双分支验证

```powershell
python scripts/demos/day15_run_solve_branch_validation.py
```
