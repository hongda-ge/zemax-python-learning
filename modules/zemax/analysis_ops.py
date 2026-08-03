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


__all__ = [
    "AnalysisOperationError",
    "export_standard_spot_text",
    "parse_standard_spot_text",
]
