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

## Manuscript Reproducibility

The current multimodal manuscript outputs use the Box-hosted model folder:

```text
C:\Users\hanhu\Box\NED3_Share\0_BubbleID\BubbleID-Flow\detectron2_flow_mrcnn_roi485_70
```

Raw optical, thermal, and acoustic data remain outside git under the CWRU Test
17 Box folder. See [docs/manuscript_reproducibility.md](docs/manuscript_reproducibility.md)
for the exact data inventory and rerun instructions.

To recreate the tracked four-case manuscript summaries and figures:

```powershell
.\scripts\run_multimodal_manuscript_cases.ps1
```

The cross-case synthesis writes `cross_case_trend_summary.csv` with the
rank-agreement checks used to support optical/thermal and quality-gated AE
claims in the manuscript. It also writes `cross_case_trend_sensitivity.csv`
with leave-one-state-out checks that flag state-sensitive AE conclusions.
It now also writes `cross_case_sampling_uncertainty.csv`, which recomputes
sampled-frame confidence intervals from the per-frame image metrics and flags
states where short image samples or wide intervals weaken state-level optical
claims.
It also writes `cross_case_active_threshold_sensitivity.csv`, which audits
whether active vapor length changes materially when the projected-vapor column
threshold is swept around the manuscript value. Existing tracked frame metrics
predate that sweep, so the current artifact gates the claim until the
Detectron2-backed per-case image analyses are rerun.
It also writes `cross_case_segmentation_validation_plan.csv`, which selects
held-out manual-mask target states across onset or low-vapor, developed,
high-vapor or CHF-adjacent, and high-uncertainty conditions. This is a worklist,
not completed validation evidence; individual bubble statistics remain blocked
until those masks and evaluation metrics are archived.
It also writes `cross_case_thermal_response_checks.csv`, which audits the
reduced thermal context used in the figures. Current tracked outputs support
state-level heat-flux and mean-HTC interpretation, but they still do not
validate local optical-thermal registration or full HTC uncertainty.
It also writes `cross_case_ae_evidence_tiers.csv`, which converts AE-window
quality, pass-level window counts, overlap blockers, and sensitivity checks into
a case-level acoustic claim scope. Current tracked AE correlations should be
treated as screening diagnostics until trigger synchronization and sensor
coupling are verified.
It also writes `cross_case_ae_readiness_matrix.csv`, which applies stricter
acceptance criteria for quantitative AE interpretation: pass-quality windows,
nonblocked state coverage, contiguous-window provenance, trigger verification,
and sensor-coupling verification. Current tracked outputs have zero
quantitative-ready AE cases, so acoustic statements remain screening-only.
It also writes `cross_case_ae_verification_status.csv` and
`cross_case_ae_remediation_plan.csv`. The verification table records whether
case-level trigger synchronization and AE sensor coupling have been supplied,
and the remediation plan ranks the contiguous-window reruns and waveform/sensor
checks needed before AE language can be strengthened.
It also writes `cross_case_claim_evidence_matrix.csv`, which converts the
trend, sampling-uncertainty, thermal-response, AE evidence-tier, and AE
readiness artifacts into a manuscript claim-scope gate. Current tracked outputs
support optical heat-flux trend language and state-level thermal-context
language with limits, restrict AE to quality-tagged screening comparisons, and
block AE classifier/timing, individual bubble-statistic, and local
optical-thermal registration claims until validation artifacts exist.
The ATE package audit now enforces those unsupported claim rows against
`main.tex`, so stronger wording becomes a submission blocker instead of only a
prose caveat.
The small cross-case synthesis CSV/TXT/PNG artifacts under
`outputs/multimodal/cross_case_synthesis` are intentionally versionable because
the manuscript, validation audit, and ATE package audit use them as evidence
gates. Raw data, model weights, generated masks, and bulky intermediate outputs
remain ignored.

The Applied Thermal Engineering submission draft, Overleaf source, highlights,
cover letter, bibliography, graphical abstract, and figure files are in:

```text
overleaf_applied_thermal_engineering
```

See [docs/applied_thermal_engineering_submission_notes.md](docs/applied_thermal_engineering_submission_notes.md)
for the submission package inventory and verification checklist.

Run manuscript validation and package audits with:

