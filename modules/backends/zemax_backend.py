# modules/backends/zemax_backend.py

from typing import Any, Dict

from modules.backends.base_backend import BaseBackend


class ZemaxBackend(BaseBackend):
    """
    ZemaxBackend 未来用于真实调用 ZOS-API。

    D58 阶段只建立接口壳层，
    不在今天连接 OpticStudio。
    """

    name = "zemax"

    def execute_run(self, run_item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "error",
            "backend": self.name,
            "message": "ZemaxBackend is not implemented yet. This is a D58 placeholder.",
            "simulation_mode": False,
        }