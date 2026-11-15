# Manuscript Reproducibility Map

## Scope and source of truth

The public data release for *BubbleID-Flow: Machine-Vision Quantification of
Vapor Area Fraction in Subcooled Flow Boiling* is Zenodo record
[10.5281/zenodo.22235802](https://doi.org/10.5281/zenodo.22235802). It contains
the raw optical sequences, annotations, thermal and AE inputs, and the released
Mask R-CNN checkpoint. The GitHub repository contains the analysis and figure
scripts, manuscript source, small derived tables, and tests.

The released checkpoint is `ModelWeights/model_final.pth` with SHA-256
`6F60969CE876F57A78B53FC61895C99B92CB2E1B6F0E0B30F01FA301236042CD` and
Detectron2 iteration `1999`. Use the manuscript inference settings in every
rerun: ROI `0,485,1024,70`, score threshold `0.30`, and detection cap `300`.
The earlier checkpoint with SHA-256 beginning `10613...` is a legacy artifact
and must not be used for the manuscript results.

## What is and is not directly reproducible today

| Artifact | Status | Interpretation |
| --- | --- | --- |
| `outputs/aug9_model_analysis/canonical/aug9_state_vapor_area_fraction.csv` | Releasable derived data | The 37 manuscript state values exported from Abrar's August worksheet. Each row records the worksheet and checkpoint hashes. It is an archived state table, not a new all-state inference run. |
| `outputs/aug9_model_analysis/aug9_temporal_vapor_fraction_45V.csv` and `aug9_temporal_summary_45V.csv` | Direct inference evidence | Four 45 V sequences, 391 frames total, were inferred with the released checkpoint. The `25gs_20C/45 V` direct mean is `0.013777`; the archived worksheet value is `0.014231`. |
| `outputs/aug9_model_analysis/full_sequences/` | Partial direct inference | Three 5 g/s states only. These files are not evidence for a full 37-state reproduction. |
| `outputs/multimodal/` | Legacy June exploratory output | It predates the August checkpoint and does not store a model hash. Its `vapor_area_fraction_mean` must not be used for the manuscript figures or values. |

The August worksheet `values_vf_bc.xlsx` was available in the local manuscript
workspace but was omitted from the Zenodo v1 archive. The canonical CSV above
is its public, checksum-recorded derivative. A future Zenodo version should add
the original worksheet or an equivalent state-level derived-data package with
this provenance manifest.

The release does not contain a frozen file-level 104/26 split manifest, original
training trace, random seed, augmentation record, or checkpoint-selection
history. The 26-image result is therefore a same-sequence reconstruction
evaluation, not an experiment-held-out generalization result.

## Regenerate the canonical state table

Set the data root to an unpacked Zenodo record. The command below records the
released checkpoint hash in every output row and does not modify raw data.

```powershell
$env:PYTHONPATH = 'src;.'
$dataRoot = 'D:\ned3-018_BubbleID-Flow\ned3-018_BubbleID-Flow'

C:\Users\hanhu\Anaconda3\envs\bubbleid\python.exe `
  scripts\export_aug9_vapor_area_fraction.py `
  --values-workbook 'C:\path\to\values_vf_bc.xlsx' `
  --checkpoint "$dataRoot\ModelWeights\model_final.pth" `
  --output-dir outputs\aug9_model_analysis\canonical
```

The original worksheet is currently needed for this export. A reader without
that file can use the committed canonical CSV for the manuscript figures, but
cannot recreate the CSV itself until the source worksheet is added to a revised
archive.

## Regenerate the 45 V direct-inference check and Figures 4--7

The state table and the released raw images are sufficient to rerun the direct
45 V check and the manuscript plotting workflow. The `combined-summary` input
is thermal/AE context only; its legacy optical area column is discarded by the
current figure-preparation script.

```powershell
$env:PYTHONPATH = 'src;.'
$dataRoot = 'D:\ned3-018_BubbleID-Flow\ned3-018_BubbleID-Flow'
$py = 'C:\Users\hanhu\Anaconda3\envs\bubbleid\python.exe'

& $py scripts\prepare_aug9_optical_results.py `
  --state-vapor-table outputs\aug9_model_analysis\canonical\aug9_state_vapor_area_fraction.csv `
  --combined-summary outputs\multimodal\cross_case_synthesis\combined_multimodal_state_summary.csv `
  --image-root "$dataRoot\MultimodalData\Images" `
  --weights "$dataRoot\ModelWeights\model_final.pth" `
  --output-dir tmp\aug9_regeneration `
  --roi 0,485,1024,70 `
  --score-threshold 0.30 `
  --detections-per-image 300

& $py scripts\analyze_optical_thermal_association.py `
  --optical-summary outputs\aug9_model_analysis\canonical\aug9_state_vapor_area_fraction.csv `
  --thermal-summary outputs\aug9_model_analysis\thermal_audit\thermal_state_audit.csv `
  --temporal-summary tmp\aug9_regeneration\aug9_temporal_summary_45V.csv `
  --output-dir tmp\aug9_regeneration\optical_thermal_association
```

To create a genuine all-state rerun rather than using the archived worksheet,
run the following command. It processes all raw frames and will be materially
slower than the 45 V check. Compare its 37-state output with the canonical
table before replacing any reported result.

```powershell
& $py scripts\analyze_full_state_sequences.py `
  --image-root "$dataRoot\MultimodalData\Images" `
  --weights "$dataRoot\ModelWeights\model_final.pth" `
  --output-dir tmp\aug9_full_state_rerun `
  --roi 0,485,1024,70 `
  --score-threshold 0.30 `
  --detections-per-image 300
```

## Figure-script map

| Manuscript result | Script | Primary inputs |
| --- | --- | --- |
| Segmentation evaluation and robustness figure | `scripts/evaluate_detectron2.py`; `scripts/analyze_segmentation_robustness.py` | COCO annotations, released checkpoint, 26-image internal holdout predictions |
| State vapor-area-fraction and 45 V agreement figures | `scripts/export_aug9_vapor_area_fraction.py`; `scripts/prepare_aug9_optical_results.py` | August state table, raw images, released checkpoint |
| Segmentation baseline figure | `scripts/evaluate_segmentation_baselines.py` | holdout masks and predictions |
| Optical--thermal association figure | `scripts/analyze_optical_thermal_association.py` | canonical optical table, thermal state audit, 45 V direct-inference summary |

Run `python -m pytest` after a code change.
The manuscript and figure package should be audited separately before a
submission build.
