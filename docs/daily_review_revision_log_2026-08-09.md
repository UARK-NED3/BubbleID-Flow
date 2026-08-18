# Daily Review, Revision, and Verification Log: 2026-08-09

## Manuscript Identity

- Journal target: *Applied Thermal Engineering*.
- Canonical source: `overleaf_applied_thermal_engineering/main.tex`.
- Title: *Multimodal Optical, Thermal, and Acoustic Diagnostics of Flow Boiling Using BubbleID-Flow*.
- Abrar Fahim's DOCX and PPTX were treated as source evidence, not as the
  canonical manuscript.

## Independent Reviewer Comments

1. The checked-in optical summaries and old manuscript figures were generated
   with a different checkpoint/configuration and could not support the Aug. 9
   claims.
2. Detectron2's default 100-detection cap truncated dense frames. The inference
   cap, ROI, threshold, frame rate, and checkpoint hash needed to be explicit.
3. The one-class checkpoint supports combined projected coverage more strongly
   than instance identity. Bubble counts, class-specific counts, sizes, and
   coalescence statistics were not scientifically supported.
4. The 130-image every-fifth-frame holdout is internal to one annotation
   package. It does not establish experiment-held-out or cross-facility
   generalization.
5. The supplied 37-state workbook did not encode the averaging/frame-selection
   rule. A raw-image sequence-level reproduction check was needed.
6. The updated 10 and 25 g/s endpoints decrease after their coverage maxima.
   The earlier monotonic CHF-adjacent narrative was not valid for this model.
7. Abrar's dataset and fine-tuning schematics were useful, but his OriginLab
   plots did not match the manuscript figure style and did not carry the full
   evidence/limitation context.
8. AE synchronization, overlapping state windows, and sensor coupling remain
   unresolved. Acoustic quantities cannot support classification or lead/lag
   claims.
9. Camera calibration, local optical-thermal registration, thermal-reduction
   uncertainty, and complete state-sequence uncertainty remain open.
10. Citation compilation passed, but metadata verification found an incomplete
    2015 author list and an incorrect 2024 journal volume.

## Repeated Issues and Deeper Response

- **Segmentation validation:** Previous logs repeatedly called for held-out
  manual-mask evidence. This revision evaluates all 26 internal-holdout images
  using both COCO instance metrics and task-aligned union-mask metrics. The
  manuscript still labels experiment-held-out validation as open.
- **Sparse frame sampling:** Previous revisions used 6--8 frames per state.
  This revision processes every available 45 V frame (391 frames total) and
  reports Student-t confidence intervals. The other 33 states remain open rather
  than being described as fully reproduced.
- **Active-vapor length:** Earlier logs repeatedly flagged dependence on the
  `0.05` column threshold. The updated manuscript removes active-length claims
  because the new evidence package is stronger and more direct for projected
  area coverage.
- **AE readiness:** The synchronization/coupling critique recurs. It is not
  resolved by wording; the audit continues to block quantitative AE use and the
  manuscript retains only quality-tagged screening comparisons.
- **Model provenance:** The active checkpoint, OSF record, SHA256, score
  threshold, ROI, detection cap, and generated evidence paths are now recorded
  together in the manuscript and artifact manifest.

## Revisions Made

- Added `scripts/evaluate_detectron2.py` for standard COCO and union-mask
  coverage evaluation.
- Added `scripts/prepare_aug9_optical_results.py` for workbook ingestion,
  complete 45 V inference, state/temporal summaries, manuscript plots, and the
  graphical abstract.
- Evaluated the 26-image internal holdout: mask AP `0.249`, AP50 `0.521`, mean
  union-mask IoU `0.652`, mean Dice `0.769`, and projected-area MAE `0.0051`.
- Reprocessed 100, 108, 88, and 95 frames at 45 V for the 5, 10, 15, and 25 g/s
  cases. The four-case mean absolute difference from the workbook state means is
  `0.00085`.
- Replaced the old optical results in the canonical LaTeX manuscript. Updated
  the abstract, methods, results, discussion, limitations, conclusions,
  highlights, cover letter, data availability, and acknowledgments.
- Directly used Abrar Fahim's dataset-preparation and fine-tuning schematics as
  Figs. 2 and 3. Excluded the supplied inference schematic because it named a
  script not present in the repository and implied unsupported count outputs.
- Remade Figs. 4--6 and the graphical abstract in the manuscript's Matplotlib
  style. Superseded OriginLab plots were not used.
- Removed stale figure copies from the flat Overleaf folder and converted the
  PowerPoint-derived PDFs to PDF 1.5 for clean pdfLaTeX inclusion.
- Updated `docs/model_artifact_manifest.csv` to make the Aug. 9 checkpoint the
  active artifact and record the new evaluation files/checksums.
- Corrected the 2015 flow-boiling paper's author list, the Shingote et al. paper
  volume (`152`), and the NASA acoustic poster metadata.
- Marked the older Markdown manuscript as a superseded historical snapshot.

## Verification

- `python -m pytest -q`: `35 passed`.
- `python -m py_compile` on the new/updated analysis and audit scripts: passed.
- `scripts/audit_ate_submission_package.py`: `0 errors`, `6 submission
  blockers`, `20 warnings`, `68 passes`; abstract `250` words; all five
  highlights under 85 characters; Aug. 9 result synchronization passed.
- `scripts/audit_manuscript_validation.py`: `0 errors`, `3 blockers`, `18
  warnings`, `14 passes`; internal manual-mask evaluation documented.
- `latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex`: passed with
  no overfull boxes, undefined citations/references, or figure PDF-version
  warnings. MiKTeX separately reports that its installation update check is due.
- `pdflatex cover_letter.tex`: passed.
- Poppler rendering: all 19 manuscript pages rendered and inspected; no blank,
  clipped, or overlapping figures/text were observed.
- `pdftotext` plus stale-value/prompt scan: no old optical values, old figure
  names, TODO/FIXME text, hidden prompts, or ChatGPT wording found.
- `git diff --check`: passed.
- Final 19-page PDF SHA256:
  `C3621F4CE90F3FAFFDDD657B708B3116461C082C04BC9A4D8D69A39D1FEAE65E`.
- Flat Overleaf ZIP SHA256:
  `6BDA8753032E22D30E30CC13F85F142617FC89C27B8EF3FA5C075192C898E09F`.

## Remaining Risks

- Reprocess all 33 non-45 V states from complete raw sequences and quantify
  threshold/detection-cap sensitivity before interpreting endpoint changes as
  flow physics.
- Add experiment-held-out manual masks from a separate video/operating path and
  preserve the modest instance AP claim ceiling.
- Archive the exact training configuration and loss/evaluation trace used to
  select `model_final.pth`.
- Audit thermal equations, properties, heat losses, calibration, spatial
  registration, and propagated uncertainty.
- Resolve AE trigger synchronization, overlapping windows, contiguous-window
  provenance, and sensor coupling before quantitative acoustic use.
- Independently download/hash the OSF-hosted checkpoint; only the local Box hash
  and user-provided OSF view-only record were verified in this run.
- Confirm raw-data sharing rights, figure permissions, final authorship/CRediT
  treatment for Abrar Fahim, funding numbers, competing interests, and all
  author approvals.

## Post-Revision Reviewer Verdict

The revised package is materially stronger and internally reproducible for the
documented projected-coverage endpoint. It is not submission-ready because the
open AE, thermal-uncertainty, complete-state-sequence, independent-validation,
and author/funding gates remain consequential.
