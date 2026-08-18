# Mechanical Engineering Skill Review and Manuscript Revision - 2026-08-12

## Skill provenance

- Online source: `hanhuark/mechanical-engineering-research-skill`.
- Verified upstream commit: `7ab424c7374a429b17831736361d766bc25edc7b` dated 2026-08-12.
- The installed skill was one revision behind and was synchronized before this
  review. The ML credibility guidance itself was unchanged; the upstream update
  added Han Hu manuscript-style and scientific-figure safeguards.

## Reviewer findings

1. The 26-image every-fifth-frame split was described cautiously, but its
   leakage risk had not been measured. This is a repeated scientific issue from
   the earlier package audit and required analysis rather than another caveat.
2. Aggregate IoU, Dice, and area error lacked uncertainty intervals and hid
   performance differences between sparse- and dense-vapor images.
3. The score threshold and 300-detection cap were documented without a direct
   operating-point sensitivity analysis tied to the projected-area endpoint.
4. The archived checkpoint can be evaluated reproducibly, but the original
   training process cannot be reproduced without its log, seed, augmentation
   record, and checkpoint-selection trace.
5. Cross-experiment segmentation validation, thermal uncertainty propagation,
   camera-to-thermocouple registration, and AE synchronization/coupling remain
   unresolved submission risks.

## Revisions and new evidence

- Added `scripts/analyze_segmentation_robustness.py` and focused tests.
- Audited all train/holdout filenames and image similarity. Ten of 26 holdout
  images share a nominal source index with training data, and 25 of 26 have a
  training image within one sequence index. The evidence is now explicitly
  classified as same-sequence reconstruction.
- Added 10,000-resample image-level percentile bootstrap intervals. Mean IoU is
  0.652 with 95% interval 0.573-0.721; mean Dice is 0.769 with interval
  0.690-0.830; area-fraction MAE is 0.0051 with interval 0.0037-0.0066.
- Added score-threshold and detection-cap sweeps. The 0.30 threshold minimizes
  area-fraction MAE among tested thresholds. Caps of 200 and 300 are effectively
  equivalent, whereas cap 100 increases MAE to 0.0079 and introduces negative
  bias.
- Added coverage-regime evaluation. Mean IoU is 0.444 at manual coverage no
  greater than 0.05, compared with 0.758 and 0.775 in intermediate and high
  coverage groups. The manuscript now identifies sparse-vapor onset states as
  the weakest regime.
- Added and integrated `Figure_5_segmentation_robustness.pdf`, updated methods,
  results, abstract, limitations, conclusions, highlights, reproducibility
  notes, Overleaf README, and package audit.

## Remaining risks

- No independent experiment/video/operating-path manual-mask test exists.
- The 130-image annotation package comes from one camera sequence and is not a
  basis for domain-generalization claims.
- Annotation uncertainty and inter-annotator variability are not quantified.
- The model-training trace is incomplete.
- AE timing/coupling and thermal uncertainty/registration gates remain open.

## Verification

- `python scripts/analyze_segmentation_robustness.py ...`: passed and reproduced
  the archived 0.30/300 metrics exactly.
- `python -m pytest -q`: 37 passed.
- `python scripts/audit_ate_submission_package.py`: 0 errors, 6 declared
  submission blockers, 20 warnings, and 72 passes.
- `python scripts/audit_manuscript_validation.py`: 0 errors, 3 scientific
  blockers, 15 warnings, and 13 passes.
- `latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex`: passed with
  21 pages, no unresolved references, and no overfull boxes. MiKTeX reported
  that its package-update check has not been run; this did not prevent compile.
- Poppler rasterization and contact-sheet inspection covered all 21 pages. The
  new robustness figure was also inspected at full resolution and on manuscript
  page 12; no blank pages, clipping, or figure/text overlap were found.
- `git diff --check`: passed; line-ending conversion warnings remain for
  pre-existing working-tree files.
- Final PDF: `output/pdf/bubbleid_flow_ate_manuscript_2026-08-12.pdf`, SHA256
  `16DC562C2F5964BD674EC8050A79D8C275ED57E2C8368865F03C11F5F8FF122F`.
- Clean Overleaf archive: `overleaf_applied_thermal_engineering.zip`, SHA256
  `E0262A4C7C209E6B434F15DE7C61BA682A96CFDD730E5DF0BDAF4FED441E3052`.
