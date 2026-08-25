"""Portable OpticStudio installation-path discovery."""

import os
from pathlib import Path
from typing import Iterable, Optional


ENVIRONMENT_VARIABLE = "ZEMAX_INSTALL_DIR"
COMMON_INSTALL_DIRS = (
    Path(r"C:\Program Files\Ansys Zemax OpticStudio 2024 R1.00"),
    Path(r"C:\Program Files\Zemax OpticStudio"),
    Path(r"D:\Program Files\Zemax OpticStudio"),
    Path(r"E:\Program Files\Ansys Zemax OpticStudio 2024 R1.00"),
    Path(r"L:\Program Files\Zemax2024 R1.03"),
)


def discover_zemax_install_dir(
    environment_value: Optional[str] = None,
    candidates: Iterable[Path] = COMMON_INSTALL_DIRS,
) -> Path:
    """Prefer an explicit override, then the first installation containing all API DLLs."""

    override = environment_value
    if override is None:
        override = os.environ.get(ENVIRONMENT_VARIABLE)
    if override:
        return Path(override).expanduser()

    required = ("ZOSAPI_NetHelper.dll", "ZOSAPI.dll", "ZOSAPI_Interfaces.dll")
    for candidate in candidates:
        path = Path(candidate).expanduser()
        if path.is_dir() and all((path / name).is_file() for name in required):
            return path

    return COMMON_INSTALL_DIRS[-1]


DEFAULT_ZEMAX_INSTALL_DIR = discover_zemax_install_dir()


__all__ = [
    "COMMON_INSTALL_DIRS",
    "DEFAULT_ZEMAX_INSTALL_DIR",
    "ENVIRONMENT_VARIABLE",
    "discover_zemax_install_dir",
]
