# Daily Review-Revision-Verification Log: 2026-07-06

Run time: 2026-07-06 04:21:41 -05:00

## Reviewer Comments

1. The manuscript still fits Applied Thermal Engineering as an applied
   thermal-systems diagnostic workflow because it connects visible vapor
   morphology, reduced heat-transfer response, and nonintrusive acoustic
   screening for flow boiling. The current ScienceDirect ATE guide emphasizes
   engineering application, thermal processes, systems, components, and energy
   utilization, so the paper should keep foregrounding the heat-transfer
   diagnostic value rather than presenting BubbleID-Flow as a generic computer
   vision method.
2. The scientific scope remains appropriately conservative. Optical heat-flux
   and active-vapor-length trends are supported with sampling and projection
   limits; AE remains screening-only; individual bubble statistics, acoustic
   timing/classification, and local optical-thermal registration remain outside
   the supported evidence.
3. The repeated AE synchronization critique is still unresolved in substance:
   the regenerated audits still report 4 overlap-blocked AE states, 32
   caution-level AE states, zero quantitative-ready AE cases, zero
   trigger-verified cases, and zero sensor-coupling-verified cases. This is not
   a wording problem and still requires raw acquisition metadata, contiguous
   window reruns, and coupling evidence.
4. Manual segmentation validation also remains unresolved in substance. The
   generated plan is useful, but all 16 selected states remain
   `planned_not_complete`; instance-level bubble count, size, coalescence, and
   separation claims must stay blocked.
5. A reproducibility gap from the 2026-07-05 log was confirmed today: the
   segmentation-validation worklist and companion evidence CSVs existed locally
   but were hidden by the broad `outputs/` ignore rule. Because the manuscript,
   validation audit, and ATE package audit cite those generated tables, keeping
   them invisible to Git would make the claim-evidence trail fragile.
6. Figure quality and package synchronization remain mostly sound. Summary
   figures and flat Overleaf PDFs were refreshed; Figure 5 retains 95%
   confidence-interval bars, Figure 6 retains AE quality masking, and Figure 7
   still could not be regenerated because the Box AE hit file is
   permission-denied.

## Repeated Issues

- AE synchronization and quantitative acoustic interpretation recurred again
  after 2026-07-03, 2026-07-04, and 2026-07-05. Today's work does not claim to
  solve that experimental gap; it keeps the AE gates active and makes the
  generated evidence artifacts easier to preserve.
- Manual segmentation validation recurred again. The worklist is now visible to
  Git, but the masks, validation metrics, and representative validation overlays
  still need to be produced.
- Human submission placeholders remain unchanged in `main.tex`: author
  confirmation, competing-interest confirmation, funding grant/sponsor wording,
  public repository URL, and acknowledgments still require final human review.
- The priority-1 AE rerun set remains `5gs_22C`, `10gs_22C`, and `15gs_20C`.
  `25gs_20C` remains priority-2 for contiguous-window provenance.

## Revisions Made

- Changed `.gitignore` so raw and bulky generated outputs remain ignored, while
  the small manuscript evidence artifacts under
  `outputs/multimodal/cross_case_synthesis` are versionable.
- Added an ATE package-audit check for evidence-artifact versioning. The audit
  now warns on missing cross-case evidence artifacts and reports a blocker if
  those artifacts are present but hidden by git ignore rules.
- Added focused direct tests for the new evidence-versioning guard, covering
  both visible and ignored artifact states.
- Updated `README.md`, `docs/manuscript_reproducibility.md`,
  `docs/applied_thermal_engineering_submission_notes.md`, and
  `overleaf_applied_thermal_engineering/README_Overleaf.txt` to document that
  cross-case synthesis evidence artifacts are intentionally versionable, while
  raw data, model weights, generated masks, and bulky intermediates remain
  outside git.
- Regenerated cross-case synthesis artifacts, summary-driven ATE figure files,
  validation/package audit reports, and `overleaf_applied_thermal_engineering.zip`.

## Remaining Risks

- `docs/manuscript_validation_audit.md` still reports 3 blockers: overlapping
  thermal/AE windows, 4 AE interpretation-blocked states, and zero cases
  satisfying quantitative AE readiness criteria.
- `docs/ate_submission_package_audit.md` still reports 7 submission blockers:
  five human submission placeholders, overlapping voltage-matched windows, and
  blocked AE confidence states.
- The 13 cross-case synthesis evidence artifacts are now visible to Git, but
  newly visible CSV artifacts remain untracked until deliberately added in a
  future commit.
- Full raw-data reruns, trigger synchronization, AE sensor coupling, HTC
  uncertainty propagation, camera registration, archived Detectron2 evaluation
  metrics, completed manual segmentation validation, and final author/sponsor
  confirmations remain unresolved.
- The active `python` command is Anaconda Python 3.9.12 while the project
  requires Python >=3.10. `pytest`, `ruff`, `pdflatex`, and `latexmk` are still
  not installed or not on `PATH`.

## Commands and Checks

- Consulted the current ScienceDirect ATE guide for authors and aims/scope.
- `python --version` reported Python 3.9.12.
- `git check-ignore -q
  outputs\multimodal\cross_case_synthesis\cross_case_segmentation_validation_plan.csv`
  now reports `NOT_IGNORED`.
- `python scripts\synthesize_multimodal_results.py --summary ... --output-dir
  outputs\multimodal\cross_case_synthesis` regenerated all cross-case
  synthesis CSV/TXT/PNG artifacts.
- `python scripts\prepare_ate_submission_figures.py --summary-only` succeeded
  and refreshed the flat Overleaf figure PDFs; Figure 7 regeneration was
  skipped because the Box AE hit file was permission-denied.
- `python scripts\audit_manuscript_validation.py` wrote
  `docs\manuscript_validation_audit.md` with 0 errors, 3 blockers, 17 warnings,
  and 12 passes.
- `python scripts\audit_ate_submission_package.py` wrote
  `docs\ate_submission_package_audit.md` with 0 errors, 7 blockers, 14
  warnings, and 76 passes, including 13 of 13 cross-case evidence artifacts
  visible to Git.
- Direct function-call harness passed 24 focused tests across
  `tests/test_synthesize_multimodal_results.py`,
  `tests/test_audit_ate_submission_package.py`, and
  `tests/test_audit_manuscript_validation.py`.
- `python -m compileall scripts tests src` passed.
- `Compress-Archive -Path overleaf_applied_thermal_engineering\*
  -DestinationPath overleaf_applied_thermal_engineering.zip -Force` refreshed
  the Overleaf package.
- `git diff --check` passed, with only Git LF-to-CRLF conversion warnings.
- `python -m pytest --version` failed because `pytest` is not installed.
- `python -m ruff check .` failed because `ruff` is not installed.
- `where.exe pdflatex` and `where.exe latexmk` found no local LaTeX toolchain.
