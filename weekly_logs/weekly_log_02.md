# Week 2：ZOS-API / Python 入门

## D8：Python 连接 OpticStudio 并读取 LDE

### 今日完成
- 成功通过 Interactive Extension 连接 Zemax OpticStudio。
- 终端显示 Connected to OpticStudio。
- Python 成功读取当前 Cooke 40 degree field.zmx 示例镜头。
- 读取到 LDE 表面数量：8。
- 成功输出每个表面的 Radius、Thickness、Material。

### 今日截图
- figures/D8_connected_terminal.png
- figures/D8_cooke_lde_read_success.png

### 今日理解
Python 不是直接修改 zmx 文件，而是先连接 OpticStudio，
通过 TheApplication 获取软件对象，
通过 TheSystem 获取当前光学系统，
再通过 TheSystem.LDE 访问 Lens Data Editor。

### 最小连接流程
Python → win32com / ZOS-API → TheApplication → TheSystem → LDE

### 我读到的镜头信息
当前模型：Cooke 40 degree field.zmx  
表面数量：8  
材料包括：SK16、F2  
这说明 Python 已经可以读取 Zemax 镜头数据。

### 明天 D9 目标
跑通一个官方 ZOS-API Python 示例脚本。

## D9：跑通官方/本机 ZOS-API Python 示例

### 今日目标
运行 Zemax 安装目录或本机生成的 Python 示例，记录报错和解决方法，至少跑通一个示例脚本。

### 今日环境
- Zemax OpticStudio：19.4
- Python 虚拟环境：.venv_zosapi38
- Python 版本：3.8.10
- 项目路径：C:\Users\20181\Desktop\Zemax\02_zosapi_python

### 今日完成
1. 尝试运行官方 Standalone 示例 D9_official_sample_01.py。
2. 脚本输出 open error。
3. 通过添加 STEP 0 / STEP 1 定位，确认错误发生在创建 PythonStandaloneApplication 阶段。
4. 检查任务管理器/PowerShell，未发现残留 Zemax / OpticStudio / ZOS 后台进程。
5. 尝试生成 Zemax 19.4 本机 Python → 独立应用程序模板。
6. 本机模板成功运行，终端输出 Standalone application created、License type、Serial、SamplesDir、Number of surfaces。
7. 确认 COM / pywin32 路线可用，后续脚本优先基于 D9_local_standalone_template.py 修改。

### 问题分析
原官方示例失败不等于 ZOS-API 不能用。更可能是官方示例代码与本机 Zemax 19.4 环境不完全匹配：
- 官方示例使用 Python.NET / clr / ZOSAPI_NetHelper 路线；
- 本机生成模板使用 win32com / pywin32 / COM 路线；
- 本机模板成功说明授权、ZOS-API 连接和 Standalone 创建都可用；
- 官方示例还包含 .zos 文件保存路径，而 .zos 格式是较新版本 OpticStudio 引入的，对 19.4 不适合。

### 今日结论
D9 已完成。至少跑通了一个本机生成的 ZOS-API Standalone Python 示例脚本。
后续 D10、D11、D12 不再直接使用失败的官方示例，而是基于 D9_local_standalone_template.py 或备份的 zosapi_standalone_base.py 开发。

### 今日保留文件
- scripts/D9_local_standalone_template.py
- scripts/zosapi_standalone_base.py
- figures/D9_local_standalone_success.png
- notes/D9_error_log.md

## D10：读取模型参数

### 今日目标
基于 D9 成功的 Standalone 模板，写 read_lens_data.py，读取 Cooke 示例镜头的系统信息和 LDE 表面参数。

### 今日完成
- 成功使用 Standalone 模式启动 OpticStudio。
- 使用 TheSystem.LoadFile 打开 Cooke 40 degree field.zmx。
- 使用 TheSystem.LDE 获取 Lens Data Editor。
- 成功读取 LDE 表面数量。
- 逐行输出每个 Surface 的 Radius、Thickness、Material、Comment。
- 成功导出 CSV 文件：results/D10_cooke_lde_data.csv。

### 今日理解
TheApplication 代表 OpticStudio 软件本身；
TheSystem 代表当前打开的光学系统；
TheSystem.LDE 代表 Lens Data Editor；
TheLDE.GetSurfaceAt(i) 可以访问第 i 个表面；
surf.Radius、surf.Thickness、surf.Material 分别对应 LDE 中的曲率半径、厚度和材料。

### 今日产物
- scripts/D10_read_lens_data.py
- scripts/read_lens_data.py
- results/D10_cooke_lde_data.csv
- figures/D10_read_lens_success.png

### 明天 D11 目标
在 D10 基础上修改一个表面参数，例如修改 Surface 6 的 Thickness 或 Radius，并保存为新模型。


# D12 运行分析并导出结果

## 今日目标
使用 Python/ZOS-API 自动调用 Zemax 分析窗口，导出 FFT MTF 和 Standard Spot Diagram 的分析结果。

