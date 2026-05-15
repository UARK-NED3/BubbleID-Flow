# BubbleID-Flow

Adaptation workspace for using BubbleID-style instance segmentation on flow boiling images.

## Purpose

BubbleID was developed for pool boiling imagery. This repository extends that workflow to flow boiling by adding:

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
2. Select a balanced annotation pilot set across flow rates, temperatures, and visual failure modes.
3. Label bubble instances and export to COCO JSON.
4. Fine-tune Mask R-CNN from BubbleID or COCO weights.
5. Evaluate segmentation quality and derived metrics on held-out operating conditions.

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

Initial scaffold. No raw data, model weights, or generated masks are tracked yet.
