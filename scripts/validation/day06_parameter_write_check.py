
from pathlib import Path

from modules.zemax.connection import StandaloneZemaxConnection
from modules.zemax.model_ops import sha256_file


ROOT = Path(__file__).resolve().parents[2]
MODEL = (
    ROOT / "models" / "baselines"
    / "Day06_BEST_850Astig.zos"
)


def main():
    print("=== Day06 Parameter Write Check ===")

    hash_before = sha256_file(MODEL)

    with StandaloneZemaxConnection() as conn:
        system = conn.system
        system.LoadFile(str(MODEL), False)

        surface9 = system.LDE.GetSurfaceAt(9)
        surface10 = system.LDE.GetSurfaceAt(10)

        # 记录BEST原始参数
        k9_original = float(surface9.Conic)
        r10_original = float(surface10.Radius)

        print("\nOriginal parameters:")
        print(f"k9  = {k9_original:.6f}")
        print(f"R10 = {r10_original:.6f} mm")

        # 在内存中测试参数写入
        try:
            surface9.Conic = -0.34416
            surface10.Radius = 6.184721

            k9_actual = float(surface9.Conic)
            r10_actual = float(surface10.Radius)

            print("\nModified parameters:")
            print(f"k9  = {k9_actual:.6f}")
            print(f"R10 = {r10_actual:.6f} mm")

            assert abs(k9_actual + 0.34416) < 1e-6
            assert abs(r10_actual - 6.184721) < 1e-6

            print("\nPARAMETER WRITE PASSED")

        finally:
            # 无论测试成功与否，都尝试恢复内存参数
            surface9.Conic = k9_original
            surface10.Radius = r10_original

            print("\nRestored parameters:")
            print(f"k9  = {float(surface9.Conic):.6f}")
            print(f"R10 = {float(surface10.Radius):.6f}")

        # 不调用Save或SaveAs

    assert sha256_file(MODEL) == hash_before
    print("\nSource model unchanged: True")


if __name__ == "__main__":
    main()
