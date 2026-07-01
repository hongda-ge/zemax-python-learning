from pathlib import Path
import csv
import yaml

from zemax_runner import (
    connect_zemax,
    open_lens,
    export_lde_csv,
    save_lens,
    export_fft_mtf,
    export_standard_spot,
    set_surface_thickness,
)


def generate_delta_values(start_delta, end_delta, step):
    """
    生成 delta 扫描值列表。
    例如 -1.0 到 1.0，步长 0.2，会生成 11 个点。
    """
    values = []
    delta = float(start_delta)

    while delta <= float(end_delta) + 1e-9:
        values.append(round(delta, 10))
        delta += float(step)

    return values


def format_delta_for_filename(delta):
    """
    把 delta 数值变成适合文件名的字符串。
    例如：
    -1.0 -> m1p00
     0.2 -> p0p20
    """
    sign = "p" if delta >= 0 else "m"
    text = f"{abs(delta):.2f}".replace(".", "p")
    return sign + text


def load_config(config_path):
    """
    读取 YAML 配置文件。
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config


if __name__ == "__main__":
    print("===== D16 Thickness Sweep Started =====")

    # 1. 项目根目录
    project_dir = Path(__file__).resolve().parents[1]

    # 2. 读取 D16 配置文件
    config_path = project_dir / "configs" / "config_D16_cooke_thickness_sweep.yaml"
    config = load_config(config_path)

    # 3. 从配置文件中取出模型、扫描、输出信息
    lens_file = Path(config["model"]["lens_file"])

    sweep = config["sweep"]
    surface_id = int(sweep["surface_id"])
    start_delta = float(sweep["start_delta"])
    end_delta = float(sweep["end_delta"])
    step = float(sweep["step"])

    output_dir = Path(config["outputs"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    models_dir = output_dir / "models"
    lde_dir = output_dir / "lde_csv"
    mtf_dir = output_dir / "mtf_txt"
    spot_dir = output_dir / "spot_txt"

    models_dir.mkdir(parents=True, exist_ok=True)
    lde_dir.mkdir(parents=True, exist_ok=True)
    mtf_dir.mkdir(parents=True, exist_ok=True)
    spot_dir.mkdir(parents=True, exist_ok=True)

    summary_csv = output_dir / config["outputs"]["summary_csv"]

    # 4. 生成扫描点
    delta_values = generate_delta_values(start_delta, end_delta, step)

    print("Config file:", config_path)
    print("Lens file:", lens_file)
    print("Output dir:", output_dir)
    print("Surface ID:", surface_id)
    print("Delta values:", delta_values)
    print("Total cases:", len(delta_values))

    # 5. 启动 Zemax
    zosapi = None
    summary_rows = []

    try:
        zosapi, TheApplication, TheSystem = connect_zemax()

        # 6. 打开原始 Cooke 镜头
        open_lens(TheSystem, lens_file)

        # 7. 读取原始厚度
        TheLDE = TheSystem.LDE
        target_surf = TheLDE.GetSurfaceAt(surface_id)
        original_thickness = target_surf.Thickness

        print("\nOriginal thickness:")
        print(f"Surface {surface_id} Thickness = {original_thickness}")

        # 8. 先保存一份原始 LDE
        export_lde_csv(
            TheSystem,
            output_dir / "D16_original_lde.csv"
        )

        # 9. 开始循环扫描
        for idx, delta in enumerate(delta_values, start=1):
            case_tag = format_delta_for_filename(delta)
            actual_thickness = original_thickness + delta

            print("\n" + "=" * 60)
            print(f"Case {idx}/{len(delta_values)}")
            print("Delta:", delta)
            print("Actual thickness:", actual_thickness)
            print("=" * 60)

            model_path = models_dir / f"case_{idx:03d}_delta_{case_tag}.zmx"
            lde_csv_path = lde_dir / f"case_{idx:03d}_delta_{case_tag}_lde.csv"
            mtf_filename = f"case_{idx:03d}_delta_{case_tag}_fft_mtf.txt"
            spot_filename = f"case_{idx:03d}_delta_{case_tag}_standard_spot.txt"

            status = "success"
            error_message = ""

            try:
                # 9.1 设置当前扫描点厚度
                set_surface_thickness(
                    TheSystem,
                    surface_id=surface_id,
                    new_thickness=actual_thickness
                )

                # 9.2 导出当前 LDE
                export_lde_csv(
                    TheSystem,
                    lde_csv_path
                )

                # 9.3 保存当前模型
                save_lens(
                    TheSystem,
                    model_path
                )

                # 9.4 导出 MTF
                mtf_path = export_fft_mtf(
                    TheSystem,
                    mtf_dir,
                    filename=mtf_filename
                )

                # 9.5 导出 Spot
                spot_path = export_standard_spot(
                    TheSystem,
                    spot_dir,
                    filename=spot_filename
                )

            except Exception as e:
                status = "failed"
                error_message = str(e)
                mtf_path = ""
                spot_path = ""

                print("This case failed:")
                print(error_message)

            summary_rows.append({
                "case_index": idx,
                "delta_mm": delta,
                "original_thickness_mm": original_thickness,
                "actual_thickness_mm": actual_thickness,
                "status": status,
                "model_path": str(model_path),
                "lde_csv_path": str(lde_csv_path),
                "mtf_txt_path": str(mtf_path),
                "spot_txt_path": str(spot_path),
                "error_message": error_message,
            })

        # 10. 保存扫描摘要 CSV
        with open(summary_csv, "w", newline="", encoding="utf-8-sig") as f:
            fieldnames = [
                "case_index",
                "delta_mm",
                "original_thickness_mm",
                "actual_thickness_mm",
                "status",
                "model_path",
                "lde_csv_path",
                "mtf_txt_path",
                "spot_txt_path",
                "error_message",
            ]

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(summary_rows)

        print("\nSummary CSV saved to:", summary_csv)

    finally:
        # 11. 关闭 Zemax
        if zosapi is not None:
            del zosapi
            zosapi = None

    print("\n===== D16 Thickness Sweep Finished =====")