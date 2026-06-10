from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


BUBBLE_LABELS = {"bubble", "bubble_cluster"}


@dataclass(frozen=True)
class LabelmeRecord:
    json_path: Path
    image_path: Path
    width: int
    height: int
    mask: np.ndarray
    labels: tuple[str, ...]


def read_labelme_record(json_path: str | Path) -> LabelmeRecord:
    """Read a Labelme JSON file and rasterize bubble polygons into a binary mask."""
    json_path = Path(json_path)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    width = int(data["imageWidth"])
    height = int(data["imageHeight"])
    image_path = json_path.parent / data.get("imagePath", json_path.with_suffix(".bmp").name)

    mask_image = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask_image)
    labels: list[str] = []
    for shape in data.get("shapes", []):
        label = str(shape.get("label", "")).strip().lower()
        if label not in BUBBLE_LABELS:
            continue
        points = shape.get("points", [])
        if len(points) < 3:
            continue
        polygon = [(float(x), float(y)) for x, y in points]
        draw.polygon(polygon, outline=1, fill=1)
        labels.append(label)

    return LabelmeRecord(
        json_path=json_path,
        image_path=image_path,
        width=width,
        height=height,
        mask=np.asarray(mask_image, dtype=bool),
        labels=tuple(labels),
    )


def find_labelme_jsons(roots: list[str | Path]) -> list[Path]:
    """Find Labelme JSON files under one or more annotation roots."""
    paths: list[Path] = []
    for root in roots:
        paths.extend(Path(root).rglob("*.json"))
    return sorted(paths)
