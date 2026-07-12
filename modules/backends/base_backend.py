# modules/backends/base_backend.py

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseBackend(ABC):
    """
    Backend 抽象基类。

    所有 Backend 都应该实现 execute_run()。
    Workflow Runner 不关心底层是真 Zemax 还是 Mock，
    只要求 Backend 返回统一格式结果。
    """

    name = "base"

    @abstractmethod
    def execute_run(self, run_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行一次参数扫描任务。

        输入：
            run_item: 单次运行参数，例如 surface、parameter、value 等。

        输出：
            标准结果字典。
        """
        raise NotImplementedError