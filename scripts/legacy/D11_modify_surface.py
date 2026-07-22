from win32com.client.gencache import EnsureDispatch, EnsureModule
from win32com.client import CastTo, constants
from win32com.client import gencache

# Notes
#
# The python project and script was tested with the following tools:
#       Python 3.4.3 for Windows (32-bit) (https://www.python.org/downloads/) - Python interpreter
#       Python for Windows Extensions (32-bit, Python 3.4) (http://sourceforge.net/projects/pywin32/) - for COM support
#       Microsoft Visual Studio Express 2013 for Windows Desktop (https://www.visualstudio.com/en-us/products/visual-studio-express-vs.aspx) - easy-to-use IDE
#       Python Tools for Visual Studio (https://pytools.codeplex.com/) - integration into Visual Studio
#
# Note that Visual Studio and Python Tools make development easier, however this python script should should run without either installed.

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
        # make sure the Python wrappers are available for the COM client and
        # interfaces
        gencache.EnsureModule('{EA433010-2BAC-43C4-857C-7AEAC4A8CCE0}', 0, 1, 0)
        gencache.EnsureModule('{F66684D7-AAFE-4A62-9156-FF7A7853F764}', 0, 1, 0)
        # Note - the above can also be accomplished using 'makepy.py' in the
        # following directory:
        #      {PythonEnv}\Lib\site-packages\win32com\client\
        # Also note that the generate wrappers do not get refreshed when the
        # COM library changes.
        # To refresh the wrappers, you can manually delete everything in the
        # cache directory:
        #	   {PythonEnv}\Lib\site-packages\win32com\gen_py\*.*
        
        self.TheConnection = EnsureDispatch("ZOSAPI.ZOSAPI_Connection")
        if self.TheConnection is None:
            raise PythonStandaloneApplication.ConnectionException("Unable to intialize COM connection to ZOSAPI")

        self.TheApplication = self.TheConnection.CreateNewApplication()
        if self.TheApplication is None:
            raise PythonStandaloneApplication.InitializationException("Unable to acquire ZOSAPI application")

        if self.TheApplication.IsValidLicenseForAPI == False:
            raise PythonStandaloneApplication.LicenseException("License is not valid for ZOSAPI use")

        self.TheSystem = self.TheApplication.PrimarySystem
        if self.TheSystem is None:
            raise PythonStandaloneApplication.SystemNotPresentException("Unable to acquire Primary system")

    def __del__(self):
        if self.TheApplication is not None:
            self.TheApplication.CloseApplication()
            self.TheApplication = None

        self.TheConnection = None

    def OpenFile(self, filepath, saveIfNeeded):
        if self.TheSystem is None:
            raise PythonStandaloneApplication.SystemNotPresentException("Unable to acquire Primary system")
        self.TheSystem.LoadFile(filepath, saveIfNeeded)

    def CloseFile(self, save):
        if self.TheSystem is None:
            raise PythonStandaloneApplication.SystemNotPresentException("Unable to acquire Primary system")
        self.TheSystem.Close(save)

    def SamplesDir(self):
        if self.TheApplication is None:
            raise PythonStandaloneApplication.InitializationException("Unable to acquire ZOSAPI application")

        return self.TheApplication.SamplesDir

    def ExampleConstants(self):
        if self.TheApplication.LicenseStatus is constants.LicenseStatusType_PremiumEdition:
            return "Premium"
        elif self.TheApplication.LicenseStatus is constants.LicenseStatusType_ProfessionalEdition:
            return "Professional"
        elif self.TheApplication.LicenseStatus is constants.LicenseStatusType_StandardEdition:
            return "Standard"
        else:
            return "Invalid"


if __name__ == '__main__':
    print("STEP 0: script started", flush=True)

    # 1. 启动 Standalone OpticStudio
    zosapi = PythonStandaloneApplication()
    print("STEP 1: Standalone application created", flush=True)

    TheApplication = zosapi.TheApplication
    TheSystem = zosapi.TheSystem

    print("Connected to OpticStudio", flush=True)
    print("Serial #:", TheApplication.SerialCode, flush=True)
    print("SamplesDir:", TheApplication.SamplesDir, flush=True)

    # 2. 打开 Cooke 示例镜头
    cooke_file = r"models\Cooke 40 degree field.zmx"
    print("\nSTEP 2: loading lens file", flush=True)
    print("Lens file:", cooke_file, flush=True)

    TheSystem.LoadFile(cooke_file, False)
    print("STEP 3: lens file loaded", flush=True)

    # 3. 获取 LDE
    TheLDE = TheSystem.LDE
    n_surfaces = TheLDE.NumberOfSurfaces

    # ===== D11：修改指定表面的 Thickness =====
    target_surface = 3          # 要修改的表面编号，先用 Surface 3 练习
    delta_thickness = 1.0       # 厚度增加 1 mm

    target_surf = TheLDE.GetSurfaceAt(target_surface)

    old_thickness = target_surf.Thickness
    new_thickness = old_thickness + delta_thickness

    print("\n===== D11 Modify Surface =====")
    print("Target surface:", target_surface)
    print("Old thickness:", old_thickness)

    target_surf.Thickness = new_thickness

    print("New thickness:", target_surf.Thickness)
    print("Thickness has been modified.")

    print("\n===== System Information =====")
    print("Number of surfaces:", n_surfaces)

    print("\n===== LDE Surface Data =====")
    print("Surface | Radius | Thickness | Material | Comment")
    print("-" * 80)

    import csv

    csv_path = r"results\D11_cooke_lde_after_modify.csv"
    csv_file = open(csv_path, "w", newline="", encoding="utf-8-sig")
    writer = csv.writer(csv_file)
    writer.writerow(["Surface", "Radius", "Thickness", "Material", "Comment"])

    # 4. 逐个读取表面参数
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

        print(f"{i:>7} | {radius!s:<15} | {thickness!s:<15} | {material!s:<10} | {comment}")
        
        writer.writerow([i, radius, thickness, material, comment])


    # 5. 关闭后台 OpticStudio
    
    csv_file.close()
    print("\nCSV saved to:", csv_path)

    # 6. 保存修改后的 Zemax 模型，不覆盖原始文件
    save_path = r"results\D11_cooke_surface3_thickness_plus1.zmx"
    TheSystem.SaveAs(save_path)

    print("\nModified Zemax file saved to:", save_path)

    del zosapi
    zosapi = None

    print("\nSTEP 4: script finished", flush=True)



