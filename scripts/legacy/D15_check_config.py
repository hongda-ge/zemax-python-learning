from pathlib import Path
import yaml

config_path = Path("configs/config_D15_cooke_thickness.yaml")

print("===== D15 Config Check =====")
print("Config path:", config_path.resolve())

if not config_path.exists():
    raise FileNotFoundError(f"配置文件不存在：{config_path}")

with open(config_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

sweep = config["sweep"]
output_dir = Path(config["outputs"]["output_dir"])
output_dir.mkdir(parents=True, exist_ok=True)

surface_id = sweep["surface_id"]
parameter = sweep["parameter"]
start_delta = float(sweep["start_delta"])
end_delta = float(sweep["end_delta"])
step = float(sweep["step"])

original_thickness = 0.999974567

print("\n===== Basic Info =====")
print("Surface ID:", surface_id)
print("Parameter:", parameter)
print("Original thickness:", original_thickness)
print("Output dir:", output_dir)

print("\n===== Sweep Values =====")
print("Delta(mm) | Actual Thickness(mm)")
print("-" * 42)

delta = start_delta
count = 0

while delta <= end_delta + 1e-9:
    actual_thickness = original_thickness + delta
    print(f"{delta:>8.2f} | {actual_thickness:>20.9f}")
    delta += step
    count += 1

print("\nTotal sweep points:", count)
print("D15 config check finished.")