from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from bubbleid_flow.labelme import BUBBLE_LABELS, find_labelme_jsons


def labelme_to_coco(
    annotation_roots: list[str | Path],
    output_dir: str | Path,
    *,
    holdout_every: int = 5,
    roi: tuple[int, int, int, int] | None = None,
) -> tuple[Path, Path]:
    """Convert Labelme bubble polygons into train/validation COCO JSON files."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    json_paths = find_labelme_jsons(annotation_roots)
    if not json_paths:
        raise RuntimeError("No Labelme JSON files found")

    train_items: list[Path] = []
    val_items: list[Path] = []
    for index, json_path in enumerate(json_paths):
        if index % holdout_every == 0:
            val_items.append(json_path)
        else:
            train_items.append(json_path)

    if not train_items or not val_items:
        raise RuntimeError("Need at least one train and one validation annotation")

    train_json = output_dir / "train_coco.json"
    val_json = output_dir / "val_coco.json"
    train_json.write_text(
        json.dumps(_build_coco(train_items, output_dir / "train_images", roi), indent=2),
        encoding="utf-8",
    )
    val_json.write_text(
        json.dumps(_build_coco(val_items, output_dir / "val_images", roi), indent=2),
        encoding="utf-8",
    )
    return train_json, val_json


def _build_coco(
    json_paths: list[Path],
    image_output_dir: Path,
    roi: tuple[int, int, int, int] | None,
) -> dict:
    images = []
    annotations = []
    annotation_id = 1
    if roi is not None:
        image_output_dir.mkdir(parents=True, exist_ok=True)

    for image_id, json_path in enumerate(json_paths, start=1):
        data = json.loads(json_path.read_text(encoding="utf-8"))
        width = int(data["imageWidth"])
        height = int(data["imageHeight"])
        image_path = json_path.parent / data.get("imagePath", json_path.with_suffix(".bmp").name)
        if not image_path.exists():
            raise FileNotFoundError(f"Missing image for annotation {json_path}: {image_path}")

        coco_image_path = image_path
        if roi is not None:
            x, y, roi_width, roi_height = roi
            with Image.open(image_path) as image:
                image.crop((x, y, x + roi_width, y + roi_height)).save(
                    image_output_dir / f"{image_path.stem}.png"
                )
            coco_image_path = image_output_dir / f"{image_path.stem}.png"
            width = roi_width
            height = roi_height

        images.append(
            {
                "id": image_id,
                "file_name": str(coco_image_path.resolve()),
                "width": width,
                "height": height,
            }
        )

        for shape in data.get("shapes", []):
            label = str(shape.get("label", "")).strip().lower()
            if label not in BUBBLE_LABELS:
                continue
            points = shape.get("points", [])
            if len(points) < 3:
                continue

            polygon = [(float(x), float(y)) for x, y in points]
            if roi is not None:
                polygon = _shift_polygon_to_roi(polygon, roi)
                if polygon is None:
                    continue
            flat = [coord for point in polygon for coord in point]
            bbox = _bbox(polygon)
            area = abs(_polygon_area(polygon))
            if area <= 1.0 or bbox[2] <= 1.0 or bbox[3] <= 1.0:
                continue

            annotations.append(
                {
                    "id": annotation_id,
                    "image_id": image_id,
                    "category_id": 1,
                    "segmentation": [flat],
                    "bbox": bbox,
                    "area": area,
                    "iscrowd": 0,
                }
            )
            annotation_id += 1

    return {
        "info": {
            "description": "BubbleID-Flow Labelme annotations converted to COCO",
            "version": "0.1.0",
        },
        "licenses": [],
        "images": images,
        "annotations": annotations,
        "categories": [{"id": 1, "name": "bubble", "supercategory": "bubble"}],
    }


def _bbox(points: list[tuple[float, float]]) -> list[float]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    x_min = min(xs)
    y_min = min(ys)
    return [x_min, y_min, max(xs) - x_min, max(ys) - y_min]


def _polygon_area(points: list[tuple[float, float]]) -> float:
    area = 0.0
    for index, (x1, y1) in enumerate(points):
        x2, y2 = points[(index + 1) % len(points)]
        area += x1 * y2 - x2 * y1
    return 0.5 * area


def _shift_polygon_to_roi(
    points: list[tuple[float, float]],
    roi: tuple[int, int, int, int],
) -> list[tuple[float, float]] | None:
    x, y, width, height = roi
    shifted = [(px - x, py - y) for px, py in points]
    if all(px < 0 or px > width or py < 0 or py > height for px, py in shifted):
        return None
    clipped = [
        (min(max(px, 0.0), float(width)), min(max(py, 0.0), float(height)))
        for px, py in shifted
    ]
    if len(set(clipped)) < 3:
        return None
    return clipped
