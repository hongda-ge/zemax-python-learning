from pathlib import Path
import re
import matplotlib.pyplot as plt


def read_text_auto(path):
    """自动尝试几种常见编码读取 Zemax 导出的 txt。"""
    encodings = ["utf-8-sig", "utf-16", "gbk", "latin1"]

    for enc in encodings:
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            pass

    return path.read_text(errors="ignore")


def extract_mtf_numeric_rows(text):
    """
    从 Zemax MTF txt 中提取数字行。
    假设每行格式大概是：
    空间频率  曲线1  曲线2  曲线3 ...
    """
    rows = []

    for line in text.splitlines():
        nums = re.findall(r"[-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?", line)

        if len(nums) >= 2:
            values = [float(x) for x in nums]

            frequency = values[0]
            mtf_values = values[1:]

            # 简单过滤：MTF 通常在 0~1 之间，空间频率为正
            if 0 <= frequency <= 1000 and all(-0.05 <= y <= 1.05 for y in mtf_values):
                rows.append(values)

    if not rows:
        raise ValueError("没有从 txt 中识别到 MTF 数字数据。可以把 txt 前 30 行发我，我帮你改解析规则。")

    # 保留列数一致的行，避免把标题里的零散数字混进去
    max_cols = max(len(r) for r in rows)
    rows = [r for r in rows if len(r) == max_cols]

    return rows


def plot_mtf_txt(txt_path, png_path):
    txt_path = Path(txt_path)
    png_path = Path(png_path)

    text = read_text_auto(txt_path)
    rows = extract_mtf_numeric_rows(text)

    x = [r[0] for r in rows]

    plt.figure(figsize=(7, 5))

    n_curves = len(rows[0]) - 1

    for j in range(1, n_curves + 1):
        y = [r[j] for r in rows]
        plt.plot(x, y, label=f"Curve {j}")

    plt.xlabel("Spatial Frequency (cycles/mm)")
    plt.ylabel("MTF")
    plt.title("FFT MTF from Zemax txt")
    plt.ylim(0, 1.05)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    png_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(png_path, dpi=300)
    plt.close()

    print("MTF 图已保存到：", png_path)


if __name__ == "__main__":
    txt_path = r"C:\Users\20181\Desktop\Zemax\02_zosapi_python\results\D12_analysis_export\fft_mtf.txt"
    png_path = r"C:\Users\20181\Desktop\Zemax\02_zosapi_python\results\D12_analysis_export\fft_mtf_from_txt.png"

    plot_mtf_txt(txt_path, png_path)