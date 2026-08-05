"""Safe raw-analysis exports for real ZOS-API model runs."""

import re
from pathlib import Path
from typing import Any, Dict, List, Union

from modules.zemax.model_ops import OUTPUT_ROOT


class AnalysisOperationError(RuntimeError):
    """Raised when a real Zemax analysis cannot be exported safely."""


def _require_output_text_path(path: Union[str, Path]) -> Path:
    """Allow a new text artifact only below the project outputs root."""

    result = Path(path).expanduser()
    if not result.is_absolute():
        result = OUTPUT_ROOT.parent / result
    result = result.resolve()

    try:
        result.relative_to(OUTPUT_ROOT)
    except ValueError:
        raise AnalysisOperationError(
            f"Analysis output must stay inside {OUTPUT_ROOT}: {result}"
        )

    if result.suffix.lower() != ".txt":
        raise AnalysisOperationError(
            f"Analysis output must be a .txt file: {result}"
        )

    if result.exists():
        raise AnalysisOperationError(
            f"Refusing to overwrite analysis output: {result}"
        )

    result.parent.mkdir(parents=True, exist_ok=True)
    return result


_FLOAT_PATTERN = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?"


def parse_standard_spot_text(
    text_file: Union[str, Path],
) -> Dict[str, Any]:
    """Parse field-dependent RMS and maximum radii from Zemax text."""

    source = Path(text_file).expanduser().resolve()
    if not source.is_file():
        raise AnalysisOperationError(
            f"Standard Spot text not found: {source}"
        )

    text = source.read_text(encoding="utf-16")

    reference_match = re.search(r"参考\s*:\s*(\S+)", text)
    if reference_match is None:
        raise AnalysisOperationError(
            "Standard Spot reference was not found in the text."
        )

    field_pattern = re.compile(
        rf"视场坐标\s*:\s*({_FLOAT_PATTERN})\s+({_FLOAT_PATTERN})"
    )
    rms_pattern = re.compile(
        rf"RMS光斑半径\s*:\s*({_FLOAT_PATTERN})\s*(\S+)"
    )
    maximum_pattern = re.compile(
        rf"最大光斑半径\s*:\s*({_FLOAT_PATTERN})\s*(\S+)"
    )

    fields: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {}

    for line in text.splitlines():
        field_match = field_pattern.search(line)
        if field_match is not None:
            if current:
                fields.append(current)
            current = {
                "field_x_degree": float(field_match.group(1)),
                "field_y_degree": float(field_match.group(2)),
            }
            continue

        rms_match = rms_pattern.search(line)
        if rms_match is not None and current:
            current["rms_radius_um"] = float(rms_match.group(1))
            current["rms_unit"] = rms_match.group(2)
            continue

        maximum_match = maximum_pattern.search(line)
        if maximum_match is not None and current:
            current["maximum_radius_um"] = float(
                maximum_match.group(1)
            )
            current["maximum_unit"] = maximum_match.group(2)

    if current:
        fields.append(current)

    required = {
        "field_x_degree",
        "field_y_degree",
        "rms_radius_um",
        "maximum_radius_um",
    }
    for index, field in enumerate(fields, start=1):
        missing = required.difference(field)
        if missing:
            raise AnalysisOperationError(
                f"Spot field {index} is incomplete; missing {sorted(missing)}."
            )

    if not fields:
        raise AnalysisOperationError(
            "No field-dependent Spot metrics were parsed."
        )

    return {
        "source_text": str(source),
        "reference": reference_match.group(1),
        "field_count": len(fields),
        "fields": fields,
    }


def export_standard_spot_text(
    system: Any,
    zosapi: Any,
    output_file: Union[str, Path],
) -> Path:
    """Run Standard Spot with current settings and export raw Zemax text."""

    destination = _require_output_text_path(output_file)
    analysis = system.Analyses.New_Analysis(
        zosapi.Analysis.AnalysisIDM.StandardSpot
    )
    if analysis is None:
        raise AnalysisOperationError(
            "Unable to create the Standard Spot analysis."
        )

    try:
        settings = analysis.GetSettings()
        settings.ReferTo = (
            zosapi.Analysis.Settings.Spot.Reference.Centroid
        )
        settings.RayDensity = 6
        settings.Pattern = (
            zosapi.Analysis.Settings.Spot.Patterns.Hexapolar
        )
        settings.Field.SetFieldNumber(0)
        settings.Wavelength.SetWavelengthNumber(0)
        settings.Surface.UseImageSurface()
        settings.UsePolarization = False
        settings.IgnoreLateralColor = False
        settings.DeltaFocus = 0.0

        analysis.ApplyAndWaitForCompletion()
        results = analysis.GetResults()
        if results is None:
            raise AnalysisOperationError(
                "Standard Spot did not return a results object."
            )
        results.GetTextFile(str(destination))
    finally:
        analysis.Close()

    if not destination.is_file():
        raise AnalysisOperationError(
            f"Zemax did not create the analysis text: {destination}"
        )

    return destination


