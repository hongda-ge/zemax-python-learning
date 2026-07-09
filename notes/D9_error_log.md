# D9 错误记录：官方 Standalone 示例 open error

## 报错现象
运行 scripts/D9_official_sample_01.py 时，终端输出：

open error

## 定位过程
在 main 入口处加入：

STEP 0: script started
STEP 1: before creating Standalone application

运行后输出：

STEP 0: script started
STEP 1: before creating Standalone application
open error

说明错误发生在 PythonStandaloneApplication() 创建阶段，还没有进入 SaveAs、LDE 设置、QuickFocus 等后续操作。

## 已排查
- Python 虚拟环境可用；
- pywin32 已安装；
- 无 Zemax / OpticStudio / ZOS 残留后台进程；
- Cooke 示例文件存在；
- results 文件夹已创建；
- 但原官方示例仍然 open error。

## 原因判断
不是 Python 完全不能连接 Zemax，而是该官方示例与当前 Zemax 19.4 环境不完全匹配。
该官方示例使用 Python.NET / clr / ZOSAPI_NetHelper 路线；
而本机 Zemax 19.4 生成的 Standalone 模板使用 win32com / COM 路线，能够成功运行。

## 解决方法
使用 Zemax 19.4 本机生成的 Python Standalone 模板。
该模板成功创建 Standalone OpticStudio 实例，并输出 License、Serial、SamplesDir 和 LDE 表面数量。

## 后续策略
后续脚本以本机模板为基础开发：
- D10_read_lens_data.py
- D11_modify_surface.py
- D12_export_analysis.py