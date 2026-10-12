"""Plot the frozen Day06 IR7 tangential MTF response surface offline."""

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
CSV_FILE = ROOT / "results" / "day06_double_gauss" / "scan_fft_mtf.csv"
OUTPUT_FILE = ROOT / "figures" / "day06" / "day06_ir850_t_mtf_heatmap.png"

BEST_K9 = -0.33416
BEST_R10 = 6.194721
EXPECTED_FREQUENCY = 79.86622073578596


def main():
    with CSV_FILE.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    if len(rows) != 25:
        raise RuntimeError(f"Expected 25 rows, found {len(rows)}")

    k9_values = sorted({float(row["k9"]) for row in rows})
    r10_values = sorted({float(row["R10"]) for row in rows})
    frequencies = {float(row["frequency"]) for row in rows}

    if len(k9_values) != 5 or len(r10_values) != 5:
        raise RuntimeError("Expected a complete 5 x 5 K9/R10 grid")
    if frequencies != {EXPECTED_FREQUENCY}:
        raise RuntimeError(f"Unexpected frequency values: {frequencies}")

    values = {
        (float(row["k9"]), float(row["R10"])): float(row["IR7_T"])
        for row in rows
    }
    grid = np.array(
        [[values[(k9, r10)] for r10 in r10_values] for k9 in k9_values]
    )

    fig, ax = plt.subplots(figsize=(9.2, 6.8), constrained_layout=True)
    image = ax.imshow(grid, origin="lower", cmap="viridis", aspect="auto")

    ax.set_xticks(range(len(r10_values)), [f"{value:.6f}" for value in r10_values])
    ax.set_yticks(range(len(k9_values)), [f"{value:.5f}" for value in k9_values])
    ax.set_xlabel("R10 radius (mm)", fontsize=12)
    ax.set_ylabel("K9 conic coefficient", fontsize=12)
    ax.set_title(
        "850 nm, 25.7 deg Tangential MTF at 79.866 lp/mm",
        fontsize=15,
        pad=14,
    )

    threshold = (float(grid.min()) + float(grid.max())) / 2.0
    for row_index in range(grid.shape[0]):
        for column_index in range(grid.shape[1]):
            value = grid[row_index, column_index]
            color = "white" if value < threshold else "black"
            ax.text(
                column_index,
                row_index,
                f"{value:.4f}",
                ha="center",
                va="center",
                color=color,
                fontsize=10,
            )

    best_x = r10_values.index(BEST_R10)
    best_y = k9_values.index(BEST_K9)
    ax.scatter(
        best_x,
        best_y,
        marker="o",
        s=330,
        facecolors="none",
        edgecolors="#ff3b30",
        linewidths=2.6,
        label="Original BEST",
    )
    ax.annotate(
        "Original BEST\nK9=-0.33416, R10=6.194721 mm",
        xy=(best_x, best_y),
        xytext=(-115, 56),
        textcoords="offset points",
        arrowprops={"arrowstyle": "->", "color": "#ff3b30", "lw": 1.8},
        bbox={"boxstyle": "round,pad=0.35", "fc": "white", "ec": "#ff3b30"},
        fontsize=9.5,
    )

    colorbar = fig.colorbar(image, ax=ax, shrink=0.92)
    colorbar.set_label("Tangential MTF (IR7_T)", fontsize=11)
    ax.text(
        0.0,
        -0.16,
        "Frozen CSV | Fixed image plane | No Quick Focus",
        transform=ax.transAxes,
        fontsize=9.5,
        color="#555555",
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_FILE, dpi=180, facecolor="white")
    plt.close(fig)
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()
