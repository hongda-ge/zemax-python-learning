"""Zemax ZOS-API integration modules for Project-X."""

from modules.zemax.analysis_ops import (
    AnalysisOperationError,
    export_fft_mtf_text,
    export_standard_spot_text,
    parse_fft_mtf_text,
    parse_standard_spot_text,
)
from modules.zemax.connection import (
    DEFAULT_ZEMAX_INSTALL_DIR,
    StandaloneZemaxConnection,
    ZemaxConnectionError,
)
from modules.zemax.focus_ops import FocusOperationError, run_quick_focus
from modules.zemax.merit_ops import (
    calculate_existing_merit_function,
    load_merit_recipe,
    read_merit_definition,
)
from modules.zemax.model_ops import (
    ModelOperationError,
    copy_baseline_model,
    copy_output_model,
    open_working_model,
    read_surface,
    save_model_as,
    set_surface_thickness,
    sha256_file,
)

__all__ = [
    "AnalysisOperationError",
    "export_fft_mtf_text",
    "export_standard_spot_text",
    "parse_fft_mtf_text",
    "parse_standard_spot_text",
    "DEFAULT_ZEMAX_INSTALL_DIR",
    "StandaloneZemaxConnection",
    "ZemaxConnectionError",
    "FocusOperationError",
    "run_quick_focus",
    "calculate_existing_merit_function",
    "load_merit_recipe",
    "read_merit_definition",
    "ModelOperationError",
    "copy_baseline_model",
    "copy_output_model",
    "open_working_model",
    "read_surface",
    "save_model_as",
    "set_surface_thickness",
    "sha256_file",
]
