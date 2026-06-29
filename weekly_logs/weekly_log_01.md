# Weekly Log 01：Zemax 手动基础学习复盘

## 1. 本周完成内容

* 熟悉 Zemax OpticStudio 顺序模式基本界面，包括 LDE、System Explorer、Field、Wavelength、Aperture。
* 打开并分析 Double Gauss 和 Cooke Triplet 官方示例。
* 学习 Layout、Spot Diagram、RMS vs Field、FFT MTF、Ray Fan 等分析图。
* 手动修改 Thickness 和 Radius，观察像面聚焦、Spot 和 MTF 的变化。
* 初步学习 Merit Function、Variable、Operand、Constraint 和局部优化流程。
* 完成 Cooke Triplet 原始、扰动后、优化后 MTF 对比。

## 2. 已掌握的知识点

* EFFL、WFNO、ENPD、TOTR 的基本含义。
* Spot Diagram 用于判断光线是否在像面集中。
* RMS Spot Radius 和 GEO Radius 通常越小越好。
* MTF 越高越好，评价时需要固定空间频率、视场和波长。
* Tangential / Sagittal 分离越大，说明方向性像差越明显。
* Ray Fan 用于分析不同孔径位置光线偏差，曲线越接近 0 越好。
* Merit Function 是优化目标函数，Operand 是其中的单个评价项。
* Variable 决定 Zemax 可以改变哪些参数，Constraint 限制参数不能乱跑。

## 3. 容易混淆的点

* Spot 变形不等于畸变，边缘 Spot 不圆通常是彗差、像散或场曲等离轴像差。
* 畸变主要是像点位置或图像几何比例错误，不一定导致单个点模糊。
* MTF 不能只看中心视场，需要综合边缘视场和 T/S 分离。
* Merit Function 下降只说明系统按当前目标函数变好，不代表所有指标都一定变好。
* RMS 类指标越小越好，MTF 越高越好。

## 4. 本周可展示成果

* Double Gauss 光路图
* Double Gauss Spot Diagram
* Double Gauss FFT MTF
* Double Gauss Ray Fan
* Cooke Triplet 原始 MTF
* Cooke Triplet 修改后 MTF
* Cooke Triplet 优化后 MTF

## 5. 还需要继续加强

* 五种 Seidel 像差和各类分析图之间的对应关系。
* MTF 综合评分方法。
* Merit Function 中不同 Operand 的具体含义。
* 如何从 Zemax 中导出可用于 Python 处理的数据。

## 6. 下周计划：ZOS-API / Python 入门

下周重点从手动操作转向自动化。目标是让 Python 能够连接 Zemax，读取 LDE 参数，修改一个表面参数，并导出 MTF 或 Spot 结果。计划完成 read_lens_data.py、modify_surface.py 和 export_analysis.py 三个基础脚本。
