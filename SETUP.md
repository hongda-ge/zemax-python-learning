# Project-X 环境恢复

## 1. 环境基线

- Windows 11 64-bit
- Ansys Zemax OpticStudio 2024 R1.03
- Python 3.8.20 64-bit
- Python.NET 2.5.2
- Conda 项目环境：`.conda_zosapi38`

正式环境的完整说明见：
`docs/architecture/D59_environment_baseline.md`。

## 2. 创建项目环境

在项目根目录执行：

```powershell
conda env create --prefix .\.conda_zosapi38 --file environment-zosapi38.yml
```

环境目录不提交 Git；`environment-zosapi38.yml` 是可提交、可复现的环境配方。

## 3. 激活环境

```powershell
conda activate .\.conda_zosapi38
```

激活后确认：

```powershell
python --version
```

预期为：

```text
Python 3.8.20
```

## 4. VS Code

项目工作区已将默认解释器设置为：

```text
${workspaceFolder}\.conda_zosapi38\python.exe
```

第一次打开项目时：

1. 按 `Ctrl+Shift+P`；
2. 运行 `Python: Select Interpreter`；
3. 选择项目内 `.conda_zosapi38\python.exe`；
4. 关闭旧终端并新建终端。

项目内解释器路径不包含 Windows 用户名中的单引号，因此 VS Code 的运行按钮不会再生成无法解析的 PowerShell 命令。

## 5. 环境体检

```powershell
python scripts/validation/D59_check_environment.py
```

全部显示 `PASS` 才表示 Python、依赖和本地 ZOS-API DLL 已准备好。

注意：环境体检不会启动 OpticStudio，也不会检查许可证。真实连接将在 D59 连接 Demo 中单独验证。

## 6. 常见问题

### VS Code 仍显示旧环境

VS Code 会缓存曾经选择过的解释器。重新执行 `Python: Select Interpreter`，并确认终端提示符对应 `.conda_zosapi38`。

### pip 报 SSL 或代理错误

优先使用 `environment-zosapi38.yml` 由 Conda 创建环境。不要为了绕过错误而关闭 SSL 校验或修改系统全局代理。

### ZOS-API DLL 找不到

确认以下文件存在：

```text
L:\Program Files\Zemax2024 R1.03\ZOSAPI_NetHelper.dll
L:\Program Files\Zemax2024 R1.03\ZOSAPI.dll
L:\Program Files\Zemax2024 R1.03\ZOSAPI_Interfaces.dll
```

如果 OpticStudio 安装位置不同，后续应通过项目配置修改路径，不要在多个脚本中分别写死。
