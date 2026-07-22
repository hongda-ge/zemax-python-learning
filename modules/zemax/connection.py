"""Standalone OpticStudio connection for Project-X.

This module is intentionally limited to connection lifecycle management:
initialize ZOS-API, create an application, expose the primary system, and
close the application safely. Model and analysis operations belong elsewhere.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union

import clr


DEFAULT_ZEMAX_INSTALL_DIR = Path(r"L:\Program Files\Zemax2024 R1.03")


class ZemaxConnectionError(RuntimeError):
    """Raised when a Standalone OpticStudio connection cannot be established."""


def _require_file(path: Path, label: str) -> Path:
    """Return a resolved file path or raise a diagnostic error."""
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise ZemaxConnectionError("{0} not found: {1}".format(label, resolved))
    return resolved


class StandaloneZemaxConnection:
    """Own one Standalone OpticStudio application and close it safely."""

    def __init__(
        self,
        install_dir: Union[str, Path] = DEFAULT_ZEMAX_INSTALL_DIR,
    ) -> None:
        self.install_dir = Path(install_dir).expanduser().resolve()
        self.zemax_dir: Optional[Path] = None
        self.ZOSAPI: Any = None
        self.connection: Any = None
        self.application: Any = None
        self.system: Any = None
        self._closed = False

        try:
            self._connect()
        except Exception:
            self.close()
            raise

    def _connect(self) -> None:
        """Initialize assemblies and create a new OpticStudio application."""
        if not self.install_dir.is_dir():
            raise ZemaxConnectionError(
                "OpticStudio install directory not found: {0}".format(
                    self.install_dir
                )
            )

        net_helper = _require_file(
            self.install_dir / "ZOSAPI_NetHelper.dll",
            "ZOSAPI_NetHelper.dll",
        )
        clr.AddReference(str(net_helper))

        import ZOSAPI_NetHelper

        initialized = ZOSAPI_NetHelper.ZOSAPI_Initializer.Initialize(
            str(self.install_dir)
        )
        if not initialized:
            raise ZemaxConnectionError(
                "ZOS-API initialization failed for: {0}".format(
                    self.install_dir
                )
            )

        detected_dir = Path(
            str(ZOSAPI_NetHelper.ZOSAPI_Initializer.GetZemaxDirectory())
        ).expanduser().resolve()

        if not (detected_dir / "ZOSAPI.dll").is_file():
            detected_dir = self.install_dir

        self.zemax_dir = detected_dir

        zosapi_dll = _require_file(detected_dir / "ZOSAPI.dll", "ZOSAPI.dll")
        interfaces_dll = _require_file(
            detected_dir / "ZOSAPI_Interfaces.dll",
            "ZOSAPI_Interfaces.dll",
        )
        clr.AddReference(str(zosapi_dll))
        clr.AddReference(str(interfaces_dll))

        import ZOSAPI

        self.ZOSAPI = ZOSAPI
        self.connection = ZOSAPI.ZOSAPI_Connection()
        if self.connection is None:
            raise ZemaxConnectionError("Unable to create ZOSAPI_Connection.")

        self.application = self.connection.CreateNewApplication()
        if self.application is None:
            raise ZemaxConnectionError(
                "Unable to create a Standalone OpticStudio application."
            )

        if not bool(self.application.IsValidLicenseForAPI):
            raise ZemaxConnectionError(
                "The current OpticStudio license is not valid for ZOS-API."
            )

        self.system = self.application.PrimarySystem
        if self.system is None:
            raise ZemaxConnectionError(
                "Unable to acquire the OpticStudio PrimarySystem."
            )

    @property
    def closed(self) -> bool:
        """Whether this connection has completed its close lifecycle."""
        return self._closed

    def info(self) -> Dict[str, Any]:
        """Return non-sensitive connection facts for logs and demos."""
        if self.application is None or self.system is None:
            raise ZemaxConnectionError("OpticStudio connection is not active.")

        version = "{0}.{1} SP{2}".format(
            self.application.ZOSMajorVersion,
            self.application.ZOSMinorVersion,
            self.application.ZOSSPVersion,
        )

        return {
            "backend": "zemax",
            "simulation_mode": False,
            "connected": True,
            "version": version,
            "license_valid": bool(self.application.IsValidLicenseForAPI),
            "license_status": str(self.application.LicenseStatus),
            "primary_system_available": self.system is not None,
            "install_dir": str(self.install_dir),
            "zosapi_dir": str(self.zemax_dir),
        }

    def close(self) -> None:
        """Close OpticStudio once and release local object references."""
        if self._closed:
            return

        try:
            if self.application is not None:
                self.application.CloseApplication()
        finally:
            self.system = None
            self.application = None
            self.connection = None
            self.ZOSAPI = None
            self._closed = True

    def __enter__(self) -> "StandaloneZemaxConnection":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


__all__ = [
    "DEFAULT_ZEMAX_INSTALL_DIR",
    "StandaloneZemaxConnection",
    "ZemaxConnectionError",
]
