# modules/result_analyzer.py

from pathlib import Path
import pandas as pd


def test_result_analyzer():
    print("result_analyzer.py 导入成功")


def read_csv_result(csv_path):
    """
    读取参数扫描结果 CSV。
    后面 D23/D24 会继续完善。
    """
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"找不到 CSV 文件: {csv_path}")

    df = pd.read_csv(csv_path)
    print("CSV 读取成功，前 5 行如下：")
    print(df.head())
    return df


if __name__ == "__main__":
    test_result_analyzer()