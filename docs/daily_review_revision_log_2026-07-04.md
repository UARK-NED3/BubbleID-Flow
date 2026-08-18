# Daily Review-Revision-Verification Log: 2026-07-04

Run time: 2026-07-04 04:11:56 -05:00

## Reviewer Comments

1. The manuscript remains best suited to Applied Thermal Engineering as a
   reproducible multimodal diagnostic-workflow paper for flow boiling. The
   optical projected-vapor and state-level reduced-thermal claims are the
   strongest supported claims; quantitative AE timing, regime classification,
   and local optical-thermal coupling are still not submission-ready.
2. The main repeated scientific issue from 2026-07-03 persists. Current audits
   still report 4 overlap-blocked AE states, 32 caution-level AE states, zero
   quantitative-ready AE cases, zero trigger-verified cases, and zero
   sensor-coupling-verified cases.
3. The existing claim-evidence matrix was useful but too passive. A reviewer
   could still worry that future manuscript edits might accidentally reintroduce
   unsupported AE classifier/timing, individual bubble-statistic, or local
   optical-thermal registration language while leaving the matrix unchanged.
4. Figure and package consistency remain good for the current claim scope:
   Figure 5 cites sampled-frame 95% confidence intervals, Figure 6 masks
   overlap-blocked AE cells and shows AE quality weights, and headline result
   values still match generated CSV outputs.
5. Segmentation validation remains a real scientific gap, not a wording issue.
   The model-weight archive and checksum are documented, but archived
   Detectron2 evaluation metrics and a held-out manual-mask validation panel
   are still needed before instance-level bubble claims.
6. Submission readiness remains blocked by human placeholders, overlapping
   voltage-matched windows, blocked AE confidence states, unresolved AE
   readiness, missing trigger/coupling evidence, and final author/sponsor
   confirmations.

## Repeated Issues

- AE synchronization and quantitative acoustic interpretation recurred again
  after the 2026-07-03 run. Today did not solve the missing external trigger,
  contiguous-window, or coupling evidence, so the appropriate stronger revision
  was to enforce the restricted claim scope mechanically.
- The priority-1 AE rerun set remains unchanged: `5gs_22C`, `10gs_22C`, and
  `15gs_20C` contain overlap-blocked windows. `25gs_20C` remains priority-2
  for missing contiguous-window provenance.
- The `15gs_20C` final `55 CHF` point remains the influential AE sensitivity
  target; removing it changes nonblocked vapor/AE agreement from 0.12 to 0.68.
- Sampling uncertainty remains unchanged: 29 warning states and 4 projected
  vapor states above the 25% relative 95% confidence-interval threshold.

## Revisions Made

- Added claim-language gates to `scripts/audit_ate_submission_package.py`.
  When `cross_case_claim_evidence_matrix.csv` marks a claim family as
  `not_supported_current_snapshot`, the audit now flags assertive unsupported
  wording in `main.tex` as a submission blocker while allowing explicit
  limitation or screening-only wording.
- Added `tests/test_audit_ate_submission_package.py` covering allowed
  limitation wording and blocked assertive language for AE classifier/timing,
  bubble-instance statistics, and local optical-thermal registration.
- Updated the Overleaf manuscript to state that the claim-evidence matrix is
  enforced by the package audit, not only cited as a scope guard.
- Updated `README.md`, `docs/manuscript_reproducibility.md`,
  `docs/applied_thermal_engineering_submission_notes.md`, and
  `overleaf_applied_thermal_engineering/README_Overleaf.txt` so the submission
  package documentation now points authors to the enforced claim-language gate.
- Regenerated `docs/ate_submission_package_audit.md`,
  `docs/manuscript_validation_audit.md`, and
  `overleaf_applied_thermal_engineering.zip`.

## Remaining Risks

- `docs/manuscript_validation_audit.md` still reports 3 blockers: overlapping
  thermal/AE windows, 4 AE interpretation-blocked states, and zero cases
  satisfying quantitative AE readiness criteria.
- `docs/ate_submission_package_audit.md` still reports 7 submission blockers:
  five human submission placeholders, overlapping voltage-matched windows, and
  blocked AE confidence states.
- Full raw-data reruns, trigger synchronization, AE sensor coupling, HTC
  uncertainty propagation, camera registration, archived Detectron2 evaluation
  metrics, manual segmentation validation, and final author/sponsor
  confirmations remain unresolved.
- The active `python` command is Anaconda Python 3.9.12 while the project
  requires Python >=3.10. Some imports that evaluate PEP 604 type annotations
  fail under this interpreter; the Python 3.13 launcher is present but cannot
  start the WindowsApps executable.

## Commands and Checks

- `python --version` reported Python 3.9.12.
- Focused direct harness passed 4 new claim-language-gate tests.
- Broader direct harness passed 21 existing tests before stopping at
  `tests/test_vapor_fraction.py` because `pytest` is not installed.
- Direct vapor-fraction assertions passed for streamwise profile, projected
  mask metrics, and invalid-input errors.
- Direct path/preprocess assertions could not run under Python 3.9 because
  `src/bubbleid_flow/paths.py` evaluates `str | Path` at import time.
- `python -m compileall scripts tests src` passed.
- `python scripts\audit_ate_submission_package.py` wrote
  `docs\ate_submission_package_audit.md` with 0 errors, 7 blockers, 13
  warnings, and 73 passes; the new claim-language gate reports 3 active
  unsupported-claim gates and no assertive unsupported language in `main.tex`.
- `python scripts\audit_manuscript_validation.py` wrote
  `docs\manuscript_validation_audit.md` with 0 errors and 3 blockers.
- `Compress-Archive -Path overleaf_applied_thermal_engineering\*
  -DestinationPath overleaf_applied_thermal_engineering.zip -Force` refreshed
  the Overleaf package.
- `git diff --check` passed, with only Git LF-to-CRLF conversion warnings.
- `python -m pytest --version` failed because `pytest` is not installed.
- `python -m ruff check .` failed because `ruff` is not installed.
- `where.exe pdflatex` and `where.exe latexmk` found no local LaTeX toolchain.
