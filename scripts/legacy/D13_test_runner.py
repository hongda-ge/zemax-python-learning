from pathlib import Path

from zemax_runner import (
    connect_zemax,
    make_output_dir,
    open_lens,
    export_lde_csv,
    modify_surface_thickness,
    save_lens,
    export_fft_mtf,
    export_standard_spot,
)


if __name__ == "__main__":
    print("===== D13 Test Runner Started =====")

    # 1. 路径设置
    project_dir = Path(r"C:\Users\20181\Desktop\Zemax\02_zosapi_python")

    lens_file = r"C:\Users\20181\Documents\Zemax\Samples\Sequential\Objectives\Cooke 40 degree field.zmx"

    out_dir = make_output_dir(project_dir / "results" / "D13_runner_test")

    # 2. 连接 Zemax
    zosapi, TheApplication, TheSystem = connect_zemax()

    # 3. 打开镜头
    open_lens(TheSystem, lens_file)

    # 4. 导出修改前 LDE
    export_lde_csv(
        TheSystem,
        out_dir / "D13_lde_before_modify.csv"
    )

    # 5. 修改 Surface 3 厚度
    modify_surface_thickness(
        TheSystem,
        surface_id=3,
        delta_thickness=1.0
    )

    # 6. 导出修改后 LDE
    export_lde_csv(
        TheSystem,
        out_dir / "D13_lde_after_modify.csv"
    )

    # 7. 保存修改后的模型
    save_lens(
        TheSystem,
        out_dir / "D13_cooke_surface3_thickness_plus1.zmx"
    )

    # 8. 导出 MTF 和 Spot
    export_fft_mtf(
        TheSystem,
        out_dir,
        filename="D13_fft_mtf.txt"
    )

    export_standard_spot(
        TheSystem,
        out_dir,
        filename="D13_standard_spot.txt"
    )

    # 9. 关闭 Zemax
    del zosapi
    zosapi = None

    print("===== D13 Test Runner Finished =====")