from __future__ import annotations

import argparse

from bubbleid_flow.coco import labelme_to_coco
from bubbleid_flow.preprocess import parse_roi


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert Labelme bubble annotations to COCO JSON.")
    parser.add_argument("--annotation-root", action="append", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--holdout-every", type=int, default=5)
    parser.add_argument("--roi", default=None, help="Optional crop ROI formatted as x,y,width,height")
    args = parser.parse_args()

    train_json, val_json = labelme_to_coco(
        args.annotation_root,
        args.output_dir,
        holdout_every=args.holdout_every,
        roi=parse_roi(args.roi) if args.roi else None,
    )
    print(f"Wrote {train_json}")
    print(f"Wrote {val_json}")


if __name__ == "__main__":
    main()
