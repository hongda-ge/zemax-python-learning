# Day 29：实验注册表与统一索引

## 为什么现在需要注册表

前三周已经积累了大量文件。一个 Day 通常可能包含：

- YAML 配置；
- 计划脚本；
- 基准验证脚本；
- 批量执行脚本；
- 离线分析脚本；
- 学习笔记；
- 输出目录和审计报告。

如果只依赖记忆，很快会出现以下问题：

- 忘记某个脚本属于哪一天；
- 不知道应该先运行计划还是批量脚本；
- 混淆当前光学教学主线与早期 D30、D37-D60 架构演示；
- 找不到某天对应的配置和笔记；
- 重复编写已经存在的功能。

实验注册表不是新的光学算法，而是项目的“目录和地图”。

## Day29 的注册范围

当前主线从 Day3 到 Day28，共 26 天。它分为三个阶段：

| 阶段 | 天数 | 主题 |
|---|---|---|
| foundation_and_scan | Day3-Day10 | 安全执行、基准、调焦、扫描和指标提取 |
| decision_and_solve | Day11-Day19 | 场景决策、Solve因果、Spot/MTF补偿 |
| mechanism_and_acceptance | Day20-Day28 | 行程、机构误差、残余离焦、验收和余量 |

早期 `D30`、`D37-D60` 文件属于另一条架构或工具实验线，不纳入 Day3-Day28 光学注册表。

## 为什么 Day3-Day7 是特殊情况

Day3-Day7 是逐步教学阶段，主要共用：

```text
configs/baseline_case.yaml
```

Day3-Day7 仍然共用同一份基准配置，但现在已经根据真实脚本和历史结果补齐了各自的学习笔记。注册表应继续明确记录“共用配置”，同时把文档缺口更新为空。

从 Day8 开始，项目形成了稳定规范：

```text
configs/dayN_*.yaml
scripts/demos/dayN_*.py
docs/learning_notes/DAYN_*.md
```

## 注册表准备记录什么

每一天至少记录：

- `day`：天数编号；
- `phase_id`：所属阶段；
- `primary_config`：主要配置文件；
- `scripts`：当天脚本列表；
- `learning_note`：学习笔记；
- `artifact_coverage_status`：文件覆盖状态；
- `documentation_gap`：已知文档缺口。

第一版不会仅凭文件名推断光学结论，因为文件名只能说明用途，不能替代报告证据。

## 第一步运行方式

请在 VS Code 中运行：

```powershell
python scripts/demos/day29_experiment_registry_plan.py
```

计划脚本会只读扫描配置、脚本和笔记，检查：

1. Day3-Day28 是否全部存在可执行脚本；
2. Day3-Day28 是否各有一篇学习笔记；
3. Day3-Day7 是否正确引用共享基准配置；
4. 如果以后再次出现学习笔记缺口，是否会被明确报告；
5. D30、D37-D60 是否保持在当前注册范围之外。

本步骤不会连接 Zemax，不会生成注册表文件，也不会修改任何既有 Day 文件。

## 第二步：生成三种注册表

计划审计通过后运行：

```powershell
python scripts/demos/day29_generate_experiment_registry.py
```

脚本会在 Day29 输出目录生成：

- `experiment_registry.csv`：适合 Excel 筛选和统计；
- `experiment_registry.json`：适合后续程序读取；
- `EXPERIMENT_REGISTRY.md`：适合人在 GitHub 或 VS Code 中浏览。

生成过程只读取现有配置、脚本和学习笔记，不修改既有 Day 文件，也不会连接 ZOS-API。

## 今天需要理解的项目思想

1. 自动化项目不仅要能运行，还要能被未来的自己理解。
2. 文件存在不等于证据完整，缺口应该明确记录。
3. 主线实验与架构原型必须分类，避免编号混乱。
4. 注册表记录来源和入口，不凭文件名制造科学结论。
5. 维护性是科研可重复性的一部分。
