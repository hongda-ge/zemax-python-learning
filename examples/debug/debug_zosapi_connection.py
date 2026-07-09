import traceback
import sys

print("DEBUG FILE:", __file__)
print("Python executable:", sys.executable)
print("Python version:", sys.version)

try:
    import PythonStandalone_01_new_file_and_quickfocus as sample
    print("Imported sample file:", sample.__file__)

    print("Step 1: create PythonStandaloneApplication")
    zos = sample.PythonStandaloneApplication()
    print("Step 2: connection created successfully")

    app = zos.TheApplication
    system = zos.TheSystem

    print("IsValidLicenseForAPI:", app.IsValidLicenseForAPI)
    print("LicenseStatus:", app.LicenseStatus)
    print("SamplesDir:", app.SamplesDir)
    print("TheSystem:", system)

    print("ZOS-API connection test PASSED")

    del zos

except BaseException as e:
    print("ZOS-API connection test FAILED")
    print("Error type:", type(e))
    print("Error args:", getattr(e, "args", None))
    print("Error message:", e)
    print("Full traceback:")
    traceback.print_exc()