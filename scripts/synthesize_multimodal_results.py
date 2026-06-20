from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthesize multimodal state summaries.")
    parser.add_argument("--summary", action="append", required=True, help="State summary CSV.")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    data = load_summaries([Path(path) for path in args.summary])
    combined_path = output_dir / "combined_multimodal_state_summary.csv"
    data.to_csv(combined_path, index=False)

    plot_cross_case_story(data, output_dir / "cross_case_multimodal_story.png")
    plot_state_map(data, output_dir / "cross_case_state_map.png")
    write_key_numbers(data, output_dir / "cross_case_key_numbers.txt")

    print(f"Wrote {combined_path}")
    print(f"Wrote {output_dir / 'cross_case_multimodal_story.png'}")
    print(f"Wrote {output_dir / 'cross_case_state_map.png'}")


def load_summaries(paths: list[Path]) -> pd.DataFrame:
    frames = []
    for path in paths:
        frame = pd.read_csv(path)
        case = path.name.replace("_multimodal_state_summary.csv", "")
        frame["case_label"] = case
        if case.startswith("5gs"):
            frame["mass_flow_g_s"] = 5.0
            frame["subcooling_nominal_c"] = 22.0
        elif case.startswith("10gs"):
            frame["mass_flow_g_s"] = 10.0
            frame["subcooling_nominal_c"] = 22.0
        elif case.startswith("15gs"):
            frame["mass_flow_g_s"] = 15.0
            frame["subcooling_nominal_c"] = 20.0
        elif case.startswith("25gs"):
            frame["mass_flow_g_s"] = 25.0
            frame["subcooling_nominal_c"] = 20.0
        frames.append(frame)
    data = pd.concat(frames, ignore_index=True)
    return data.sort_values(["mass_flow_g_s", "state_voltage"])


def plot_cross_case_story(data: pd.DataFrame, output_path: Path) -> None:
    colors = {
        "5gs_22C": "#1b9e77",
        "10gs_22C": "#377eb8",
        "15gs_20C": "#d95f02",
        "25gs_20C": "#6a3d9a",
    }
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    ax00, ax01, ax10, ax11 = axes.ravel()

    for case, group in data.groupby("case_label", sort=False):
        color = colors.get(case, None)
        label = case.replace("_", " ")
        ax00.plot(
            group["heat_flux_mean_w_cm2"],
            group["vapor_area_fraction_mean"],
            marker="o",
            linewidth=1.8,
            color=color,
            label=label,
        )
        ax01.scatter(
            group["vapor_area_fraction_mean"],
            group["ae_abs_energy_rate"],
            s=40 + group["state_voltage"] * 1.2,
            color=color,
            alpha=0.75,
            label=label,
        )
        ax10.plot(
            group["vapor_area_fraction_mean"],
            group["htc_mean_w_m2k"],
            marker="s",
            linewidth=1.8,
            color=color,
            label=label,
        )
        ax11.plot(
            group["heat_flux_mean_w_cm2"],
            group["active_length_fraction_mean"],
            marker="^",
            linewidth=1.8,
            color=color,
            label=label,
        )

    ax00.set_title("Visual vapor coverage rises with thermal forcing")
    ax00.set_xlabel("Heat flux (W/cm$^2$)")
    ax00.set_ylabel("Projected vapor area fraction")
    ax00.grid(True, alpha=0.3)

    ax01.set_title("AE energy increases with image-derived vapor activity")
    ax01.set_xlabel("Projected vapor area fraction")
    ax01.set_ylabel("AE absolute-energy rate")
    ax01.grid(True, alpha=0.3)

    ax10.set_title("Thermal response versus visual vapor metric")
    ax10.set_xlabel("Projected vapor area fraction")
    ax10.set_ylabel("Mean HTC (W/m$^2$ K)")
    ax10.grid(True, alpha=0.3)

    ax11.set_title("Vapor-covered streamwise length versus heat flux")
    ax11.set_xlabel("Heat flux (W/cm$^2$)")
    ax11.set_ylabel("Active vapor length fraction")
    ax11.grid(True, alpha=0.3)

    handles, labels = ax00.get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=4)
    fig.suptitle("Cross-case multimodal flow-boiling signatures", fontsize=14)
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def plot_state_map(data: pd.DataFrame, output_path: Path) -> None:
    metrics = [
        ("heat_flux_mean_w_cm2", "Heat flux"),
        ("vapor_area_fraction_mean", "Vapor area"),
        ("active_length_fraction_mean", "Active length"),
        ("ae_abs_energy_rate", "AE energy"),
        ("htc_mean_w_m2k", "HTC"),
    ]
    rows = []
    labels = []
    for _, row in data.iterrows():
        labels.append(f"{row['case_label']} | {row['state_label']}")
        rows.append([row[column] for column, _ in metrics])
    values = np.array(rows, dtype=float)
    mins = np.nanmin(values, axis=0)
    maxs = np.nanmax(values, axis=0)
    scaled = (values - mins) / np.where(maxs > mins, maxs - mins, 1)

    fig, ax = plt.subplots(figsize=(8, max(6, 0.22 * len(labels))), constrained_layout=True)
    im = ax.imshow(scaled, aspect="auto", cmap="viridis", vmin=0, vmax=1)
    ax.set_yticks(range(len(labels)), labels=labels, fontsize=7)
    ax.set_xticks(range(len(metrics)), labels=[label for _, label in metrics], rotation=25, ha="right")
    ax.set_title("Normalized multimodal state map")
    cbar = fig.colorbar(im, ax=ax, fraction=0.025)
    cbar.set_label("Column-normalized value")
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def write_key_numbers(data: pd.DataFrame, output_path: Path) -> None:
    lines = []
    for case, group in data.groupby("case_label", sort=False):
        low = group.iloc[0]
        high = group.iloc[-1]
        lines.append(f"{case}")
        lines.append(
            f"  heat flux range: {group['heat_flux_mean_w_cm2'].min():.2f} to "
            f"{group['heat_flux_mean_w_cm2'].max():.2f} W/cm2"
        )
        lines.append(
            f"  vapor area fraction range: {group['vapor_area_fraction_mean'].min():.3f} to "
            f"{group['vapor_area_fraction_mean'].max():.3f}"
        )
        lines.append(
            f"  first state {low['state_label']}: vapor={low['vapor_area_fraction_mean']:.3f}, "
            f"AE energy rate={low['ae_abs_energy_rate']:.1f}"
        )
        lines.append(
            f"  final state {high['state_label']}: vapor={high['vapor_area_fraction_mean']:.3f}, "
            f"AE energy rate={high['ae_abs_energy_rate']:.1f}"
        )
    output_path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
