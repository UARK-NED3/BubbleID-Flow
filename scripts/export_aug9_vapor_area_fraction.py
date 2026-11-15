"""Export the archived August state table with explicit provenance.

The 37-state values used by the manuscript were supplied in an August workbook.
They are not a full re-inference of every released raw frame.  This utility
turns that worksheet into a small, versionable table without obscuring that
distinction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


EXPECTED_CASES = ("5gs_22C", "10gs_22C", "15gs_20C", "25gs_20C")
EXPECTED_CHECKPOINT_SHA256 = "6F60969CE876F57A78B53FC61895C99B92CB2E1B6F0E0B30F01FA301236042CD"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export the archived August manuscript vapor-area-fraction state table."
    )
    parser.add_argument("--values-workbook", required=True, type=Path)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--roi", default="0,485,1024,70")
    parser.add_argument("--score-threshold", type=float, default=0.30)
    parser.add_argument("--detections-per-image", type=int, default=300)
    args = parser.parse_args()

    values = read_values_workbook(args.values_workbook)
    checkpoint_sha256 = sha256(args.checkpoint)
    if checkpoint_sha256 != EXPECTED_CHECKPOINT_SHA256:
        raise ValueError(
            "Checkpoint SHA-256 does not match the released August model: "
            f"{checkpoint_sha256}"
        )

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    workbook_sha256 = sha256(args.values_workbook)
    values = values.assign(
        value_provenance="archived_august_workbook",
        values_workbook_sha256=workbook_sha256,
        checkpoint_sha256=checkpoint_sha256,
        roi=args.roi,
        score_threshold=args.score_threshold,
        detections_per_image=args.detections_per_image,
    )
    table_path = output_dir / "aug9_state_vapor_area_fraction.csv"
    values.to_csv(table_path, index=False)

    manifest = {
        "state_table": table_path.name,
        "state_count": int(len(values)),
        "case_count": int(values["case_label"].nunique()),
        "values_workbook": args.values_workbook.name,
        "values_workbook_sha256": workbook_sha256,
        "checkpoint": args.checkpoint.name,
        "checkpoint_sha256": checkpoint_sha256,
        "roi": args.roi,
        "score_threshold": args.score_threshold,
        "detections_per_image": args.detections_per_image,
        "state_value_status": (
            "Archived August state table. It is linked to the released checkpoint "
            "by the documented manuscript configuration, but this export does not "
            "claim a fresh full-state inference."
        ),
        "direct_inference_check": (
            "The separately archived 45 V sequence analysis provides direct "
            "checkpoint inference for four states."
        ),
    }
    (output_dir / "aug9_state_vapor_area_fraction_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Wrote {table_path}")


def read_values_workbook(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path, header=None) if path.suffix.lower() == ".csv" else pd.read_excel(path, header=None)
    marker_rows = raw.index[raw.iloc[:, 0].astype(str).str.strip().str.lower() == "vf"].tolist()
    if len(marker_rows) != 1:
        raise ValueError("Expected exactly one 'vf' section in the values workbook")
    header_row = marker_rows[0]
    voltages = pd.to_numeric(raw.iloc[header_row, 1:], errors="coerce")
    rows: list[dict[str, object]] = []
    for row_index in range(header_row + 1, len(raw)):
        case = str(raw.iloc[row_index, 0]).strip()
        if case.lower() in {"total_bc", "bubble", "bubble_cluster", "nan", ""}:
            break
        values = pd.to_numeric(raw.iloc[row_index, 1:], errors="coerce")
        for voltage, vapor_area_fraction in zip(voltages, values):
            if pd.notna(voltage) and pd.notna(vapor_area_fraction):
                rows.append(
                    {
                        "case_label": case,
                        "state_voltage": float(voltage),
                        "vapor_area_fraction": float(vapor_area_fraction),
                    }
                )
    result = pd.DataFrame(rows).sort_values(["case_label", "state_voltage"], ignore_index=True)
    if tuple(sorted(result["case_label"].unique())) != tuple(sorted(EXPECTED_CASES)):
        raise ValueError(f"Unexpected cases in values workbook: {sorted(result['case_label'].unique())}")
    if len(result) != 37:
        raise ValueError(f"Expected 37 manuscript states, found {len(result)}")
    return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


if __name__ == "__main__":
    main()
