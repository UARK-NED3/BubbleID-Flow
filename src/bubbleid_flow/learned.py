from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from skimage import filters, measure, morphology


@dataclass(frozen=True)
class PixelGaussianModel:
    feature_names: tuple[str, ...]
    foreground_mean: list[float]
    foreground_std: list[float]
    background_mean: list[float]
    background_std: list[float]
    foreground_prior: float
    threshold: float
    roi: tuple[int, int, int, int] | None
    min_area_px: int = 20
    clear_top_px: int = 6

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "PixelGaussianModel":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("roi") is not None:
            data["roi"] = tuple(data["roi"])
        data["feature_names"] = tuple(data["feature_names"])
        data.setdefault("clear_top_px", 6)
        return cls(**data)


def extract_features(gray: np.ndarray) -> tuple[np.ndarray, tuple[str, ...]]:
    """Extract per-pixel features for bubble/background appearance modeling."""
    gray = gray.astype(np.float32)
    gray = np.clip(gray, 0.0, 1.0)
    local_mean = ndi.uniform_filter(gray, size=17)
    dark_contrast = np.clip(local_mean - gray, 0.0, 1.0)
    edge = filters.sobel(gray).astype(np.float32)
    blackhat = morphology.black_tophat(gray, morphology.disk(7)).astype(np.float32)
    y_coord = np.linspace(0.0, 1.0, gray.shape[0], dtype=np.float32)[:, None]
    y_coord = np.broadcast_to(y_coord, gray.shape)

    features = np.stack([gray, dark_contrast, edge, blackhat, y_coord], axis=-1)
    names = ("gray", "dark_contrast", "edge", "blackhat", "y")
    return features, names


def fit_pixel_gaussian(
    images: list[np.ndarray],
    masks: list[np.ndarray],
    *,
    roi: tuple[int, int, int, int] | None = None,
    max_pixels_per_class: int = 300_000,
    threshold: float = 0.50,
    min_area_px: int = 20,
    seed: int = 7,
) -> PixelGaussianModel:
    """Fit a diagonal Gaussian foreground/background pixel classifier."""
    rng = np.random.default_rng(seed)
    foreground: list[np.ndarray] = []
    background: list[np.ndarray] = []
    feature_names: tuple[str, ...] | None = None

    for gray, mask in zip(images, masks, strict=True):
        gray_roi, mask_roi = _apply_roi(gray, mask, roi)
        features, names = extract_features(gray_roi)
        feature_names = names
        flat_features = features.reshape(-1, features.shape[-1])
        flat_mask = mask_roi.reshape(-1)

        fg = flat_features[flat_mask]
        bg = flat_features[~flat_mask]
        if len(fg):
            foreground.append(_sample_rows(fg, max_pixels_per_class // max(1, len(images)), rng))
        if len(bg):
            background.append(_sample_rows(bg, max_pixels_per_class // max(1, len(images)), rng))

    if not foreground or not background:
        raise ValueError("Training requires at least one foreground and one background pixel")

    fg_all = np.concatenate(foreground, axis=0)
    bg_all = np.concatenate(background, axis=0)
    eps = 1e-4

    return PixelGaussianModel(
        feature_names=feature_names or (),
        foreground_mean=fg_all.mean(axis=0).tolist(),
        foreground_std=(fg_all.std(axis=0) + eps).tolist(),
        background_mean=bg_all.mean(axis=0).tolist(),
        background_std=(bg_all.std(axis=0) + eps).tolist(),
        foreground_prior=float(len(fg_all) / (len(fg_all) + len(bg_all))),
        threshold=threshold,
        roi=roi,
        min_area_px=min_area_px,
    )


def predict_probability(gray: np.ndarray, model: PixelGaussianModel) -> np.ndarray:
    """Predict foreground probability for an image or ROI."""
    gray_roi, _ = _apply_roi(gray, None, model.roi)
    features, _ = extract_features(gray_roi)
    flat = features.reshape(-1, features.shape[-1])

    fg_mean = np.asarray(model.foreground_mean)
    fg_std = np.asarray(model.foreground_std)
    bg_mean = np.asarray(model.background_mean)
    bg_std = np.asarray(model.background_std)

    log_fg = _diag_gaussian_logpdf(flat, fg_mean, fg_std) + np.log(model.foreground_prior + 1e-9)
    log_bg = _diag_gaussian_logpdf(flat, bg_mean, bg_std) + np.log(1.0 - model.foreground_prior + 1e-9)
    prob = 1.0 / (1.0 + np.exp(np.clip(log_bg - log_fg, -60, 60)))
    return prob.reshape(gray_roi.shape)


def predict_mask(gray: np.ndarray, model: PixelGaussianModel) -> np.ndarray:
    """Predict a cleaned binary bubble mask."""
    prob = predict_probability(gray, model)
    mask = prob >= model.threshold
    if model.clear_top_px > 0:
        mask[: model.clear_top_px, :] = False
    mask = morphology.binary_closing(mask, morphology.disk(1))
    mask = morphology.remove_small_objects(mask, min_size=model.min_area_px)
    mask = remove_wall_line_components(mask)
    return mask


def remove_wall_line_components(mask: np.ndarray) -> np.ndarray:
    """Remove wide, shallow components that usually come from channel wall lines."""
    labels = measure.label(mask)
    clean = mask.copy()
    max_width = 0.80 * mask.shape[1]
    for region in measure.regionprops(labels):
        min_row, min_col, max_row, max_col = region.bbox
        width = max_col - min_col
        height = max_row - min_row
        if width >= max_width and height <= 12:
            clean[labels == region.label] = False
    return clean


def overlay_mask(rgb: np.ndarray, mask: np.ndarray, alpha: float = 0.45) -> np.ndarray:
    """Overlay a red mask and green boundaries on RGB image data."""
    out = rgb.copy().astype(np.float32)
    red = np.zeros_like(out)
    red[..., 0] = 255
    out[mask] = (1 - alpha) * out[mask] + alpha * red[mask]

    contours = measure.find_contours(mask.astype(float), level=0.5)
    for contour in contours:
        rows = np.clip(np.round(contour[:, 0]).astype(int), 0, out.shape[0] - 1)
        cols = np.clip(np.round(contour[:, 1]).astype(int), 0, out.shape[1] - 1)
        out[rows, cols] = np.array([0, 255, 80])
    return np.clip(out, 0, 255).astype(np.uint8)


def iou_score(prediction: np.ndarray, target: np.ndarray) -> float:
    """Compute binary intersection-over-union."""
    prediction = prediction.astype(bool)
    target = target.astype(bool)
    union = np.logical_or(prediction, target).sum()
    if union == 0:
        return 1.0
    return float(np.logical_and(prediction, target).sum() / union)


def _diag_gaussian_logpdf(x: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    z = (x - mean) / std
    return -0.5 * np.sum(z * z + 2 * np.log(std) + np.log(2 * np.pi), axis=1)


def _sample_rows(rows: np.ndarray, count: int, rng: np.random.Generator) -> np.ndarray:
    if len(rows) <= count:
        return rows
    indices = rng.choice(len(rows), size=count, replace=False)
    return rows[indices]


def _apply_roi(
    gray: np.ndarray, mask: np.ndarray | None, roi: tuple[int, int, int, int] | None
) -> tuple[np.ndarray, np.ndarray | None]:
    if roi is None:
        return gray, mask
    x, y, width, height = roi
    gray_roi = gray[y : y + height, x : x + width]
    mask_roi = None if mask is None else mask[y : y + height, x : x + width]
    return gray_roi, mask_roi
