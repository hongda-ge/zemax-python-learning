# modules/backends/mock_backend.py

import math
from typing import Any, Dict

from modules.backends.base_backend import BaseBackend


class MockBackend(BaseBackend):
    """
    MockBackend 用于无 Zemax 环境下测试完整工作流。

    它不会启动 Zemax，
    只根据参数值生成模拟 MTF / RMS / score。
    """

    name = "mock"

    def execute_run(self, run_item: Dict[str, Any]) -> Dict[str, Any]:
        value = float(run_item["value"])

        mtf_50 = 0.65 + 0.25 * math.exp(-((value - 0.2) ** 2) / 0.25)
        mtf_30 = mtf_50 + 0.08
        rms_spot = 8.0 + 10.0 * abs(value - 0.2)
        score = mtf_50 - 0.02 * rms_spot

        return {
            "status": "success",
            "backend": self.name,
            "index": run_item.get("index"),
            "surface": run_item.get("surface"),
            "parameter": run_item.get("parameter"),
            "parameter_value": value,
            "MTF_30": round(mtf_30, 4),
            "MTF_50": round(mtf_50, 4),
            "RMS_Spot": round(rms_spot, 4),
            "score": round(score, 4),
            "simulation_mode": True,
        }