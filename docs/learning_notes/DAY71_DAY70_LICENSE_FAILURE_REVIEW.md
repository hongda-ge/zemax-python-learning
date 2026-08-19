# Day 71：审核 Day70 的 ZOS-API 许可证失败

## 为什么今天做

Day70 的一次性授权已经消费，但 Standalone ZOS-API 连接没有成功。如果直接重跑，会破坏一次性授权和审计链，因此必须先审核失败。

## 和昨天的关系

Day70 在 Spot/FFT MTF 之前停止，并留下失败 JSON、消费标记和工作副本。Day71 只检查这些证据，不连接 Zemax。

## 核心概念

### 1. 许可证失败不是光学失败

本次错误发生在连接阶段，没有计算 Spot 或 MTF，因此不能对光学性能作任何结论。

### 2. `connection_closed=false` 的正确解释

连接构造函数在成功建立连接前抛出异常，因此没有可关闭的连接对象。关闭异常窗口后，系统中没有残留 Python 或 OpticStudio 进程。

### 3. 一次性授权仍然有效消费

授权标记在连接前写入，这是故意的安全设计。即使执行失败，原授权也不能重复使用，必须签发新的重试审批。

### 4. GUI恢复不等于API验证

操作者已经重新打开 OpticStudio 并确认 GUI 可运行，随后完全关闭。但只有新的 Standalone 连接尝试才能验证 ZOS-API 许可证，因此 Day71 不宣称许可证已经恢复。

## 操作流程

先运行审核计划：

```powershell
python scripts/demos/day71_day70_license_failure_review_plan.py
```

计划通过后生成审核记录：

```powershell
python scripts/demos/day71_generate_day70_license_failure_review.py
```

## 完成标准

- Day70 失败类型和错误文本准确；
- 原授权已消费且不可复用；
- 没有 Spot/MTF 输出；
- 模型和副本哈希未变；
- 只开放新重试审批申请资格；
- 重试执行、七点批次和 Slot 6 保持锁定。

## 简历表达参考

设计 ZOS-API 失败恢复审计，将许可证连接异常与光学性能失败分离；通过一次性授权消费、前后哈希验证、残留进程检查和最小重试权限，保证异常情况下的证据链完整性与可恢复性。
