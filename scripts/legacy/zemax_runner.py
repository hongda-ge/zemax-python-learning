from __future__ import annotations

from pathlib import Path
from typing import Any
import csv
import os

import clr


# Project structure:
# 02_zosapi_python/
# ├─ scripts/
# │  └─ legacy/
# │     └─ zemax_runner.py
# ├─ models/
# ├─ results/
# └─ configs/
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Your OpticStudio 2024 R1.03 installation directory.
ZEMAX_INSTALL_DIR = Path(r"L:\Program Files\Zemax2024 R1.03")

# Set after connect_zemax() succeeds. Analysis functions use this namespace.
_ZOSAPI: Any | None = None


class ZemaxRunnerError(RuntimeError):
    """Base exception for this module."""


class ZemaxConnectionError(ZemaxRunnerError):
    """Raised when OpticStudio cannot be initialized or connected."""


class ZemaxFileError(ZemaxRunnerError):
    """Raised when a model or output file operation fails."""


class ZemaxAnalysisError(ZemaxRunnerError):
    """Raised when an OpticStudio analysis fails."""


def _require_file(path: Path, label: str) -> Path:
    """Return an absolute file path, or raise a clear error."""
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"{label} not found: {path}")
    return path


def _resolve_project_path(path: str | Path) -> Path:
    """
    Resolve a relative path against PROJECT_ROOT.

    Example:
        models/Cooke.zmx
        -> <project>/models/Cooke.zmx
    """
    result = Path(path).expanduser()
    if not result.is_absolute():
        result = PROJECT_ROOT / result
    return result.resolve()


class PythonStandaloneApplication:
    """Standalone OpticStudio connection implemented with pythonnet."""

    def __init__(
        self,
        zemax_install_dir: str | Path = ZEMAX_INSTALL_DIR,
    ):
        global _ZOSAPI

        # Define these first so cleanup is safe if initialization fails.
        self.TheConnection = None
        self.TheApplication = None
        self.TheSystem = None
        self.ZOSAPI = None
        self._closed = False

        install_dir = Path(zemax_install_dir).expanduser().resolve()
        if not install_dir.is_dir():
            raise ZemaxConnectionError(
                f"OpticStudio install directory not found: {install_dir}"
            )

        # Your installation stores the API assemblies directly in this folder.
        net_helper = _require_file(
            install_dir / "ZOSAPI_NetHelper.dll",
            "ZOSAPI_NetHelper.dll",
        )
        clr.AddReference(str(net_helper))

        import ZOSAPI_NetHelper

        initialized = ZOSAPI_NetHelper.ZOSAPI_Initializer.Initialize(
            str(install_dir)
        )
        if not initialized:
            raise ZemaxConnectionError(
                f"Unable to initialize OpticStudio from: {install_dir}"
            )

        # Ask NetHelper for the active OpticStudio directory.
        zemax_dir = Path(
            str(ZOSAPI_NetHelper.ZOSAPI_Initializer.GetZemaxDirectory())
        ).expanduser().resolve()

        # Fallback for installations where the DLLs are in install_dir.
        if not (zemax_dir / "ZOSAPI.dll").is_file():
            zemax_dir = install_dir

        zosapi_dll = _require_file(
            zemax_dir / "ZOSAPI.dll",
            "ZOSAPI.dll",
        )
        interfaces_dll = _require_file(
            zemax_dir / "ZOSAPI_Interfaces.dll",
            "ZOSAPI_Interfaces.dll",
        )

        clr.AddReference(str(zosapi_dll))
        clr.AddReference(str(interfaces_dll))

        import ZOSAPI

        self.ZOSAPI = ZOSAPI
        _ZOSAPI = ZOSAPI

        self.TheConnection = ZOSAPI.ZOSAPI_Connection()
        if self.TheConnection is None:
            raise ZemaxConnectionError(
                "Unable to create ZOSAPI_Connection."
            )

        self.TheApplication = self.TheConnection.CreateNewApplication()
        if self.TheApplication is None:
            raise ZemaxConnectionError(
                "Unable to create a new OpticStudio application."
            )

        if not self.TheApplication.IsValidLicenseForAPI:
            self.close()
            raise ZemaxConnectionError(
                "The current OpticStudio license is not valid for ZOS-API."
            )

        self.TheSystem = self.TheApplication.PrimarySystem
        if self.TheSystem is None:
            self.close()
            raise ZemaxConnectionError(
                "Unable to acquire the OpticStudio PrimarySystem."
            )

    def close(self) -> None:
        """Close the Standalone OpticStudio process safely."""
        if self._closed:
            return

        try:
            if self.TheApplication is not None:
                self.TheApplication.CloseApplication()
        finally:
            self.TheSystem = None
            self.TheApplication = None
            self.TheConnection = None
            self._closed = True

    def __enter__(self) -> "PythonStandaloneApplication":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def __del__(self) -> None:
        # Never let interpreter-shutdown cleanup create a second error.
        try:
            self.close()
        except Exception:
            pass


def connect_zemax(
    zemax_install_dir: str | Path = ZEMAX_INSTALL_DIR,
):
    """
    Start OpticStudio in Standalone mode.

    Returns:
        zos, application, system
    """
    zos = PythonStandaloneApplication(zemax_install_dir)
    app = zos.TheApplication
    system = zos.TheSystem

    print("Connected to OpticStudio")
    print(
        "Version:",
        app.ZOSMajorVersion,
        app.ZOSMinorVersion,
        "SP",
        app.ZOSSPVersion,
    )
    print("Serial #:", app.SerialCode)
    print("SamplesDir:", app.SamplesDir)

    return zos, app, system


