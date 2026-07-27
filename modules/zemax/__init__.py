"""Zemax ZOS-API integration modules for Project-X."""

from modules.zemax.connection import (
    DEFAULT_ZEMAX_INSTALL_DIR,
    StandaloneZemaxConnection,
    ZemaxConnectionError,
)
from modules.zemax.model_ops import (
    ModelOperationError,
    copy_baseline_model,
    open_working_model,
    read_surface,
    save_model_as,
    set_surface_thickness,
    sha256_file,
)

__all__ = [
    "DEFAULT_ZEMAX_INSTALL_DIR",
    "StandaloneZemaxConnection",
    "ZemaxConnectionError",
    "ModelOperationError",
    "copy_baseline_model",
    "open_working_model",
    "read_surface",
    "save_model_as",
    "set_surface_thickness",
    "sha256_file",
]
