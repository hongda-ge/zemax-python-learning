# modules/zemax_runner.py

from pathlib import Path


def test_zemax_runner():
    print("zemax_runner.py 导入成功")


def get_project_root():
    """
    获取项目根目录。
    当前文件在 modules 文件夹里，所以 parents[1] 是 02_ZOSAPI_PYTHON。
    """
    return Path(__file__).resolve().parents[1]


def show_project_paths():
    """
    显示常用项目路径，检查路径是否正确。
    """
    root = get_project_root()

    print("项目根目录:", root)
    print("configs目录:", root / "configs")
    print("models目录:", root / "models")
    print("results目录:", root / "results")
    print("figures目录:", root / "figures")
    print("logs目录:", root / "logs")


if __name__ == "__main__":
    test_zemax_runner()
    show_project_paths()