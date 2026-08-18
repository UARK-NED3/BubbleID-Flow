# Aug. 9, 2026 Model Reproducibility Audit

This note records a local reproducibility audit for Abrar Hoq Fahim's Aug. 9,
2026 fine-tuned BubbleID-Flow model package. It is intended to preserve the
provenance and parameter choices needed to reproduce the reported image-derived
vapor-fraction values from the GitHub repository plus external model/data
artifacts.

## Audited Artifacts

- Annotated dataset: 130 LabelMe JSON files and 130 BMP images.
- Fine-tuned weights: `model_final.pth`, SHA256
  `6F60969CE876F57A78B53FC61895C99B92CB2E1B6F0E0B30F01FA301236042CD`.
- Reported summary workbook: `values_vf_bc.xlsx`.
- Raw image cases: `5gs_22C`, `10gs_22C`, `15gs_20C`, and `25gs_20C`.
- Result/figure artifacts reviewed: `BubbleID-Flow.docx` and
  `BubbleID-Flow_Figures.pptx`.

The Aug. 9 weight hash differs from the earlier public-archive weight hash
listed in `docs/model_artifact_manifest.csv`, so the two artifacts should not be
treated as interchangeable.

## Checks Performed

- Verified that the LabelMe dataset contains 130 JSON files and 130 BMP images.
- Verified LabelMe labels are `bubble` and `bubble_cluster`; the repository
  conversion path merges both into one COCO category named `bubble`.
- Converted the LabelMe dataset to COCO with `--holdout-every 5` and
  `--roi 0,485,1024,70`; the split produced 104 training images and 26
  validation images, with 7273 and 1908 retained ROI annotations, respectively.
- Evaluated the checkpoint on the 26-image internal holdout using standard COCO
  instance metrics and task-aligned union-mask coverage metrics.
- Loaded the Aug. 9 `model_final.pth` with the repository Detectron2 inference
  configuration and generated ROI masks/overlays from raw CWRU BMP images.
- Regenerated a vapor-fraction profile CSV/PNG for a representative
  `15gs_20C/55 CHF` frame.
- Compared one raw frame per state against the `vf` section of
  `values_vf_bc.xlsx`.
- Reprocessed every available frame in all four 45 V state folders (391 frames
  total) and compared the complete-sequence means with the workbook values.

## Key Findings

The GitHub repository can substantially reproduce the Aug. 9 image-derived
vapor-fraction values when the Aug. 9 weights, raw images, ROI
`0,485,1024,70`, score threshold `0.30`, and an increased Detectron2 detection
cap are used.

The 26-image internal holdout produced bounding-box AP of `0.234`, mask AP of
`0.249`, and mask AP50 of `0.521`. For the manuscript endpoint, the union of all
predicted masks achieved mean IoU `0.652`, median IoU `0.707`, mean Dice `0.769`,
projected-area MAE `0.0051`, and maximum absolute projected-area error `0.0161`.
This supports combined projected coverage on this internal split, not individual
bubble statistics or experiment-held-out generalization.

The complete 45 V sequences contained 100, 108, 88, and 95 frames for the 5,
10, 15, and 25 g/s cases. Their recomputed means differed from the supplied
workbook by `-0.001891`, `-0.000836`, `+0.000204`, and `-0.000454`, respectively,
for a four-case MAE of `0.00085`.

Using Detectron2's default cap of 100 detections per image underpredicts dense
small-bubble states. With `TEST.DETECTIONS_PER_IMAGE = 300`, the one-frame
state comparison against Abrar's workbook gave the following mean absolute
differences in projected vapor area fraction:

| Case | States | Mean Absolute Difference | Maximum Absolute Difference |
|---|---:|---:|---:|
| `10gs_22C` | 8 | 0.003404 | 0.010905 |
| `15gs_20C` | 9 | 0.004316 | 0.009789 |
| `25gs_20C` | 8 | 0.002706 | 0.006977 |
| `5gs_22C` | 12 | 0.006699 | 0.025578 |

The existing checked-in `outputs/multimodal/*_image_state_summary.csv` files do
not match the Aug. 9 workbook. They are much higher at several onset/low-power
states and should be treated as stale or generated with a different model or
configuration.

The DOCX/PPTX artifacts document the workflow and include manual schematics and
embedded result images, but the repository does not yet contain a single
scripted target that regenerates the DOCX/PPTX figure package from raw images,
weights, and the reported workbook.

## Remaining Reproducibility Gaps

- The exact frame-selection or averaging rule used for the 33 non-45 V workbook
  states is not encoded in the source workbook; those states still require
  complete-sequence reruns.
- The workbook includes `bubble` and `bubble_cluster` counts, but repository
  inference currently uses a one-class model that merges both labels into
  `bubble`; this is appropriate for projected vapor-region masking but not for
  two-class count claims.
- The Aug. 9 OSF record was user provided; this audit verified the local Box
  hash but did not independently fetch and hash the OSF-hosted file.
- Full multimodal reproduction still requires thermal workbooks and EasyAE hit
  files, which are separate from the image-only Aug. 9 package.

## Reproduction Commands

```powershell
$env:PYTHONPATH='src'

python scripts/labelme_to_coco.py `
  --annotation-root "C:\path\to\Model_data_Aug9_2026\Annotation_Dataset\Annotation_Dataset" `
  --output-dir "tmp\repro_audit\coco_abrar_aug9_roi" `
  --holdout-every 5 `
  --roi 0,485,1024,70

python scripts/predict_detectron2.py `
  "C:\path\to\raw\Images\15gs_20C\55 CHF" `
  "tmp\repro_audit\predict_15gs_55_chf_smoke" `
  --weights "C:\path\to\Model_data_Aug9_2026\model_final.pth" `
  --roi 0,485,1024,70 `
  --score-threshold 0.30 `
  --detections-per-image 300 `
  --limit 1 `
  --device cpu

python scripts/plot_vapor_fraction_profile.py `
  "C:\path\to\raw\Images\15gs_20C\55 CHF\192.168.0.10_C001H001S0001000001.bmp" `
  "tmp\repro_audit\vf_profile_15gs_55_chf_frame1" `
  --weights "C:\path\to\Model_data_Aug9_2026\model_final.pth" `
  --roi 0,485,1024,70 `
  --bins 64 `
  --score-threshold 0.30 `
  --detections-per-image 300 `
  --device cpu
```
