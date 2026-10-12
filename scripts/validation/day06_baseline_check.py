
from pathlib import Path

from modules.zemax.connection import StandaloneZemaxConnection
from modules.zemax.model_ops import sha256_file


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_FILE = (
    PROJECT_ROOT
    / "models"
    / "baselines"
    / "Day06_BEST_850Astig.zos"
)


def main():
    print("=== Day06 Double Gauss Baseline Check ===")

    if not MODEL_FILE.is_file():
        raise FileNotFoundError(MODEL_FILE)

    original_hash = sha256_file(MODEL_FILE)

    with StandaloneZemaxConnection() as connection:
        system = connection.system

        # 只打开镜头，不修改或保存
        system.LoadFile(str(MODEL_FILE), False)

        lde = system.LDE
        print("Surface count:", lde.NumberOfSurfaces)

        # 读取三个关键结构参数
        k7 = lde.GetSurfaceAt(7).Conic
        k9 = lde.GetSurfaceAt(9).Conic
        r10 = lde.GetSurfaceAt(10).Radius

        print("\n--- Key Parameters ---")
        print(f"k7  = {k7:.6f}")
        print(f"k9  = {k9:.6f}")
        print(f"R10 = {r10:.6f} mm")

        # 读取视场
        fields = system.SystemData.Fields
        print("\n--- Fields ---")

        for i in range(1, fields.NumberOfFields + 1):
            field = fields.GetField(i)
            print(
                f"Field {i}: Y={field.Y:.3f} deg, "
                f"Weight={field.Weight:.2f}"
            )

        # 读取波长
        waves = system.SystemData.Wavelengths
        print("\n--- Wavelengths ---")

        for i in range(1, waves.NumberOfWavelengths + 1):
            wave = waves.GetWavelength(i)
            print(
                f"Wave {i}: {wave.Wavelength:.4f} um"
            )

        # 检查BEST关键参数
        assert abs(k7 - 0.27900) < 0.0001
        assert abs(k9 - (-0.33416)) < 0.0001
        assert abs(r10 - 6.19472) < 0.0001

        assert fields.NumberOfFields == 7
        assert waves.NumberOfWavelengths == 4

    # 确认文件没有被修改
    assert sha256_file(MODEL_FILE) == original_hash

    print("\nBASELINE CHECK PASSED")


if __name__ == "__main__":
    main()
