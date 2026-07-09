# D14 ZOS-API 操作清单

## 1. 连接 Zemax
- 使用 Standalone Application 启动 OpticStudio
- 获取 TheApplication
- 获取 TheSystem

对应函数：
- connect_zemax()

## 2. 打开镜头文件
- 使用 TheSystem.LoadFile() 打开 Cooke 40 degree field.zmx
- 使用示例镜头作为 API 自动化练习对象

对应函数：
- open_lens(TheSystem, lens_path)

## 3. 读取 LDE 数据
- 获取 TheSystem.LDE
- 读取 NumberOfSurfaces
- 读取每个 Surface 的 Radius、Thickness、Material、Comment
- 导出为 CSV 文件

对应函数：
- export_lde_csv(TheSystem, csv_path)

## 4. 修改 LDE 参数
- 选择 Surface 3
- 修改 Thickness
- 修改前后分别导出 LDE CSV 进行验证

对应函数：
- modify_surface_thickness(TheSystem, surface_id, delta_thickness)

## 5. 保存修改后的镜头模型
- 使用 TheSystem.SaveAs() 保存新的 zmx 文件
- 不覆盖原始 Cooke 示例镜头

对应函数：
- save_lens(TheSystem, save_path)

## 6. 运行并导出 MTF
- 新建 FFT MTF 分析
- 运行分析
- 获取结果
- 导出 fft_mtf.txt

对应函数：
- export_fft_mtf(TheSystem, out_dir, filename)

## 7. 运行并导出 Spot Diagram
- 新建 Standard Spot Diagram 分析
- 运行分析
- 获取结果
- 导出 standard_spot.txt

对应函数：
- export_standard_spot(TheSystem, out_dir, filename)

## 8. 当前理解
- LDE 是镜头结构输入。
- MTF、Spot 属于分析结果输出。
- 修改参数要放在分析前。
- 导出结果要放在关闭 Zemax 前。
- 封装函数的意义是为后续参数扫描做准备。