```powershell
$env:PYTHONPATH="src"
python scripts\audit_manuscript_validation.py
python scripts\audit_ate_submission_package.py
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

Trained model weights are archived on OSF:

- OSF project: https://osf.io/xnkh6/
- Model folder: `models/detectron2_flow_mrcnn_roi485_70/`
- Direct weights download: https://osf.io/download/6a2a2e8f09f1e3d2a3d14dae/
- Additional OSF record saved by Abrar Hoq Fahim for the fine-tuned
  flow-boiling image model weights: [OSF view-only record](https://osf.io/xnkh6/overview?view_only=09d63d516ca0489e90fa9b94d37b529e).
- A controlled local copy of the same saved checkpoint is maintained at:

  ```text
  C:\Users\hanhu\Box\NED3_Share\0_Manuscripts\Fahim-2026-BubbleID-Flow\model_final.pth
  ```

  The checkpoint is intentionally not tracked in Git. Verify its SHA256 before
  inference or figure regeneration.
- Abrar's manually annotated flow-boiling images are maintained outside Git at:

  ```text
  C:\Users\hanhu\Box\NED3_Share\0_Manuscripts\Fahim-2026-BubbleID-Flow\Annotation_Dataset
  ```

  This is the annotation provenance for the fine-tuning dataset. It is a
  controlled local research-data location, not a versioned repository asset.
- Original public-archive `model_final.pth` SHA256:
  `10613DE030B35637BECB4FDA524F8D829E9B77B25E90AB9A670992E8A9B4B166`
- Aug. 9, 2026 local `model_final.pth` SHA256 from Abrar's fine-tuned package:
  `6F60969CE876F57A78B53FC61895C99B92CB2E1B6F0E0B30F01FA301236042CD`

The repo-tracked model artifact manifest is
`docs/model_artifact_manifest.csv`. It records the public weight archive and
checksum used by the manuscript validation audit. Evaluation metrics and
held-out manual-mask validation remain pending before instance-level bubble
statistics should be claimed.

For the Figure 5 same-sequence holdout, the robustness workflow also writes
`outputs/aug9_model_analysis/segmentation_robustness/segmentation_evaluation_image_groups.csv`.
It identifies each of the 26 evaluation images, its original COCO path, manual
and predicted projected coverage, overlap metrics, and the manual-coverage group
used in the manuscript: low (`<= 0.05`), intermediate (`0.05--0.15`), or high
(`> 0.15`).

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
  --detections-per-image 300 `
  --limit 12
```

The predictor writes binary masks, red mask overlays, and instance-level
visualizations. Use the ROI-aware Mask R-CNN path for real bubble segmentation;
the earlier pixel model is retained only as a lightweight diagnostic baseline.
For dense small-bubble states in the Aug. 9, 2026 fine-tuned package, use
`--detections-per-image 300`; Detectron2's default cap of 100 instances can
truncate detections and bias projected vapor fraction low.

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
  --score-threshold 0.30 `
  --detections-per-image 300
```

This produces the cropped ROI image, binary bubble mask, mask overlay, profile
CSV, and profile plot. The metric is a 2D projected vapor area fraction from the
camera view, not a calibrated 3D void fraction.

## Total Vapor Fraction and Bubble Statistics
Once instance masks are available, the segmented entities are enumerated for 
bubble count, and the total mask pixel area is divided by ROI domain to yield the vapor fraction.

```powershell
python scripts/vapor_fraction_and_bubble_count.py `
  "C:\path\to\raw\Images\25gs_20C\57.5" `
  "outputs\vf_and_bc\case_name_frame" `
  --weights "outputs\detectron2_flow_mrcnn_roi485_70\model_final.pth" `
  --roi 0,485,1024,70 `
  --score-threshold 0.30 `
  --cluster-size-threshold 350 `
  --device cpu
```
The results are saved to a CSV file containing the total vapor fraction, total bubble 
count, number of clustered bubbles, and number of single bubbles. Additionally,
cropped overlay images are generated, showing each detected bubble outlined and labeled
with a unique identification number for visual verification.

## Ground-Truth Vapor Fraction and Bubble Count Calculation
This script requires a folder containing manually annotated `.bmp` images with
their corresponding `.json` labelme annotation files placed side by side. 
It calculates the vapor fraction from the ratio of bubble-pixel area to ROI area
and determines the total bubble count for the specified annotation class.

```powershell
python scripts/annotation_to_ground_truth.py `
  "C:\path\to\test_images" `
  --roi 0,485,1024,70 `
  --output-dir "outputs\groundTruth"
```

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

**Under development.** BubbleID-Flow is an ongoing extension of the original
**BubbleID** framework for bubble identification and analysis under
flow-boiling conditions. This repository tracks the software, manuscript
evidence artifacts, and reproducibility documentation; raw data, model weights,
and generated masks remain outside Git.
