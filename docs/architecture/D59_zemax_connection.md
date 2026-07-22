# D59 Zemax 2024 R1 真实连接回归

## 目标

验证 Project-X 的正式 Python 3.8 环境能够通过 Python.NET 真实启动
OpticStudio、检查 API 许可证、取得 `PrimarySystem`，并在测试后安全关闭应用。

本阶段只验证连接生命周期，不打开模型、不修改 LDE、不执行任何光学分析。

## 调用链

```text
Python 3.8.20
  -> pythonnet 2.5.2 / clr
  -> ZOSAPI_NetHelper.dll
  -> ZOSAPI.dll + ZOSAPI_Interfaces.dll
  -> ZOSAPI_Connection
  -> CreateNewApplication
  -> PrimarySystem
  -> CloseApplication
```

## 文件

- `modules/zemax/connection.py`：正式 Standalone 连接与资源释放模块。
- `scripts/demos/D59_zemax_connection_demo.py`：最小真实连接 Demo。
- `outputs/D59_zosapi_connection_result.json`：本机测试证据，不提交 Git。

## 运行

```powershell
python scripts/demos/D59_zemax_connection_demo.py
```

运行时 OpticStudio 窗口可能短暂出现，然后由 Demo 自动关闭。

## 2026-07-22 本机回归结果

```json
{
  "backend": "zemax",
  "simulation_mode": false,
  "status": "success",
  "connection_closed": true,
  "connected": true,
  "version": "24.1 SP3",
  "license_valid": true,
  "primary_system_available": true
}
```

测试后进程检查结果：`opticstudio_processes=none`。

## 为什么使用上下文管理和 finally

Standalone 模式会创建真实的 OpticStudio 应用实例。若脚本在中途报错但没有关闭
应用，可能留下后台进程并继续占用许可证。连接对象因此实现 `close()`、`with`
上下文管理，并在 Demo 的 `finally` 中再次执行幂等关闭。

“幂等关闭”表示 `close()` 调用多次也只执行一次实际关闭，不会因为清理代码重复执行
而产生第二个错误。

## Real / Mock 边界

本次结果来自真实 ZOS-API 调用，不是 Mock。它只证明连接层和资源释放可用，尚未证明：

- 模型能够安全复制和打开；
- LDE 参数能够读取或修改；
- FFT MTF、Spot 等分析能够执行；
- 新 `ZemaxBackend` 已接入 Workflow。

这些能力应在 D60 及后续阶段分别验证，不能由本次连接成功直接推断。
