# Zemax Python 环境恢复

## 1. 安装软件

- Zemax OpticStudio 19.4
- Python 3.8
- VS Code

---

## 2. 创建虚拟环境

python -m venv .venv_zosapi38

---

## 3. 激活环境

PowerShell

.\.venv_zosapi38\Scripts\Activate.ps1

CMD

.\.venv_zosapi38\Scripts\activate.bat

---

## 4. 安装依赖

pip install -r requirements.txt

---

## 5. 测试 Python

python --version

应输出：

Python 3.8.x

---

## 6. 测试 ZOS-API

python examples/debug_zosapi_connection.py

如果输出：

ZOS-API connection test PASSED

说明环境恢复完成。

---

## 7. 注意事项

如果 pip 下载失败：

关闭 Clash 后安装。

如果 PowerShell 无法激活：

Set-ExecutionPolicy -Scope Process Bypass