## 使用模型
- 原始模型：Cooke 40 degree field.zmx
- 运行方式：Standalone Application
- API 路线：pywin32 / COM

## 今日修改
- 获取 TheSystem.LDE
- 读取表面数量和 LDE 参数
- 保存的模型：D12_cooke_surface3_thickness_plus1.zmx

## 今日导出结果
- fft_mtf.txt
- standard_spot.txt
- D12_cooke_lde_after_modify.csv
- 可选：fft_mtf_from_txt.png

## 今日理解
1. 修改 LDE 参数要放在 LoadFile 之后、运行分析之前。
2. MTF、Spot 这类分析属于 TheSystem.Analyses，不属于 LDE。
3. 分析导出代码要放在模型状态确定之后、del zosapi 关闭 Zemax 之前。
4. ZOS-API 分析的基本流程是：New_Analysis → ApplyAndWaitForCompletion → GetResults → GetTextFile → Close。

## 今日验收
- [√] 脚本可以正常启动 Zemax
- [√] 可以打开 Cooke 示例镜头
- [√] 可以修改 Surface 3 厚度
- [√] 可以保存修改后的 zmx 模型
- [√] 可以导出 fft_mtf.txt
- [√] 可以导出 standard_spot.txt
- [√] 输出文件不为 0 KB
- [√] 记录了输出路径和遇到的问题

## 遇到的问题
1.在使用代码修改、获取不同信息时，要遵循的规则：所有“改变模型”的代码，放在打开镜头之后、运行分析之前；所有“导出结果”的代码，放在模型状态确定之后、关闭 Zemax 之前。

## 明天 D13 第一件事
把今天的连接、打开模型、修改参数、导出 MTF/Spot 的代码封装成函数：
- connect_zemax()
- open_lens()
- modify_surface_thickness()
- export_fft_mtf()
- export_standard_spot()

## D13 封装函数

### 今日目标
将 D10-D12 中已经跑通的连接 Zemax、打开镜头、读取/修改 LDE、保存模型、导出 MTF 和 Spot 的流程封装为可重复调用的函数。

### 今日新增/使用文件
- scripts/zemax_runner.py
- scripts/D13_test_runner.py

### 今日输出结果
- results/D13_runner_test/D13_lde_before_modify.csv
- results/D13_runner_test/D13_lde_after_modify.csv
- results/D13_runner_test/D13_cooke_surface3_thickness_plus1.zmx
- results/D13_runner_test/D13_cooke_surface3_thickness_plus1.ZDA
- results/D13_runner_test/D13_fft_mtf.txt
- results/D13_runner_test/D13_standard_spot.txt

### 今日结果
D13_test_runner.py 成功调用 zemax_runner.py 中的函数，完成了打开 Cooke 示例镜头、修改 Surface 3 厚度、导出修改前后 LDE、保存修改后模型、导出 FFT MTF 和 Standard Spot Diagram。

### 今日理解
1. zemax_runner.py 相当于工具箱，负责存放可复用函数。
2. D13_test_runner.py 是测试脚本，负责调用工具箱里的函数。
3. D13 的意义不是新增分析类型，而是把 D12 的流程模块化。
4. 后续参数扫描可以基于这些函数循环运行。

### 遇到的问题
暂无，脚本成功运行并生成结果文件。

### 下一步
D14 整理第 2 周 API 操作清单，准备“Python 控制 Zemax 入门报告”。

## 第 2 周总结：ZOS-API / Python 入门

### 本周完成

1. 成功使用 Python 连接 Zemax OpticStudio。
2. 成功打开 Cooke 40 degree field.zmx 示例镜头。
3. 成功读取 LDE 表面参数，并导出 CSV。
4. 成功修改 Surface 3 的 Thickness。
5. 成功保存修改后的 zmx 模型。
6. 成功调用 FFT MTF 分析并导出 txt。
7. 成功调用 Standard Spot Diagram 分析并导出 txt。
8. 成功将连接、打开、修改、导出等流程封装为 zemax_runner.py。

### 本周可展示成果

- 脚本：scripts/zemax_runner.py
- 测试脚本：scripts/D13_test_runner.py
- 模型：results/D13_runner_test/D13_cooke_surface3_thickness_plus1.zmx
- 数据：D13_lde_before_modify.csv、D13_lde_after_modify.csv
- 分析结果：D13_fft_mtf.txt、D13_standard_spot.txt
- 截图：D13_runner_success_terminal.png、D13_runner_output_files.png

### 本周最重要的理解

- TheSystem 是操作 Zemax 当前系统的核心入口。
- LDE 负责镜头结构参数，Analysis 负责 MTF、Spot 等分析结果。
- 修改参数要在分析前完成。
- 导出结果要在关闭 Zemax 前完成。
- 函数封装是后续参数扫描和自动化优化的基础。

### 是否达到验收标准

是。已经实现 Python 连接 Zemax、读取/修改 LDE 参数、保存模型，并自动导出 MTF 和 Spot 分析结果。