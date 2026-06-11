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

For Detectron2/BubbleID-style fine-tuning, create the tested Windows environment:

```powershell
.\scripts\setup_windows_detectron2_env.ps1
```

See [docs/environment.md](docs/environment.md) for details.

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

## Learned Pixel Model

The first annotation-driven model is a lightweight foreground/background pixel
classifier. It uses Labelme polygons from multiple annotation folders and is a
practical bridge until a Detectron2/BubbleID training environment is available.

Train from Labelme annotations:

```powershell
python scripts/train_pixel_model.py `
  --annotation-root "C:\path\to\student_annotations_1" `
  --annotation-root "C:\path\to\student_annotations_2" `
  --model-out "models\pixel_gaussian_flow_roi490_60.json" `
  --report-out "outputs\evaluation\pixel_gaussian_flow_roi490_60.csv" `
  --examples-out "outputs\evaluation\pixel_gaussian_examples_roi490_60" `
  --roi 0,490,1024,60 `
  --threshold 0.45 `
  --min-area-px 20
```

Run the trained model on new images:

```powershell
python scripts/predict_pixel_model.py `
  "C:\path\to\raw\Images\25gs_20C\57.5" `
  "outputs\showcase\25gs_20C_57p5" `
  --model "models\pixel_gaussian_flow_roi490_60.json" `
  --limit 12
```

This model is not a replacement for Mask R-CNN. It is useful for quick
annotation feedback, sanity checks, and representative segmentation overlays.

## Detectron2 Flow-Boiling Mask R-CNN

Convert Labelme instance polygons to COCO. For the current flow-boiling
annotations, the near-wall bubble band is well represented by `0,485,1024,70`.

```powershell
python scripts/labelme_to_coco.py `
  --annotation-root "C:\path\to\Abrar Hoq Fahim" `
  --annotation-root "C:\path\to\Annotation (Flow Boiling)" `
  --output-dir "data\processed\flow_coco_roi485_70" `
  --holdout-every 5 `
  --roi 0,485,1024,70
```

Fine-tune Mask R-CNN from COCO weights:

```powershell
python scripts/train_detectron2.py `
  --train-json "data\processed\flow_coco_roi485_70\train_coco.json" `
  --val-json "data\processed\flow_coco_roi485_70\val_coco.json" `
  --output-dir "outputs\detectron2_flow_mrcnn_roi485_70" `
  --max-iter 1000 `
  --eval-period 250 `
  --batch-size 1 `
  --base-lr 0.00025
```

Run the trained model on raw flow-boiling images using the same ROI:

```powershell
python scripts/predict_detectron2.py `
  "C:\path\to\raw\Images\25gs_20C\57.5" `
  "outputs\detectron2_showcase\25gs_20C_57p5" `
  --weights "outputs\detectron2_flow_mrcnn_roi485_70\model_final.pth" `
  --roi 0,485,1024,70 `
  --score-threshold 0.30 `
  --limit 12
```

The predictor writes binary masks, red mask overlays, and instance-level
visualizations. Use the ROI-aware Mask R-CNN path for real bubble segmentation;
the earlier pixel model is retained only as a lightweight diagnostic baseline.

## Projected Vapor Area Fraction

Once a bubble mask is available, the cropped channel can be split into
streamwise bins and summarized as projected vapor area fraction:

```text
projected vapor area fraction = bubble mask pixels in bin / total pixels in bin
```

Plot one representative frame:

```powershell
python scripts/plot_vapor_fraction_profile.py `
  "C:\path\to\raw\frame.bmp" `
  "outputs\vapor_fraction\case_name_frame" `
  --weights "outputs\detectron2_flow_mrcnn_roi485_70\model_final.pth" `
  --roi 0,485,1024,70 `
  --bins 64 `
  --score-threshold 0.30
```

This produces the cropped ROI image, binary bubble mask, mask overlay, profile
CSV, and profile plot. The metric is a 2D projected vapor area fraction from the
camera view, not a calibrated 3D void fraction.

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
