from pathlib import Path

# ===== D15 dry-run：不调用 Zemax，只检查扫描点 =====

project_dir = Path(r"C:\Users\20181\Desktop\Zemax\02_zosapi_python")

output_dir = project_dir / "results" / "D15_sweep_define"
output_dir.mkdir(parents=True, exist_ok=True)

# 你 D13 终端里显示的 Surface 3 原始厚度
original_thickness = 0.999974567

surface_id = 3
parameter = "Thickness"
unit = "mm"

start_delta = -1.0
end_delta = 1.0
step = 0.25

print("===== D15 Sweep Dry Run =====")
print("Surface ID:", surface_id)
print("Parameter:", parameter)
print("Unit:", unit)
print("Original thickness:", original_thickness)
print("Output dir:", output_dir)

print("\nDelta(mm) | Actual Thickness(mm)")
print("-" * 42)

delta = start_delta
count = 0

while delta <= end_delta + 1e-9:
    actual_thickness = original_thickness + delta
    print(f"{delta:>8.2f} | {actual_thickness:>20.9f}")

    delta += step
    count += 1

print("\nTotal sweep points:", count)
print("D15 dry-run finished.")