# D60 安全模型操作层

## 1. 目标

D60 在 D59 真实连接的基础上验证以下链路：

```text
baseline 只读模型
  -> 复制到 outputs
  -> OpticStudio 打开 working copy
  -> 读取 LDE Surface 3
  -> 修改 working copy 的 Thickness
  -> SaveAs 新模型
  -> 重新加载保存文件
  -> 验证 baseline 哈希未改变
```

本阶段不运行 MTF、Spot 或优化，也不评价修改后的光学性能。

## 2. 文件职责

- `modules/zemax/model_ops.py`：可复用的路径保护、复制、哈希、打开、读取、修改和另存函数。
- `scripts/demos/D60_model_operations_demo.py`：真实 ZOS-API 端到端演示。
- `outputs/D60_model_operations/<run_id>/`：每次演示的独立产物目录，不提交 Git。

## 3. Baseline 与 Working Copy

Baseline 是对比实验中的基准设计。它必须保持不变，否则后续所有 before/after
结论都会失去共同参照。

Project-X 当前规定：

```text
models/   = baseline 允许根目录
outputs/  = 可写运行产物根目录
```

`model_ops.py` 使用 `Path.resolve()` 得到规范绝对路径，再用 `relative_to()` 检查
目标是否属于允许根目录。`..` 等路径跳转在解析后无法绕过该检查。

## 4. 为什么使用 SHA-256

SHA-256 是文件内容的数字指纹。复制后，baseline 和 working copy 的哈希必须相同；
任务结束后，baseline 哈希也必须与任务开始前相同。

哈希相同并不说明两个光学系统“性能相似”，而是说明两个文件的二进制内容完全一致。

## 5. LDE 读取

真实测试模型为 `Cooke 40 degree field.zmx`。OpticStudio 返回 8 个 LDE Surface，
其中 Surface 3 的初始数据为：

```text
Radius    = -22.213277182315093 mm
Thickness = 0.999974567 mm
Material  = F2
```

ZOS-API 使用：

```python
surface = system.LDE.GetSurfaceAt(3)
thickness = float(surface.Thickness)
```

Surface 编号必须先与 `NumberOfSurfaces` 比较，防止访问不存在的表面。

## 6. 修改与保存

测试只对 working copy 的 Surface 3 执行：

```text
0.999974567 mm + 0.1 mm = 1.099974567 mm
```

给 `surface.Thickness` 赋值首先改变的是当前 OpticStudio 会话中的内存状态。
只有调用 `SaveAs()` 后，新值才会写入磁盘模型。

为了证明保存有效，Demo 会再次 `LoadFile()` 打开 `modified_model.zmx` 并重新读取
Surface 3。重新读取结果仍为 `1.099974567 mm`，持久化验证通过。

## 7. 真实验证结果

2026-07-22 的本机结果：

```json
{
  "backend": "zemax",
  "simulation_mode": false,
  "status": "success",
  "copy_verified": true,
  "saved_thickness_verified": true,
  "baseline_unchanged": true,
  "connection_closed": true
}
```

Baseline SHA-256 在任务前后均为：

```text
a3f4baa1433f36c7f363bbb1c7721d972854f2ec842e916efc17de2ff9a77585
```

测试后没有残留 OpticStudio 进程。

## 8. 如何运行

环境体检：

```powershell
python scripts/validation/D59_check_environment.py
```

真实 D60 演示：

```powershell
python scripts/demos/D60_model_operations_demo.py --surface 3 --delta-mm 0.1
```

若使用其他模型，先把合法 baseline 放在项目 `models/` 下，再传入：

```powershell
python scripts/demos/D60_model_operations_demo.py --model "models/your_model.zmx"
```

`models/` 中的模型是否适合公开提交应单独审查许可证和来源，D60 不会自动把模型
上传 GitHub。

## 9. 失败保护

以下情况会在写入前被拒绝：

- baseline 不在 `models/`；
- run directory 不在 `outputs/`；
- 文件扩展名不是 `.zmx` 或 `.zos`；
- working copy 或另存目标已经存在；
- Surface 编号超出 LDE 范围；
- Thickness 不是有限数值；
- 复制前后哈希不一致；
- 重新加载的 Thickness 与保存值不一致；
- baseline 任务前后哈希不一致。

## 10. Real / Mock 边界

D60 使用真实 OpticStudio 24.1 SP3 和 ZOS-API，不是 Mock。它已经证明模型复制、
LDE 单表面读取、Thickness 修改、另存和重新加载可用。

它仍未证明 FFT MTF、Spot、Ray Fan 等分析接口可用，也尚未将这些操作接入
`ZemaxBackend` 或 Workflow。分析操作属于 D61。