def close_zemax(zos: PythonStandaloneApplication | None) -> None:
    """Explicitly close a Standalone OpticStudio session."""
    if zos is not None:
        zos.close()


def make_output_dir(out_dir: str | Path) -> Path:
    """Create and return an absolute output directory."""
    path = _resolve_project_path(out_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def open_lens(TheSystem, lens_path: str | Path) -> Path:
    """Open a Zemax model and return its absolute path."""
    path = _resolve_project_path(lens_path)

    if not path.is_file():
        raise ZemaxFileError(f"Lens file not found: {path}")

    print("Loading lens file:", path)
    loaded = TheSystem.LoadFile(str(path), False)

    if not loaded:
        raise ZemaxFileError(f"OpticStudio failed to load: {path}")

    print("Lens file loaded.")
    return path


def export_lde_csv(TheSystem, csv_path: str | Path) -> Path:
    """Export current LDE surface data to CSV."""
    path = _resolve_project_path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lde = TheSystem.LDE
    n_surfaces = int(lde.NumberOfSurfaces)

    with path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            ["Surface", "Radius", "Thickness", "Material", "Comment"]
        )

        for surface_id in range(n_surfaces):
            surface = lde.GetSurfaceAt(surface_id)

            def safe_read(attribute: str):
                try:
                    return getattr(surface, attribute)
                except Exception:
                    return ""

            writer.writerow(
                [
                    surface_id,
                    safe_read("Radius"),
                    safe_read("Thickness"),
                    safe_read("Material"),
                    safe_read("Comment"),
                ]
            )

    print("LDE CSV saved to:", path)
    return path


def modify_surface_thickness(
    TheSystem,
    surface_id: int,
    delta_thickness: float,
) -> tuple[float, float]:
    """Add a thickness delta to one LDE surface."""
    surface = TheSystem.LDE.GetSurfaceAt(int(surface_id))

    old_thickness = float(surface.Thickness)
    surface.Thickness = old_thickness + float(delta_thickness)
    actual_thickness = float(surface.Thickness)

    print(
        f"Surface {surface_id} thickness: "
        f"{old_thickness} -> {actual_thickness}"
    )
    return old_thickness, actual_thickness


def set_surface_thickness(
    TheSystem,
    surface_id: int,
    new_thickness: float,
) -> tuple[float, float]:
    """Set one LDE surface to an absolute thickness."""
    surface = TheSystem.LDE.GetSurfaceAt(int(surface_id))

    old_thickness = float(surface.Thickness)
    surface.Thickness = float(new_thickness)
    actual_thickness = float(surface.Thickness)

    print(
        f"Surface {surface_id} thickness: "
        f"{old_thickness} -> {actual_thickness}"
    )
    return old_thickness, actual_thickness


def save_lens(TheSystem, save_path: str | Path) -> Path:
    """Save the current model as a new Zemax file."""
    path = _resolve_project_path(save_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    TheSystem.SaveAs(str(path))

    if not path.is_file():
        raise ZemaxFileError(
            f"SaveAs returned, but the output file was not created: {path}"
        )

    print("Lens saved to:", path)
    return path


def _get_zosapi():
    if _ZOSAPI is None:
        raise ZemaxConnectionError(
            "ZOS-API is not initialized. Call connect_zemax() first."
        )
    return _ZOSAPI


def _export_analysis_text(
    TheSystem,
    analysis_id,
    output_path: str | Path,
    analysis_name: str,
) -> Path:
    """Run one analysis and export its text result."""
    path = _resolve_project_path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    analysis = None
    try:
        analysis = TheSystem.Analyses.New_Analysis(analysis_id)
        if analysis is None:
            raise ZemaxAnalysisError(
                f"Unable to create analysis: {analysis_name}"
            )

        analysis.ApplyAndWaitForCompletion()

        results = analysis.GetResults()
        if results is None:
            raise ZemaxAnalysisError(
                f"No results returned by: {analysis_name}"
            )

        exported = bool(results.GetTextFile(str(path)))
        if not exported or not path.is_file():
            raise ZemaxAnalysisError(
                f"Unable to export {analysis_name} text file: {path}"
            )

        print(f"{analysis_name} saved to:", path)
        return path

    finally:
        if analysis is not None:
            try:
                analysis.Close()
            except Exception:
                pass


def export_fft_mtf(
    TheSystem,
    out_dir: str | Path,
    filename: str = "fft_mtf.txt",
) -> Path:
    """Run FFT MTF and export its text output."""
    zosapi = _get_zosapi()
    output_dir = make_output_dir(out_dir)

    return _export_analysis_text(
        TheSystem,
        zosapi.Analysis.AnalysisIDM.FftMtf,
        output_dir / filename,
        "FFT MTF",
    )


def export_standard_spot(
    TheSystem,
    out_dir: str | Path,
    filename: str = "standard_spot.txt",
) -> Path:
    """Run Standard Spot Diagram and export its text output."""
    zosapi = _get_zosapi()
    output_dir = make_output_dir(out_dir)

    return _export_analysis_text(
        TheSystem,
        zosapi.Analysis.AnalysisIDM.StandardSpot,
        output_dir / filename,
        "Standard Spot",
    )


__all__ = [
    "PROJECT_ROOT",
    "ZEMAX_INSTALL_DIR",
    "PythonStandaloneApplication",
    "connect_zemax",
    "close_zemax",
    "make_output_dir",
    "open_lens",
    "export_lde_csv",
    "modify_surface_thickness",
    "set_surface_thickness",
    "save_lens",
    "export_fft_mtf",
    "export_standard_spot",
]
