# D15 参数扫描问题定义

## 今日目标
定义第三周 Zemax 参数扫描任务，为 D16 自动循环修改参数、D17 提取评价指标、D18 绘制性能曲线做准备。

## 选择模型
Cooke 40 degree field.zmx

选择原因：
1. 第二周已经使用该模型完成 ZOS-API 连接、LDE 读取、Thickness 修改、MTF/Spot 导出。
2. 模型较简单，适合作为参数扫描入门对象。
3. Ansys 官方示例中也常使用 Cooke 示例镜头进行 FFT MTF 数据提取和绘图演示。

## 扫描参数
- Editor：LDE
- Surface：3
- Parameter：Thickness
- Unit：mm
- Sweep mode：delta_from_original
- Delta range：-1.0 mm 到 +1.0 mm
- Step：0.25 mm

## 扫描值列表
-1.00, -0.75, -0.50, -0.25, 0.00, 0.25, 0.50, 0.75, 1.00

## 实际厚度计算方式
actual_thickness = original_thickness + delta

D15 Sweep Values
Delta(mm) | Actual Thickness(mm)
----------------------------------------
   -1.00 |         -0.000025433
   -0.75 |          0.249974567
   -0.50 |          0.499974567
   -0.25 |          0.749974567
    0.00 |          0.999974567
    0.25 |          1.249974567
    0.50 |          1.499974567
    0.75 |          1.749974567
    1.00 |          1.999974567

## 评价分析
1. FFT MTF
2. Standard Spot Diagram

## 输出计划
每个扫描点保存：
1. 修改后的 zmx 模型
2. LDE CSV
3. FFT MTF txt
4. Standard Spot txt

D17 再进一步提取：
1. MTF@指定空间频率
2. RMS Spot 或 Spot 相关指标
3. sweep_results.csv

## 注意事项
1. 不覆盖原始 Cooke 示例模型。
2. 每次扫描都应基于原始厚度计算实际厚度，避免连续累加误差。
3. 所有输出保存到 results/D15_sweep_define 或后续 D16/D17 文件夹。
4. 优化前后比较必须保持相同视场、波长、空间频率和分析设置。