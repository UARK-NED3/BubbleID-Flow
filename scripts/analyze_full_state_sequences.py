from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch
from detectron2.engine import DefaultPredictor

from bubbleid_flow.paths import iter_images
from bubbleid_flow.preprocess import crop_array, parse_roi
from bubbleid_flow.time_series import circular_moving_block_bootstrap_mean_interval
from bubbleid_flow.vapor_fraction import projected_mask_metrics
from scripts.analyze_multimodal_case import discover_states, overlay_combined_mask
from scripts.evaluate_detectron2 import build_cfg


CASE_ORDER = ("5gs_22C", "10gs_22C", "15gs_20C", "25gs_20C")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process every raw frame in every BubbleID-Flow operating state."
    )
    parser.add_argument("--image-root", required=True)
    parser.add_argument("--weights", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--roi", default="0,485,1024,70")
    parser.add_argument("--score-threshold", type=float, default=0.30)
    parser.add_argument("--detections-per-image", type=int, default=300)
    parser.add_argument("--frame-rate-hz", type=float, default=3000.0)
    parser.add_argument("--bootstrap-samples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    representatives = output_dir / "representative_assets"
    representatives.mkdir(exist_ok=True)
    frame_path = output_dir / "full_sequence_frame_metrics.csv"
    state_path = output_dir / "full_sequence_state_summary.csv"

    prior = pd.read_csv(frame_path) if args.resume and frame_path.exists() else pd.DataFrame()
    completed = set()
    if not prior.empty:
        completed = set(zip(prior["case_label"], prior["state_label"], strict=False))
        print(f"Resuming with {len(prior)} frames from {len(completed)} completed states", flush=True)

    predictor = DefaultPredictor(
        build_cfg(
            weights=args.weights,
            score_threshold=args.score_threshold,
            detections_per_image=args.detections_per_image,
            device=args.device,
        )
    )
    roi = parse_roi(args.roi)
    all_frames = [prior] if not prior.empty else []

    for case in CASE_ORDER:
        case_dir = Path(args.image_root) / case
        for state in discover_states(case_dir):
            key = (case, state["state_label"])
            if key in completed:
                continue
            image_paths = iter_images(state["path"])
            rows = []
            representative_index = len(image_paths) // 2
            print(f"Processing {case}/{state['state_label']}: {len(image_paths)} frames", flush=True)
            for frame_index, image_path in enumerate(image_paths):
                image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
                if image is None:
                    raise ValueError(f"Could not read image: {image_path}")
                cropped = crop_array(image, roi)
                predicted = predictor(cropped)["instances"].to("cpu")
                masks = (
                    predicted.pred_masks.numpy()
                    if predicted.has("pred_masks")
                    else np.empty((0, *cropped.shape[:2]), dtype=bool)
                )
                combined = (
                    np.any(masks, axis=0).astype(np.uint8) * 255
                    if len(masks)
                    else np.zeros(cropped.shape[:2], dtype=np.uint8)
                )
                metrics = projected_mask_metrics(combined)
                instances = int(len(predicted))
                rows.append(
                    {
                        "case_label": case,
                        "state_label": state["state_label"],
                        "state_voltage": state["state_voltage"],
                        "frame_index": frame_index,
                        "time_ms": 1000.0 * frame_index / args.frame_rate_hz,
                        "frame_name": image_path.name,
                        "vapor_area_fraction": metrics["vapor_area_fraction"],
                        "active_length_fraction": metrics["active_length_fraction"],
                        "predicted_instances": instances,
                    }
                )
                if frame_index == representative_index:
                    stem = f"{case}_{safe_name(state['state_label'])}"
                    cv2.imwrite(str(representatives / f"{stem}_roi.png"), cropped)
                    cv2.imwrite(str(representatives / f"{stem}_mask.png"), combined)
                    cv2.imwrite(
                        str(representatives / f"{stem}_overlay.png"),
                        overlay_combined_mask(cropped, combined),
                    )

            all_frames.append(pd.DataFrame(rows))
            combined_frames = pd.concat(all_frames, ignore_index=True)
            combined_frames.to_csv(frame_path, index=False)
            write_state_summary(
                combined_frames,
                state_path,
                bootstrap_samples=args.bootstrap_samples,
                seed=args.seed,
            )
            print(f"Checkpointed {len(combined_frames)} frames", flush=True)

    frame_metrics = pd.concat(all_frames, ignore_index=True)
    state_summary = write_state_summary(
        frame_metrics,
        state_path,
        bootstrap_samples=args.bootstrap_samples,
        seed=args.seed,
    )
    manifest = {
        "image_root": str(Path(args.image_root).resolve()),
        "weights": str(Path(args.weights).resolve()),
        "weights_sha256": sha256(Path(args.weights)),
        "roi": args.roi,
        "score_threshold": args.score_threshold,
        "detections_per_image": args.detections_per_image,
        "frame_rate_hz": args.frame_rate_hz,
        "bootstrap_samples": args.bootstrap_samples,
        "frames": int(len(frame_metrics)),
        "states": int(len(state_summary)),
        "cases": list(CASE_ORDER),
    }
    (output_dir / "full_sequence_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"Wrote {frame_path}", flush=True)
    print(f"Wrote {state_path}", flush=True)


def write_state_summary(
    frame_metrics: pd.DataFrame,
    path: Path,
    *,
    bootstrap_samples: int,
    seed: int,
) -> pd.DataFrame:
    rows = []
    grouped = frame_metrics.groupby(["case_label", "state_label", "state_voltage"], sort=False)
    for group_index, (key, group) in enumerate(grouped):
        values = group["vapor_area_fraction"].to_numpy(dtype=float)
        interval = circular_moving_block_bootstrap_mean_interval(
            values,
            samples=bootstrap_samples,
            seed=seed + group_index,
        )
        lag1 = float(pd.Series(values).autocorr(lag=1)) if len(values) > 2 else np.nan
        rows.append(
            {
                "case_label": key[0],
                "state_label": key[1],
                "state_voltage": key[2],
                "frames": int(len(group)),
                "vapor_area_fraction_mean": float(values.mean()),
                "vapor_area_fraction_std": float(values.std(ddof=1)) if len(values) > 1 else np.nan,
                "vapor_area_fraction_median": float(np.median(values)),
                "vapor_area_fraction_ci95_lower": interval["lower"],
                "vapor_area_fraction_ci95_upper": interval["upper"],
                "lag1_autocorrelation": lag1,
                "tau_int_frames": interval["tau_int_frames"],
                "effective_sample_size": interval["effective_sample_size"],
                "bootstrap_block_length_frames": interval["block_length"],
                "active_length_fraction_mean": float(group["active_length_fraction"].mean()),
                "predicted_instances_mean": float(group["predicted_instances"].mean()),
                "predicted_instances_max": int(group["predicted_instances"].max()),
            }
        )
    result = pd.DataFrame(rows).sort_values(["case_label", "state_voltage"])
    result.to_csv(path, index=False)
    return result


def safe_name(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value).strip("_")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


if __name__ == "__main__":
    main()
