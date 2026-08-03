"""Focused, auditable ZOS-API operations for sequential models."""

from typing import Any, Dict

from modules.zemax.model_ops import ModelOperationError, read_surface


class FocusOperationError(RuntimeError):
    """Raised when a ZOS-API focus operation cannot complete safely."""


def run_quick_focus(
    system: Any,
    zosapi: Any,
    use_centroid: bool = True,
) -> Dict[str, Any]:
    """Run radial-spot Quick Focus and report the image-distance change."""

    surface_count = int(system.LDE.NumberOfSurfaces)
    focus_surface_id = surface_count - 2

    if focus_surface_id < 1:
        raise FocusOperationError(
            "The sequential model has no valid image-distance surface."
        )

    try:
        before = read_surface(system, focus_surface_id)
    except ModelOperationError as exc:
        raise FocusOperationError(str(exc)) from exc

    quick_focus = system.Tools.OpenQuickFocus()
    if quick_focus is None:
        raise FocusOperationError("Unable to open the Quick Focus tool.")

    try:
        quick_focus.Criterion = (
            zosapi.Tools.General.QuickFocusCriterion.SpotSizeRadial
        )
        quick_focus.UseCentroid = bool(use_centroid)
        quick_focus.RunAndWaitForCompletion()
    finally:
        quick_focus.Close()

    try:
        after = read_surface(system, focus_surface_id)
    except ModelOperationError as exc:
        raise FocusOperationError(str(exc)) from exc

    return {
        "criterion": "spot_size_radial",
        "use_centroid": bool(use_centroid),
        "focus_surface_id": focus_surface_id,
        "thickness_before_mm": before["thickness"],
        "thickness_after_mm": after["thickness"],
        "focus_shift_mm": after["thickness"] - before["thickness"],
    }


__all__ = ["FocusOperationError", "run_quick_focus"]
