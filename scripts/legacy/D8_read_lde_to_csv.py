from win32com.client.gencache import EnsureDispatch, EnsureModule
import csv
from pathlib import Path

# 连接 ZOS-API
TheConnection = EnsureDispatch("ZOSAPI.ZOSAPI_Connection")
TheApplication = TheConnection.ConnectAsExtension(0)

if TheApplication is None:
    raise Exception("无法连接到 OpticStudio，请确认已经打开 编程 → 交互扩展")

print("Connected to OpticStudio")
print("Serial #:", TheApplication.SerialCode)

# 获取当前系统和 LDE
TheSystem = TheApplication.PrimarySystem
TheLDE = TheSystem.LDE

print("\n===== LDE 基本信息 =====")
print("Number of Surfaces:", TheLDE.NumberOfSurfaces)

# 输出 CSV 路径
project_dir = Path(r"C:\Users\20181\Desktop\Zemax\02_zosapi_python")
results_dir = project_dir / "results"
results_dir.mkdir(exist_ok=True)

csv_path = results_dir / "D8_cooke_lde_data.csv"

with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["Surface", "Comment", "Radius", "Thickness", "Material"])

    for i in range(TheLDE.NumberOfSurfaces):
        surf = TheLDE.GetSurfaceAt(i)

        try:
            comment = surf.Comment
        except:
            comment = ""

        try:
            material = surf.Material
        except:
            material = ""

        radius = surf.Radius
        thickness = surf.Thickness

        writer.writerow([i, comment, radius, thickness, material])

        print(
            f"Surface {i}: "
            f"Comment={comment}, "
            f"Radius={radius}, "
            f"Thickness={thickness}, "
            f"Material={material}"
        )

print("\nCSV saved to:")
print(csv_path)