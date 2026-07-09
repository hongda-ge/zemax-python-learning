from pathlib import Path
import csv

from win32com.client.gencache import EnsureDispatch
from win32com.client import constants
from win32com.client import gencache


class PythonStandaloneApplication(object):
    class LicenseException(Exception):
        pass

    class ConnectionException(Exception):
        pass

    class InitializationException(Exception):
        pass

    class SystemNotPresentException(Exception):
        pass

    def __init__(self):
        gencache.EnsureModule('{EA433010-2BAC-43C4-857C-7AEAC4A8CCE0}', 0, 1, 0)
        gencache.EnsureModule('{F66684D7-AAFE-4A62-9156-FF7A7853F764}', 0, 1, 0)

        self.TheConnection = EnsureDispatch("ZOSAPI.ZOSAPI_Connection")
        if self.TheConnection is None:
            raise PythonStandaloneApplication.ConnectionException(
                "Unable to initialize COM connection to ZOSAPI"
            )

        self.TheApplication = self.TheConnection.CreateNewApplication()
        if self.TheApplication is None:
            raise PythonStandaloneApplication.InitializationException(
                "Unable to acquire ZOSAPI application"
            )

        if self.TheApplication.IsValidLicenseForAPI == False:
            raise PythonStandaloneApplication.LicenseException(
                "License is not valid for ZOSAPI use"
            )

        self.TheSystem = self.TheApplication.PrimarySystem
        if self.TheSystem is None:
            raise PythonStandaloneApplication.SystemNotPresentException(
                "Unable to acquire Primary system"
            )

    def __del__(self):
        if self.TheApplication is not None:
            self.TheApplication.CloseApplication()
            self.TheApplication = None

        self.TheConnection = None


def connect_zemax():
    """
    启动 Standalone Zemax，并返回 zosapi, TheApplication, TheSystem。
    """
    zosapi = PythonStandaloneApplication()
    TheApplication = zosapi.TheApplication
    TheSystem = zosapi.TheSystem

    print("Connected to OpticStudio")
    print("Serial #:", TheApplication.SerialCode)
    print("SamplesDir:", TheApplication.SamplesDir)

    return zosapi, TheApplication, TheSystem


def make_output_dir(out_dir):
    """
    创建输出文件夹。
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def open_lens(TheSystem, lens_path):
    """
    打开 Zemax 镜头文件。
    """
    lens_path = str(lens_path)
    print("Loading lens file:", lens_path)
    TheSystem.LoadFile(lens_path, False)
    print("Lens file loaded.")


def export_lde_csv(TheSystem, csv_path):
    """
    导出当前 LDE 表面数据到 CSV。
    """
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    TheLDE = TheSystem.LDE
    n_surfaces = TheLDE.NumberOfSurfaces

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Surface", "Radius", "Thickness", "Material", "Comment"])

        for i in range(n_surfaces):
            surf = TheLDE.GetSurfaceAt(i)

            try:
                radius = surf.Radius
            except Exception:
                radius = ""

            try:
                thickness = surf.Thickness
            except Exception:
                thickness = ""

            try:
                material = surf.Material
            except Exception:
                material = ""

            try:
                comment = surf.Comment
            except Exception:
                comment = ""

            writer.writerow([i, radius, thickness, material, comment])

    print("LDE CSV saved to:", csv_path)


def modify_surface_thickness(TheSystem, surface_id, delta_thickness):
    """
    修改指定表面的 Thickness。
    surface_id：表面编号
    delta_thickness：厚度增加量，单位一般是 mm
    """
    TheLDE = TheSystem.LDE
    surf = TheLDE.GetSurfaceAt(surface_id)

    old_thickness = surf.Thickness
    new_thickness = old_thickness + delta_thickness
    surf.Thickness = new_thickness

    print("Surface:", surface_id)
    print("Old thickness:", old_thickness)
    print("New thickness:", surf.Thickness)

    return old_thickness, surf.Thickness

def set_surface_thickness(TheSystem, surface_id, new_thickness):
    """
    将指定表面的 Thickness 设置为某个绝对值。

    注意：
    - modify_surface_thickness 是“在当前基础上增加 delta”
    - set_surface_thickness 是“直接设置成 new_thickness”
    - 参数扫描时建议使用 set_surface_thickness，避免连续累加误差
    """
    TheLDE = TheSystem.LDE
    surf = TheLDE.GetSurfaceAt(surface_id)

    old_thickness = surf.Thickness
    surf.Thickness = float(new_thickness)

    print(f"Surface {surface_id} thickness: {old_thickness} -> {surf.Thickness}")

    return old_thickness, surf.Thickness


def save_lens(TheSystem, save_path):
    """
    保存当前 Zemax 模型。
    """
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    TheSystem.SaveAs(str(save_path))
    print("Lens saved to:", save_path)


def export_fft_mtf(TheSystem, out_dir, filename="fft_mtf.txt"):
    """
    运行 FFT MTF 分析，并导出 txt。
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    mtf = TheSystem.Analyses.New_Analysis(constants.AnalysisIDM_FftMtf)
    mtf.ApplyAndWaitForCompletion()

    mtf_results = mtf.GetResults()

    mtf_txt_path = out_dir / filename
    mtf_results.GetTextFile(str(mtf_txt_path))

    mtf.Close()

    print("FFT MTF saved to:", mtf_txt_path)
    return mtf_txt_path


def export_standard_spot(TheSystem, out_dir, filename="standard_spot.txt"):
    """
    运行 Standard Spot Diagram 分析，并导出 txt。
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    spot = TheSystem.Analyses.New_Analysis(constants.AnalysisIDM_StandardSpot)
    spot.ApplyAndWaitForCompletion()

    spot_results = spot.GetResults()

    spot_txt_path = out_dir / filename
    spot_results.GetTextFile(str(spot_txt_path))

    spot.Close()

    print("Standard Spot saved to:", spot_txt_path)
    return spot_txt_path