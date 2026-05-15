# BubbleID-Flow

Adaptation workspace for segmenting bubbles in flow boiling images.

## Purpose

BubbleID was developed for pool boiling imagery. This repository keeps the first goal simple:
segment bubbles in flow boiling frames. It adds:

- flow-channel region-of-interest preprocessing
- support for high-speed `.bmp` image sequences
- COCO-format annotation utilities
- Detectron2 Mask R-CNN fine-tuning configs
- validation scripts focused on bubble masks and engineering metrics

## Starting Dataset

Representative local source folder:

```text
C:\Users\hanhu\Box\NED3_Share\Ishraq Hossain\CWRU\test17_17th Oct_Friday\Test17_Flow_Loop_and_Imaging\Images
```

This path is intentionally documented but not tracked. Raw lab images should remain outside git unless a small approved sample set is created.

## Planned Workflow

1. Crop flow boiling frames to the channel/bubble region.
2. Run the baseline OpenCV segmentation to inspect the problem quickly.
3. Select a balanced annotation pilot set across visual conditions.
4. Label bubble instances and export to COCO JSON.
5. Fine-tune Mask R-CNN from BubbleID or COCO weights.
6. Evaluate segmentation quality on held-out operating conditions.

## Quick Start

Set `PYTHONPATH` so scripts can import the package:

```powershell
$env:PYTHONPATH="src"
```

Crop a few representative frames:

```powershell
python scripts/prepare_dataset.py `
  "C:\path\to\raw\Images" `
  "data\processed\cropped" `
  --roi 0,500,1024,80 `
  --limit 25
```

Run the baseline segmentation and save masks plus overlays:

```powershell
python scripts/predict_baseline.py `
  "C:\path\to\raw\Images\25gs_20C\57.5" `
  "outputs\baseline_25gs_57p5" `
  --roi 0,500,1024,80 `
  --limit 25
```

Sample frames for manual annotation:

```powershell
python scripts/sample_frames.py `
  "data\processed\cropped" `
  "data\processed\annotation_sample" `
  --count 100
```

The baseline segmentation is only a visual triage tool. The intended production
model is a fine-tuned instance segmentation model trained from manually labeled
flow-boiling masks.

## Repository Layout

```text
configs/              Detectron2 and experiment configs
docs/                 Dataset, labeling, and adaptation notes
notebooks/            Exploratory analysis notebooks
scripts/              CLI entry points for preprocessing/training/evaluation
src/bubbleid_flow/    Reusable package code
tests/                Unit tests for non-model utility code
```

## Status

Initial segmentation utilities. No raw data, model weights, or generated masks are tracked.