def export_fft_mtf_text(
    system: Any,
    zosapi: Any,
    output_file: Union[str, Path],
    maximum_frequency: float = 100.0,
) -> Path:
    """Run a configured polychromatic FFT MTF and export Zemax text."""

    destination = _require_output_text_path(output_file)
    analysis = system.Analyses.New_Analysis(
        zosapi.Analysis.AnalysisIDM.FftMtf
    )
    if analysis is None:
        raise AnalysisOperationError("Unable to create the FFT MTF analysis.")

    try:
        settings = analysis.GetSettings()
        settings.Field.SetFieldNumber(0)
        settings.Wavelength.SetWavelengthNumber(0)
        settings.Surface.UseImageSurface()
        settings.Type = zosapi.Analysis.Settings.Mtf.MtfTypes.Modulation
        settings.SampleSize = zosapi.Analysis.SampleSizes.S_64x64
        settings.MaximumFrequency = float(maximum_frequency)
        settings.ShowDiffractionLimit = False
        settings.UseDashes = False
        settings.UsePolarization = False

        analysis.ApplyAndWaitForCompletion()
        results = analysis.GetResults()
        if results is None:
            raise AnalysisOperationError(
                "FFT MTF did not return a results object."
            )
        results.GetTextFile(str(destination))
    finally:
        analysis.Close()

    if not destination.is_file():
        raise AnalysisOperationError(
            f"Zemax did not create the FFT MTF text: {destination}"
        )
    return destination


def parse_fft_mtf_text(
    text_file: Union[str, Path],
    target_frequencies: List[float],
) -> Dict[str, Any]:
    """Parse field-dependent tangential and sagittal FFT MTF samples."""

    source = Path(text_file).expanduser().resolve()
    if not source.is_file():
        raise AnalysisOperationError(f"FFT MTF text not found: {source}")
    text = source.read_text(encoding="utf-16")

    field_pattern = re.compile(
        rf"视场[：:]\s*({_FLOAT_PATTERN})\s*\(度\)"
    )
    row_pattern = re.compile(
        rf"^\s*({_FLOAT_PATTERN})\s+({_FLOAT_PATTERN})"
        rf"\s+({_FLOAT_PATTERN})\s*$"
    )
    parsed_fields: List[Dict[str, Any]] = []
    current_field = None
    current_rows: List[Dict[str, float]] = []

    def finish_field() -> None:
        if current_field is None:
            return
        if not current_rows:
            raise AnalysisOperationError(
                f"FFT MTF field {current_field} contains no numeric rows."
            )

        evaluations = []
        for target in target_frequencies:
            nearest = min(
                current_rows,
                key=lambda row: abs(row["frequency_cyc_per_mm"] - target),
            )
            if abs(nearest["frequency_cyc_per_mm"] - target) > 2.5:
                raise AnalysisOperationError(
                    f"No FFT MTF sample is close enough to {target}."
                )
            evaluations.append(
                {
                    "target_frequency_cyc_per_mm": float(target),
                    "sample_frequency_cyc_per_mm": nearest[
                        "frequency_cyc_per_mm"
                    ],
                    "tangential_mtf": nearest["tangential_mtf"],
                    "sagittal_mtf": nearest["sagittal_mtf"],
                    "mean_mtf": (
                        nearest["tangential_mtf"]
                        + nearest["sagittal_mtf"]
                    )
                    / 2.0,
                    "direction_gap": abs(
                        nearest["tangential_mtf"]
                        - nearest["sagittal_mtf"]
                    ),
                }
            )

        parsed_fields.append(
            {
                "field_y_degree": current_field,
                "sample_count": len(current_rows),
                "evaluations": evaluations,
            }
        )

    for line in text.splitlines():
        field_match = field_pattern.search(line)
        if field_match is not None:
            finish_field()
            current_field = float(field_match.group(1))
            current_rows = []
            continue

        if current_field is None:
            continue
        row_match = row_pattern.match(line)
        if row_match is None:
            continue
        frequency = float(row_match.group(1))
        tangential = float(row_match.group(2))
        sagittal = float(row_match.group(3))
        if not (0.0 <= tangential <= 1.05 and 0.0 <= sagittal <= 1.05):
            raise AnalysisOperationError(
                f"FFT MTF value outside [0, 1.05] at {frequency}."
            )
        current_rows.append(
            {
                "frequency_cyc_per_mm": frequency,
                "tangential_mtf": tangential,
                "sagittal_mtf": sagittal,
            }
        )

    finish_field()
    if not parsed_fields:
        raise AnalysisOperationError("No FFT MTF fields were parsed.")
    if len({field["field_y_degree"] for field in parsed_fields}) != len(
        parsed_fields
    ):
        raise AnalysisOperationError("Duplicate FFT MTF field sections found.")

    return {
        "source_text": str(source),
        "field_count": len(parsed_fields),
        "target_frequencies_cyc_per_mm": [
            float(value) for value in target_frequencies
        ],
        "fields": parsed_fields,
    }


__all__ = [
    "AnalysisOperationError",
    "export_fft_mtf_text",
    "export_standard_spot_text",
    "parse_fft_mtf_text",
    "parse_standard_spot_text",
]
