# Python 控制 Zemax 入门阶段报告

## 1. 学习目标

本阶段目标是初步掌握 Python/ZOS-API 控制 Zemax OpticStudio 的基本流程，包括连接软件、打开示例镜头、读取镜头参数、修改 LDE 表面参数、运行 MTF/Spot 分析并导出结果。

## 2. 实验环境

- 软件：Ansys Zemax OpticStudio
- API：ZOS-API
- 编程语言：Python
- 调用方式：Standalone Application
- 示例模型：Cooke 40 degree field.zmx

## 3. 已完成内容

### 3.1 连接 OpticStudio

通过 Python 脚本启动 Standalone OpticStudio，获取 TheApplication 和 TheSystem，确认 Python 可以与 Zemax 建立通信。

### 3.2 读取 LDE 参数

读取 Cooke 示例镜头的 LDE 数据，包括表面编号、曲率半径、厚度、材料和备注信息，并导出为 CSV 文件，便于后续检查和数据记录。

### 3.3 修改镜头参数

选取 Surface 3 作为测试对象，对其 Thickness 增加 1.0 mm，并通过修改前后 LDE CSV 对比确认参数变化。

### 3.4 保存修改后的模型

将修改后的镜头另存为新的 zmx 文件，避免覆盖原始示例模型，保证实验可追溯。

### 3.5 自动运行分析并导出结果

使用 Python/ZOS-API 自动调用 FFT MTF 和 Standard Spot Diagram 分析，并导出 txt 结果文件。其中 MTF 用于评价系统细节传递能力，Spot Diagram 用于观察像面光斑分布和成像集中程度。

### 3.6 封装函数

将连接 Zemax、打开镜头、导出 LDE、修改表面厚度、保存模型、导出 MTF 和导出 Spot Diagram 等流程封装到 zemax_runner.py 中，并通过 D13_test_runner.py 完成调用测试。

## 4. 输出文件

- modules/zemax_runner.py
- scripts/legacy/D13_test_runner.py
- results/D13_runner_test/D13_lde_before_modify.csv
- results/D13_runner_test/D13_lde_after_modify.csv
- results/D13_runner_test/D13_cooke_surface3_thickness_plus1.zmx
- results/D13_runner_test/D13_fft_mtf.txt
- results/D13_runner_test/D13_standard_spot.txt

## 5. 当前收获

通过本阶段学习，我理解了 ZOS-API 自动化的基本逻辑：先通过 Python 建立与 OpticStudio 的连接，再基于 TheSystem 操作镜头文件、LDE 和分析窗口。相比手动操作，脚本化流程可以重复执行，为后续参数扫描、批量分析和自动化优化打下基础。

## 6. 下一步计划

下一阶段将基于已封装的函数进行参数扫描，例如循环修改某一表面厚度，批量导出 MTF/Spot 结果，并进一步提取评价指标写入 CSV，形成参数-性能曲线。