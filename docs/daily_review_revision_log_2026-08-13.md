# Daily Review, Revision, and Verification Log: 2026-08-13

## Manuscript identity

- Journal: *Applied Thermal Engineering*.
- Canonical source: `overleaf_applied_thermal_engineering/main.tex`.
- Revised title: *BubbleID-Flow: Reproducible Machine-Vision Quantification of
  Projected Vapor Coverage in Subcooled Flow Boiling*.
- Canonical PDF: `output/pdf/bubbleid_flow_ate_manuscript_2026-08-13.pdf`.

## Independent reviewer comments

1. Correct the working fluid and document geometry, heating, sensors, operating
   ranges, and state matching.
2. Audit the thermal source before using HTC, quality, friction, or energy balance.
3. Replace independent-frame uncertainty with a serial-dependence method.
4. Add simple and learned segmentation baselines without holdout tuning.
5. Treat the every-fifth-image split as same-sequence reconstruction.
6. Separate the archived 37-state table from complete raw-sequence reruns.
7. Test voltage/heat-flux confounding and incremental optical information.
8. Remove undefined CHF language and quantitatively unsupported acoustic results.
9. Broaden current machine-vision boiling literature and clarify ATE fit.
10. Synchronize manuscript, figures, graphical abstract, highlights, cover letter,
    repository evidence, and submission audit.

## Repeated issues and deeper response

- **Independent validation:** Repeated from Aug. 9. The split audit is now in the
  abstract and results, and experiment-level claims are blocked. New external
  annotations were not available, so this remains an experimental gate.
- **Non-45 V sequence completeness:** Repeated from Aug. 9. A checkpointed full-
  state inference path was added, but only three states completed during this run
  before the impractical CPU job was stopped. Their differences from archived
  summaries are now reported as provenance evidence but are not mixed into the
  cross-case figure; 30 states remain without complete reruns.
- **Thermal uncertainty:** Repeated from Aug. 9. The deeper response is a source-
  code and unit audit, reconstruction of defensible quantities, and removal of
  unsupported derived endpoints. Instrument uncertainty remains blocked by
  missing calibration and heat-loss records.
- **Acoustic readiness:** Repeated across prior reviews. Quantitative AE content
  is now removed rather than reframed as screening evidence.
- **Author/funding declarations:** Repeated and still require human confirmation.

## Substantive revisions

- Corrected the author affiliations from the author-provided mapping: Abrar
  Fahim, Daniel Curl, Mohammad Ishraq Hossain, Stephen Pierson, and Han Hu are
  affiliated with the University of Arkansas; Farshad Barghi Golezani and
  Chirag Kharangate are affiliated with CWRU. Han Hu remains corresponding
  author.
- Rewrote the manuscript around projected-coverage validation and traceable
  thermal context; corrected the fluid to FC-72.
- Added moving-block bootstrap uncertainty and effective sample size analysis.
- Added Otsu and training-only Gaussian pixel baselines.
- Added thermal reduction audit and excluded unsupported HTC/quality/friction/
  energy-balance endpoints.
- Added within-case confounding and cross-validated temperature-response tests.
- Expanded current primary literature and re-positioned novelty relative to the
  large 2026 ATE vision study.
- Regenerated manuscript figures, graphical abstract, highlights, cover letter,
  Overleaf inventory, and package audit.
- Added focused time-series tests and allowlisted eleven small evidence artifacts.

## Verification

- `latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex`: passed; 19 pages,
  no undefined citations/references and no overfull boxes.
- Poppler rendering at 110 dpi: all 19 pages inspected; no clipping, overlap,
  blank figures, or unreadable tables.
- `scripts/audit_ate_submission_package.py`: 0 errors; six human-confirmation
  blockers; 61 passes; all current scientific-evidence gates pass; abstract 250
  words; all 13 small evidence artifacts are visible to git.
- `scripts/audit_manuscript_validation.py`: 0 errors, three scientific blockers,
  two warnings, and five passes; the audit now follows the revised scope rather
  than the superseded acoustic analysis.
- `python -m pytest -q`: 40 passed.
- Segmentation baseline, optical--thermal association, thermal audit, and temporal
  summary values were regenerated and synchronized with the manuscript.
- `git diff --check`: passed.
- Final PDF text extraction contains the revised title, FC-72, moving-block,
  baseline, cross-validation, and 30-state limitation text; stale water,
  CHF-adjacent, old title, and legacy AE-figure text are absent.
- Final PDF: 19 letter-size pages, PDF 1.5, SHA256
  `AACC1AB6E4AA84B93C73DB2F788201C00A12DDC291EA0305B6F66874AC9DD584`.
- Flat Overleaf ZIP SHA256:
  `774861C34ACEBA26F31E702BDC09A36B3A85BBEE6004E6152429B67912B034E0`.

## Remaining risks

- New experiment-held-out annotated image sequences are required for generalization.
- Complete frame-level reruns and temporal intervals are missing for 30 states.
- Thermal calibration, heat loss, property sources, and propagated uncertainty are
  unavailable; HTC, quality, friction, and energy balance remain excluded.
- Camera-to-heater/sensor registration and an objective CHF criterion are absent.
- CRediT roles for Stephen Pierson and Chirag Kharangate, funding details,
  competing interests, contributor approvals, and photograph permissions require
  author confirmation.
