# D59 环境基线

## 目标

为 Project-X 建立一套独立、可复现、可验证的 ZOS-API Python 环境。

## 正式基线

| 项目 | 固定值 |
|---|---|
| 操作系统 | Windows 11 64-bit |
| Python | 3.8.20 64-bit |
| 环境目录 | `.conda_zosapi38` |
| Python.NET | 2.5.2 |
| OpticStudio | 2024 R1.03 |
| ZOS-API 方式 | Python.NET / Standalone |

Python 3.8 是当前项目的真实 Zemax 基线。`optical_auto` 的 Python 3.10
环境保留为实验环境，不作为真实 ZOS-API 结果的默认运行环境。

## 为什么固定环境

Python 脚本运行时不仅依赖脚本内容，还依赖 Python 版本、第三方包、
.NET 运行库和 Zemax DLL。固定环境是为了保证同一个 commit 在不同日期、
不同终端或新电脑上尽可能得到一致行为。

环境目录本身不提交 Git；Git 只保存 `environment-zosapi38.yml` 这份环境配方。

## 创建环境

在项目根目录执行：

```powershell
conda env create --prefix .\.conda_zosapi38 --file environment-zosapi38.yml
```

如果环境已经存在，不要重复创建。先运行环境检查脚本确认状态。

## VS Code

工作区 `.vscode/settings.json` 指向：

```text
${workspaceFolder}\.conda_zosapi38\python.exe
```

打开项目后执行 `Python: Select Interpreter`，确认选择同一路径；然后新建终端，
不要继续使用在修改解释器之前已经打开的旧终端。

## 验证

```powershell
conda run --prefix .\.conda_zosapi38 python scripts/validation/D59_check_environment.py
```

这个检查不会启动 OpticStudio，也不会占用许可证。只有所有项目显示 `PASS`，
才进入下一步真实连接测试。

## Real / Mock 边界

环境检查成功只证明 Python、依赖和 DLL 文件准备就绪，不证明 ZOS-API 已经成功
连接，也不证明许可证有效。真实连接和安全关闭将在 D59 连接 Demo 中单独验证。
