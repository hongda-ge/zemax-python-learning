
from pathlib import Path
import numpy as np

from modules.zemax.connection import StandaloneZemaxConnection
from modules.zemax.model_ops import sha256_file


ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "models" / "baselines" / "Day06_BEST_850Astig.zos"


def main():
    print("=== Day06 FFT MTF Baseline Check ===")

    hash_before = sha256_file(MODEL)

    with StandaloneZemaxConnection() as conn:
        system = conn.system
        api = conn.ZOSAPI

        system.LoadFile(str(MODEL), False)

        analysis = system.Analyses.New_FftMtf()

        try:
            settings = analysis.GetSettings()

            settings.Field.SetFieldNumber(7)
            settings.Wavelength.SetWavelengthNumber(4)
            settings.Surface.UseImageSurface()

            settings.SampleSize = api.Analysis.SampleSizes.S_128x128
            settings.MaximumFrequency = 120.0
            settings.Type = api.Analysis.Settings.Mtf.MtfTypes.Modulation
            settings.ShowDiffractionLimit = False
            settings.UsePolarization = False

            assert settings.Field.GetFieldNumber() == 7
            assert settings.Wavelength.GetWavelengthNumber() == 4

            analysis.ApplyAndWaitForCompletion()
            results = analysis.GetResults()

            if results.NumberOfDataSeries != 1:
                raise RuntimeError(
                    f"Expected 1 data series, got "
                    f"{results.NumberOfDataSeries}"
                )

            data = results.GetDataSeries(0)

            frequencies = np.asarray(
                tuple(data.XData.Data), dtype=float
            )

            raw_y = data.YData.Data
            mtf = np.asarray(
                tuple(raw_y), dtype=float
            ).reshape(
                raw_y.GetLength(0),
                raw_y.GetLength(1)
            )

            # 兼容两种二维数组排列方向
            if mtf.shape == (2, len(frequencies)):
                mtf = mtf.T

            if mtf.shape != (len(frequencies), 2):
                raise RuntimeError(
                    f"Unexpected MTF array shape: {mtf.shape}"
                )

            index = int(
                np.argmin(np.abs(frequencies - 80.0))
            )

            actual_frequency = frequencies[index]
            if abs(actual_frequency - 80.0) > 2.5:
                raise RuntimeError(
                    "No FFT MTF sample close to 80 lp/mm"
                )

            t_mtf = mtf[index, 0]
            s_mtf = mtf[index, 1]

            print("\n--- Analysis Settings ---")
            print("Field: 7 (25.7 deg)")
            print("Wavelength: 4 (850 nm)")
            print("Sampling: 128x128")
            print("Focus: fixed")
            print(f"Sample frequency: {actual_frequency:.3f} lp/mm")

            print("\n--- FFT MTF ---")
            print(f"T-MTF = {t_mtf:.6f}")
            print(f"S-MTF = {s_mtf:.6f}")

            print("\nFFT MTF CHECK COMPLETED")

        finally:
            analysis.Close()

    assert sha256_file(MODEL) == hash_before
    print("Source model unchanged: True")


if __name__ == "__main__":
    main()
