# Daily Review-Revision-Verification Log: 2026-07-20

Run time: 2026-07-20 09:52:09 -05:00

## Reviewer Comments

1. The manuscript remains a plausible Applied Thermal Engineering submission when the paper is framed as an applied thermal-systems diagnostic workflow. The current Elsevier ATE scope emphasizes engineering applications of thermal processes, components, technologies, and systems for energy production, utilization, management, and conservation; therefore, the manuscript should keep the optical/thermal/acoustic fusion tied to flow-boiling heat-transfer diagnostics rather than a generic computer-vision contribution.
2. The repeated AE critique still recurs in substance. The latest tracked audits still report 4 overlap-blocked AE states, 32 caution-level states, 0 quantitative-ready AE cases, 0 trigger-verified cases, and 0 sensor-coupling-verified cases. This is an experimental/provenance gap, not a prose gap.
3. Manual segmentation validation also remains unresolved. The 16-state validation worklist is useful, but all states remain `planned_not_complete`, so individual bubble count, size, coalescence, and instance-separation claims must remain blocked.
4. The optical trend evidence is stronger than the acoustic evidence, but active vapor length still depends on the fixed `phi_thr = 0.05` projected-vapor column threshold. Prior revisions made the threshold traceable; they did not test whether the active-length trend is robust to nearby thresholds.
5. Submission readiness remains blocked by human placeholders in `main.tex`: author contribution confirmation, competing-interest confirmation, funding grant/sponsor wording, repository URL confirmation, and final acknowledgments.
6. The local toolchain is currently worse than the 2026-07-06 state: `python` is not on `PATH`, and the `py` launcher points to a Python 3.13 WindowsApps executable that cannot start. This blocks Python tests, Python audit regeneration, and figure regeneration in this run.

## Repeated Issues

- AE synchronization and acoustic sensor-coupling evidence recurred from the 2026-07-06 log. No stronger AE claim was added today; AE remains screening-only.
- Manual segmentation validation recurred from the prior logs. Today's work does not complete masks or Detectron2 evaluation artifacts.
- Active-length threshold handling recurred in a more specific form. Earlier revisions made the 0.05 threshold auditable; today's review identified threshold robustness as the next real gap.
- Human submission placeholders remain unresolved and require author/sponsor confirmation.

## Revisions Made

- Added active-length threshold-sweep support to the image analysis path. Future per-case runs now record active length at nearby projected-vapor column thresholds, currently `0.025`, `0.05`, and `0.075`, in addition to the manuscript baseline threshold.
- Added cross-case synthesis support for `cross_case_active_threshold_sensitivity.csv`. The new artifact reports checked, partial, or missing threshold-sweep status by complete analysis state and feeds the claim-evidence matrix.
- Added validation-audit and ATE-package-audit checks for the active-threshold sensitivity artifact, including manuscript-citation checks and git-visibility coverage as a versioned evidence artifact.
- Added focused tests for the threshold-sensitivity synthesis and audit logic.
- Added the current `cross_case_active_threshold_sensitivity.csv` with 36 `missing_threshold_sweep` rows, matching the 36 complete multimodal analysis states. This is intentionally a gate, not a claim of completed robustness.
- Updated `overleaf_applied_thermal_engineering/main.tex`, `README.md`, `docs/manuscript_reproducibility.md`, `docs/applied_thermal_engineering_submission_notes.md`, `docs/key_figures_for_manuscript.md`, and `docs/manuscript_multimodal_flow_boiling.md` to describe the active-length threshold limitation and the new audit path.
- Refreshed `overleaf_applied_thermal_engineering.zip` after editing the Overleaf source.

## Remaining Risks

- The active-threshold sensitivity code could not be executed because no usable Python interpreter is available. The artifact is populated from the existing complete-state table as a missing-sweep gate; a full Detectron2-backed rerun is still required.
- AE quantitative interpretation remains blocked by overlap windows, missing contiguous-window provenance in tracked outputs, missing trigger synchronization, and missing sensor-coupling verification.
- Manual segmentation validation, archived Detectron2 evaluation metrics, HTC uncertainty propagation, heat-loss audit, camera-to-thermocouple registration, and full-image-sequence sampling remain open.
- Local `pytest`, `ruff`, `pdflatex`, and `latexmk` verification could not run because the required executables are not available on `PATH`.

## Commands and Checks

- Consulted the current Elsevier ATE journal/scope page for ATE fit.
- `python -m compileall scripts tests src` failed because `python` is not recognized.
- `where.exe python` found no executable.
- `py --version` failed because the launcher could not create a process for the registered Python 3.13 WindowsApps executable.
- `py -0p` showed only `-3.13-64 python3.13.exe`.
- `where.exe pdflatex`, `where.exe latexmk`, and `where.exe ruff` found no executables.
- `Import-Csv outputs\multimodal\cross_case_synthesis\cross_case_active_threshold_sensitivity.csv` confirmed `rows=36` and `missing_threshold_sweep=36`.
- `git check-ignore -q outputs\multimodal\cross_case_synthesis\cross_case_active_threshold_sensitivity.csv` reported `NOT_IGNORED`.
- `git diff --check` passed, with only Git LF-to-CRLF conversion warnings.
- `Select-String` checks confirmed the Overleaf source and repository notes cite the active-threshold sensitivity gate.
- `Compress-Archive -Path overleaf_applied_thermal_engineering\* -DestinationPath overleaf_applied_thermal_engineering.zip -Force` refreshed the Overleaf archive.
