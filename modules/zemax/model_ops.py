"""Safe sequential-model operations for Project-X D60.

The write boundary is deliberate: baseline models live under ``models`` and
all writable copies and saved artifacts must live under ``outputs``.
"""

import hashlib
import math
import shutil
from pathlib import Path
from typing import Any, Dict, Union


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASELINE_ROOT = (PROJECT_ROOT / "models").resolve()
OUTPUT_ROOT = (PROJECT_ROOT / "outputs").resolve()
ALLOWED_MODEL_SUFFIXES = {".zmx", ".zos"}


class ModelOperationError(RuntimeError):
    """Raised when a model operation violates safety rules or fails."""


def _resolved(path: Union[str, Path]) -> Path:
    """Resolve a path, using the project root for relative paths."""
    result = Path(path).expanduser()
    if not result.is_absolute():
        result = PROJECT_ROOT / result
    return result.resolve()


def _require_inside(path: Path, root: Path, label: str) -> Path:
    """Reject a path that escapes its allowed root."""
    try:
        path.relative_to(root)
    except ValueError:
        raise ModelOperationError(
            "{0} must stay inside {1}: {2}".format(label, root, path)
        )
    return path


def _require_model_suffix(path: Path) -> None:
    """Accept only supported sequential model file extensions."""
    if path.suffix.lower() not in ALLOWED_MODEL_SUFFIXES:
        raise ModelOperationError(
            "Unsupported model extension: {0}".format(path.suffix)
        )


def sha256_file(path: Union[str, Path]) -> str:
    """Calculate a stable SHA-256 fingerprint without modifying the file."""
    resolved = _resolved(path)
    if not resolved.is_file():
        raise ModelOperationError("File not found: {0}".format(resolved))

    digest = hashlib.sha256()
    with resolved.open("rb") as file_handle:
        for block in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def copy_baseline_model(
    baseline_file: Union[str, Path],
    run_dir: Union[str, Path],
    working_name: str = "working_model.zmx",
) -> Dict[str, Any]:
    """Copy a baseline model into one writable run directory."""
    baseline = _require_inside(
        _resolved(baseline_file),
        BASELINE_ROOT,
        "Baseline model",
    )
    if not baseline.is_file():
        raise ModelOperationError(
            "Baseline model not found: {0}".format(baseline)
        )
    _require_model_suffix(baseline)

    output_dir = _require_inside(
        _resolved(run_dir),
        OUTPUT_ROOT,
        "Run directory",
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    working_file = _require_inside(
        (output_dir / working_name).resolve(),
        output_dir,
        "Working model",
    )
    _require_model_suffix(working_file)

    if working_file.exists():
        raise ModelOperationError(
            "Working model already exists; refusing to overwrite: {0}".format(
                working_file
            )
        )

    baseline_hash = sha256_file(baseline)
    shutil.copy2(str(baseline), str(working_file))
    working_hash = sha256_file(working_file)

    if working_hash != baseline_hash:
        raise ModelOperationError(
            "Copied model hash does not match the baseline hash."
        )

    return {
        "baseline_file": str(baseline),
        "baseline_sha256": baseline_hash,
        "working_file": str(working_file),
        "working_sha256_after_copy": working_hash,
        "copy_verified": True,
    }


def copy_output_model(
    source_file: Union[str, Path],
    run_dir: Union[str, Path],
    working_name: str = "working_model.zmx",
) -> Dict[str, Any]:
    """Copy one verified output model into a new output run directory."""

    source = _require_inside(
        _resolved(source_file),
        OUTPUT_ROOT,
        "Source output model",
    )
    if not source.is_file():
        raise ModelOperationError("Output model not found: {0}".format(source))
    _require_model_suffix(source)

    output_dir = _require_inside(
        _resolved(run_dir),
        OUTPUT_ROOT,
        "Run directory",
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    working_file = _require_inside(
        (output_dir / working_name).resolve(),
        output_dir,
        "Working model",
    )
    _require_model_suffix(working_file)

    if working_file.exists():
        raise ModelOperationError(
            "Working model already exists; refusing to overwrite: {0}".format(
                working_file
            )
        )
    if source == working_file:
        raise ModelOperationError("Source and working output models must differ.")

    source_hash = sha256_file(source)
    shutil.copy2(str(source), str(working_file))
    working_hash = sha256_file(working_file)
    if working_hash != source_hash:
        raise ModelOperationError("Copied output model hash does not match.")

    return {
        "source_file": str(source),
        "source_sha256": source_hash,
        "working_file": str(working_file),
        "working_sha256_after_copy": working_hash,
        "copy_verified": True,
    }


def open_working_model(system: Any, model_file: Union[str, Path]) -> Path:
    """Open a model only when it is a writable copy under ``outputs``."""
    model_path = _require_inside(
        _resolved(model_file),
        OUTPUT_ROOT,
        "Working model",
    )
    if not model_path.is_file():
        raise ModelOperationError(
            "Working model not found: {0}".format(model_path)
        )
    _require_model_suffix(model_path)

    system.LoadFile(str(model_path), False)
    return model_path


def read_surface(system: Any, surface_id: int) -> Dict[str, Any]:
    """Read common LDE values from one sequential surface."""
    surface_count = int(system.LDE.NumberOfSurfaces)
    if surface_id < 0 or surface_id >= surface_count:
        raise ModelOperationError(
            "Surface {0} is outside the valid range 0..{1}.".format(
                surface_id,
                surface_count - 1,
            )
        )

    surface = system.LDE.GetSurfaceAt(int(surface_id))

    def safe_text(attribute: str) -> str:
        try:
            return str(getattr(surface, attribute))
        except Exception:
            return ""

    return {
        "surface_id": int(surface_id),
        "surface_count": surface_count,
        "radius": float(surface.Radius),
        "thickness": float(surface.Thickness),
        "material": safe_text("Material"),
        "comment": safe_text("Comment"),
    }


def set_surface_thickness(
    system: Any,
    surface_id: int,
    new_thickness: float,
) -> Dict[str, float]:
    """Set one in-memory LDE thickness and return its before/after values."""
    requested = float(new_thickness)
    if not math.isfinite(requested):
        raise ModelOperationError("Thickness must be a finite number.")

    before = read_surface(system, surface_id)
    surface = system.LDE.GetSurfaceAt(int(surface_id))
    surface.Thickness = requested
    actual = float(surface.Thickness)

    return {
        "surface_id": int(surface_id),
        "old_thickness": float(before["thickness"]),
        "requested_thickness": requested,
        "actual_thickness": actual,
    }


def save_model_as(
    system: Any,
    output_file: Union[str, Path],
    run_dir: Union[str, Path],
) -> Path:
    """Save the current system to a new model inside its run directory."""
    allowed_run_dir = _require_inside(
        _resolved(run_dir),
        OUTPUT_ROOT,
        "Run directory",
    )
    destination = _require_inside(
        _resolved(output_file),
        allowed_run_dir,
        "Saved model",
    )
    _require_model_suffix(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        raise ModelOperationError(
            "Saved model already exists; refusing to overwrite: {0}".format(
                destination
            )
        )

    system.SaveAs(str(destination))
    if not destination.is_file():
        raise ModelOperationError(
            "OpticStudio did not create the saved model: {0}".format(
                destination
            )
        )
    return destination


__all__ = [
    "BASELINE_ROOT",
    "OUTPUT_ROOT",
    "ModelOperationError",
    "copy_baseline_model",
    "copy_output_model",
    "open_working_model",
    "read_surface",
    "save_model_as",
    "set_surface_thickness",
    "sha256_file",
]
