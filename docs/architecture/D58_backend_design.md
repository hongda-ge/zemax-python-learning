# D58 Backend 架构设计

## 目标

建立 Backend 抽象层，使 Workflow Runner 不再直接依赖模拟函数，也不直接依赖 ZOS-API。

## 当前问题

D57 审计发现：

- workflow_runner.py 使用 simulate_optical_metrics()
- zemax_runner.py 目前只是占位文件
- tool_registry.py 中 open_model / run_analysis / run_sweep 均为 Mock
- 项目缺少统一 Backend 接口

## D58 改进

新增：

- BaseBackend
- MockBackend
- ZemaxBackend placeholder

## 当前结构

Workflow Runner
    ↓
Backend Interface
    ├── MockBackend
    └── ZemaxBackend

## 当前状态

- MockBackend 可运行
- ZemaxBackend 仅为空壳
- 尚未接入真实 ZOS-API

## 下一步

D59 将把现有 ZOS-API Standalone 连接代码迁移到 ZemaxBackend。