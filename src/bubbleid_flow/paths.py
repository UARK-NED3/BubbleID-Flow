from pathlib import Path


IMAGE_EXTENSIONS = (".bmp", ".jpg", ".jpeg", ".png", ".tif", ".tiff")


def iter_images(root: str | Path) -> list[Path]:
    """Return image paths under root, sorted for reproducible frame order."""
    root = Path(root)
    return sorted(path for path in root.rglob("*") if path.suffix.lower() in IMAGE_EXTENSIONS)
