
"""Day06: Double Gauss fixed-focus FFT MTF grid scan."""

import csv
import json
import math
from datetime import datetime
from pathlib import Path

import numpy as np

from modules.zemax.connection import StandaloneZemaxConnection
from modules.zemax.model_ops import sha256_file


ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "models" / "baselines" / "Day06_BEST_850Astig.zos"

K9_VALUES = [-0.36416, -0.35416, -0.34416, -0.33416, -0.32416]
R10_VALUES = [6.164721, 6.174721, 6.184721, 6.194721, 6.204721]

# 名称、视场编号、波长编号
MEASUREMENTS = [
    ("IR7", 7, 4),      # 25.7度, 850 nm
    ("IR4", 4, 4),      # 7度, 850 nm
    ("V587_7", 7, 2),   # 25.7度, 587.6 nm
    ("V587_4", 4, 2),   # 7度, 587.6 nm
    ("V486_7", 7, 1),   # 25.7度, 486.1 nm
    ("V656_7", 7, 3),   # 25.7度, 656.3 nm
]

RUN_DIR = (
    ROOT / "outputs" / "day06_double_gauss_api_scan"
    / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
)
CSV_FILE = RUN_DIR / "scan_fft_mtf.csv"


def calculate_mtf(system, api, field_number, wave_number):
    analysis = system.Analyses.New_FftMtf()

    try:
        settings = analysis.GetSettings()
        settings.Field.SetFieldNumber(field_number)
        settings.Wavelength.SetWavelengthNumber(wave_number)
        settings.Surface.UseImageSurface()

        settings.SampleSize = api.Analysis.SampleSizes.S_128x128
        settings.MaximumFrequency = 120.0
        settings.Type = api.Analysis.Settings.Mtf.MtfTypes.Modulation
        settings.ShowDiffractionLimit = False
        settings.UsePolarization = False

        analysis.ApplyAndWaitForCompletion()
        results = analysis.GetResults()

        if results is None or results.NumberOfDataSeries != 1:
            raise RuntimeError("Unexpected FFT MTF data series")

        data = results.GetDataSeries(0)
        frequencies = np.asarray(
            tuple(data.XData.Data), dtype=float
        )

        raw_y = data.YData.Data
        mtf = np.asarray(tuple(raw_y), dtype=float).reshape(
            raw_y.GetLength(0),
            raw_y.GetLength(1)
        )

        if mtf.shape == (2, len(frequencies)):
            mtf = mtf.T

        if mtf.shape != (len(frequencies), 2):
            raise RuntimeError(f"Unexpected MTF shape: {mtf.shape}")

        idx = int(np.argmin(np.abs(frequencies - 80.0)))
        actual_frequency = float(frequencies[idx])

        if abs(actual_frequency - 80.0) > 2.5:
            raise RuntimeError("No MTF sample near 80 lp/mm")

        t_mtf = float(mtf[idx, 0])
        s_mtf = float(mtf[idx, 1])

        if not all(
            math.isfinite(v) and 0.0 <= v <= 1.05
            for v in (t_mtf, s_mtf)
        ):
            raise RuntimeError("Invalid MTF result")

        return actual_frequency, t_mtf, s_mtf

    finally:
        analysis.Close()


def main():
    print("=== Day06 ZOS-API 25-Case FFT MTF Scan ===")

    if not MODEL.is_file():
        raise FileNotFoundError(MODEL)

    source_hash = sha256_file(MODEL)
    RUN_DIR.mkdir(parents=True, exist_ok=False)

    columns = ["case_id", "k7", "k9", "R10", "frequency"]
    for name, _, _ in MEASUREMENTS:
        columns.extend([f"{name}_T", f"{name}_S"])

    completed = 0

    with StandaloneZemaxConnection() as conn:
        system = conn.system
        api = conn.ZOSAPI
        system.LoadFile(str(MODEL), False)

        lde = system.LDE
        s7 = lde.GetSurfaceAt(7)
        s9 = lde.GetSurfaceAt(9)
        s10 = lde.GetSurfaceAt(10)

        original_k9 = float(s9.Conic)
        original_r10 = float(s10.Radius)
        k7 = float(s7.Conic)

        # 像面前的间隔：用于检测意外调焦
        image_gap_surface = lde.GetSurfaceAt(
            lde.NumberOfSurfaces - 2
        )
        original_image_gap = float(image_gap_surface.Thickness)

        if abs(k7 - 0.27900) > 0.0001:
            raise RuntimeError("Unexpected surface 7 conic")

        with CSV_FILE.open(
            "w", newline="", encoding="utf-8-sig"
        ) as file:
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()

            try:
                for k9 in K9_VALUES:
                    for r10 in R10_VALUES:
                        # 每次先恢复原始参数
                        s9.Conic = original_k9
                        s10.Radius = original_r10

                        # 再设置本次扫描参数
                        s9.Conic = k9
                        s10.Radius = r10

                        if abs(float(s9.Conic) - k9) > 1e-7:
                            raise RuntimeError("K9 write mismatch")
                        if abs(float(s10.Radius) - r10) > 1e-6:
                            raise RuntimeError("R10 write mismatch")

                        if abs(
                            float(image_gap_surface.Thickness)
                            - original_image_gap
                        ) > 1e-8:
                            raise RuntimeError(
                                "Image distance changed unexpectedly"
                            )

                        row = {
                            "case_id": completed + 1,
                            "k7": k7,
                            "k9": k9,
                            "R10": r10,
                        }

                        sample_frequency = None

                        for name, field_id, wave_id in MEASUREMENTS:
                            freq, t_mtf, s_mtf = calculate_mtf(
                                system, api, field_id, wave_id
                            )
                            sample_frequency = freq
                            row[f"{name}_T"] = t_mtf
                            row[f"{name}_S"] = s_mtf

                        row["frequency"] = sample_frequency
                        writer.writerow(row)
                        file.flush()

                        completed += 1
                        print(
                            f"[{completed:02d}/25] "
                            f"k9={k9:.5f}, R10={r10:.6f} | "
                            f"IR7 T={row['IR7_T']:.4f}, "
                            f"S={row['IR7_S']:.4f}",
                            flush=True
                        )

            finally:
                # 异常发生时也恢复内存参数
                s9.Conic = original_k9
                s10.Radius = original_r10

        print("Original in-memory parameters restored.")

    # 独立验证硬盘上的BEST未改变
    if sha256_file(MODEL) != source_hash:
        raise RuntimeError("SOURCE MODEL HASH CHANGED!")

    manifest = {
        "backend": "real_zosapi",
        "model": str(MODEL),
        "model_sha256": source_hash,
        "cases_completed": completed,
        "quick_focus": False,
        "model_saved": False,
        "sampling": "128x128",
        "target_frequency_lpmm": 80.0,
        "measurements": MEASUREMENTS,
        "csv_file": str(CSV_FILE),
    }

    (RUN_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("\nCases completed:", completed)
    print("Source model unchanged: True")
    print("CSV:", CSV_FILE)

    if completed == 25:
        print("DAY06 API SCAN COMPLETED")


if __name__ == "__main__":
    main()
