# Manuscript Reproducibility Notes

## Current Analysis Snapshot

The manuscript results currently tracked in `outputs/multimodal` use the
external Detectron2 Mask R-CNN model folder:

```text
C:\Users\hanhu\Box\NED3_Share\0_BubbleID\BubbleID-Flow\detectron2_flow_mrcnn_roi485_70
```

Key files in that folder:

- `model_final.pth`
- `config.yaml`
- `metrics.json`
- `eval\coco_instances_results.json`
- `eval\instances_predictions.pth`

The model folder is intentionally outside git because the weights are large. The
manuscript text cites this path as the local analysis source and the OSF archive
as the public model-weight source. The repo-tracked manifest
`docs/model_artifact_manifest.csv` records the current public weight URL and
checksum so the validation audit can distinguish model-weight availability from
still-pending evaluation and manual-validation artifacts.

Current public model-weight record:

- OSF project: `https://osf.io/p9nzt/`
- Direct weights download: `https://osf.io/download/6a2a2e8f09f1e3d2a3d14dae/`
- `model_final.pth` SHA256:
  `10613DE030B35637BECB4FDA524F8D829E9B77B25E90AB9A670992E8A9B4B166`
- Still pending for final segmentation validation: archived `metrics.json`,
  archived `eval\coco_instances_results.json`, and a held-out manual-mask
  validation panel across onset, developed, and CHF-adjacent states.

## Raw Data Sources

Raw October 17, 2025 CWRU Test 17 data are under:

```text
C:\Users\hanhu\Box\NED3_Share\Ishraq Hossain\CWRU\test17_17th Oct_Friday
```

The analysis uses these subfolders:

| Case | Image root | Thermal workbook | Thermal input workbook | AE HIT file |
| --- | --- | --- | --- | --- |
| `5gs_22C` | `Test17_Flow_Loop_and_Imaging\Images\5gs_22C` | `Flow Loop Dataset\5gs_22C\5gs_22C.xlsx` | `Flow Loop Dataset\5gs_22C\5gs_22C_IN_with_units.xlsx` | `2\HIT_5gs_22C.TXT` |
| `10gs_22C` | `Test17_Flow_Loop_and_Imaging\Images\10gs_22C` | `Flow Loop Dataset\10gs_22C\10gs_22C.xlsx` | `Flow Loop Dataset\10gs_22C\10gs_22C_IN_with_units.xlsx` | `1\HIT_10gs_22C.TXT` |
| `15gs_20C` | `Test17_Flow_Loop_and_Imaging\Images\15gs_20C` | `Flow Loop Dataset\15gs_20C\15gs_20C.xlsx` | `Flow Loop Dataset\15gs_20C\15gs_20C_IN_with_units.xlsx` | `3\HIT_15gs_20C.TXT` |
| `25gs_20C` | `Test17_Flow_Loop_and_Imaging\Images\25gs_20C` | `Flow Loop Dataset\25gs_20C\25gs_20C.xlsx` | `Flow Loop Dataset\25gs_20C\25gs_20C_IN_with_units.xlsx` | `4\HIT_25gs_20C.TXT` |

Preliminary acoustic/thermal analysis and setup photographs are under:

```text
C:\Users\hanhu\Box\NED3_Share\0_NSF_CASIS_FBCE_Project\CWRU_visit_Oct_13_17_2025
```

The visit summary deck is:

```text
C:\Users\hanhu\Box\NED3_Share\0_NSF_CASIS_FBCE_Project\CWRU_visit_Oct_13_17_2025\CWRU_Oct_2025_Visit_Summary.pptx
```

Use that deck as the first source for the experimental setup photograph or
schematic panels in Figure 1.

## Recreate The Tracked Multimodal Outputs

## Recreate The Segmentation Robustness Audit

The archived 26-image COCO prediction file supports deterministic analysis of
the manuscript operating point without rerunning model inference. From the
repository root, run:

```powershell
$env:PYTHONPATH='src;.'
C:\Users\hanhu\Anaconda3\envs\bubbleid\python.exe `
  scripts\analyze_segmentation_robustness.py `
  --train-json tmp\repro_audit\coco_abrar_aug9_roi\train_coco.json `
  --val-json tmp\repro_audit\coco_abrar_aug9_roi\val_coco.json `
  --predictions-json outputs\aug9_model_analysis\internal_holdout_evaluation\coco_instances_results.json `
  --output-dir outputs\aug9_model_analysis\segmentation_robustness
```

The script reproduces the 0.30-threshold, 300-detection-cap union-mask metrics,
computes deterministic image-level bootstrap intervals, stratifies error by
manual projected vapor coverage, sweeps score thresholds and detection caps,
and audits source-sequence proximity between training and holdout images. The
current split contains 10 holdout images with a training image having the same
nominal sequence index and 25 of 26 with a training image within one index.
These outputs support same-sequence reconstruction only, not experiment-level
generalization. The original training trace, random seed, augmentation record,
and checkpoint-selection history remain unavailable.

From the repository root, run:

```powershell
.\scripts\run_multimodal_manuscript_cases.ps1
```

The script runs the four case analyses with:

- ROI: `0,485,1024,70`
- Mask R-CNN score threshold: `0.30`
- Active vapor column threshold: `0.05` projected vapor occupancy
- Voltage matching tolerance: `+/-0.75 V`
- Requested sampled frames per operating state: `8`
- Actual tracked sampled frames per state: `6` to `8`, because some source
  state folders contain fewer than eight available frames

It writes per-case state summaries, frame metrics, integrated panels,
representative overlays, and the cross-case synthesis under:

```text
outputs\multimodal
```

The small evidence artifacts under
`outputs\multimodal\cross_case_synthesis` are intentionally versionable even
though most generated outputs remain ignored. These CSV/TXT/PNG files are the
claim-evidence trail for the manuscript and audits; raw data, model weights,
generated masks, and bulky intermediate products should remain outside git.

The cross-case synthesis table records `active_column_threshold` for every
state. If older per-case summaries lack that column, the synthesis step fills it
from the `--active-column-threshold` argument and marks
`active_column_threshold_source` as `synthesis_argument` so active-length
figures remain auditable.

The cross-case synthesis also records AE-window interpretation quality in
`ae_window_quality`, `ae_window_quality_reason`,
`ae_window_overlaps_previous_state`, and `ae_interpretation_weight`. Current
tracked summaries predate contiguous-window provenance, so non-overlapping AE
states are caution-level and repeated-voltage overlap states are blocked for AE
interpretation until the per-case summaries are regenerated.

The synthesis step also writes
`outputs\multimodal\cross_case_synthesis\cross_case_trend_summary.csv`. This
table records case-level Spearman rank agreement for heat flux versus projected
vapor area, heat flux versus active vapor length, and projected vapor area
versus AE absolute-energy rate after removing overlap-blocked AE windows. Use
this table as the source of manuscript statements about monotonic optical trends
and quality-gated AE agreement.

The synthesis step also writes
`outputs\multimodal\cross_case_synthesis\cross_case_trend_sensitivity.csv`.
This leave-one-state-out table records how much each rank-agreement statement
changes when each operating state is removed. Use it to identify state-sensitive
claims. In the current tracked snapshot, the optical heat-flux correlations
remain positive after removing any one state, while the `15gs_20C` vapor/AE
agreement changes from `rho_s = 0.12` to `0.68` when the final `55 CHF` state is
removed.

The synthesis step also writes
`outputs\multimodal\cross_case_synthesis\cross_case_sampling_uncertainty.csv`.
This table recomputes sampled-frame means, standard deviations, standard errors,
and Student-t 95% confidence-interval half-widths from the per-frame image
metrics. It flags states with fewer than eight sampled frames and states whose
relative interval half-width exceeds 25%. In the current tracked snapshot, 29
image states carry a sampling warning, mostly because fewer than eight frames
were available, while four states exceed the 25% relative vapor-area interval
threshold. The largest relative vapor-area interval is `25gs_20C/35`, with a
half-width of `0.043`, or `38%` of the sampled mean.

The synthesis step also writes
`outputs\multimodal\cross_case_synthesis\cross_case_active_threshold_sensitivity.csv`.
Future per-case image analysis runs store active-length values at nearby
projected-vapor column thresholds, currently `0.025`, `0.05`, and `0.075`, so
the cross-case synthesis can report whether \(L_A\) is robust to the cutoff
rather than only traceable to it. The tracked frame metrics used in the current
snapshot predate this sweep, so the artifact currently records
`missing_threshold_sweep` for the complete states and keeps the active-length
claim conditional on `phi_thr = 0.05` until the Detectron2-backed case analyses
are rerun.

The synthesis step also writes
`outputs\multimodal\cross_case_synthesis\cross_case_segmentation_validation_plan.csv`.
This table turns the repeated manual-segmentation critique into a concrete
held-out mask worklist. For each case, it selects onset or low-vapor,
developed, high-vapor or CHF-adjacent, and high-uncertainty states when
available, merges duplicate selections, and records the minimum manual ROI
masks needed before individual bubble-count, bubble-size, coalescence, or
instance-separation claims can be supported. The current status is
`planned_not_complete`, so the artifact is a validation plan rather than
completed validation evidence.

The generated cross-case analysis table now carries the sampled-frame 95%
confidence-interval columns forward into
`combined_multimodal_analysis_states.csv`, and Figure 5 uses those interval
half-widths for panel (a). Figure 6 also applies acoustic evidence gating during
rendering: overlap-blocked AE states are masked in the AE-energy screening
column, and the separate AE quality-weight column remains on an absolute 0,
0.5, or 1 scale instead of being column-normalized.

The synthesis step also writes
`outputs\multimodal\cross_case_synthesis\cross_case_thermal_response_checks.csv`.
This table checks the reduced thermal context used in the manuscript figures.
In the current tracked snapshot, heat flux is monotonic with voltage in all
four cases and mean HTC has positive rank agreement with heat flux, so heat
flux and mean HTC can be used as state-level thermal context. The same artifact
keeps the interpretation bounded: it does not audit heat-loss correction,
thermocouple uncertainty, HTC equations, or camera-to-thermocouple
registration.

The synthesis step also writes
`outputs\multimodal\cross_case_synthesis\cross_case_ae_evidence_tiers.csv`.
This table combines AE-window quality, pass-level window counts, overlap
blockers, and leave-one-state-out sensitivity into a case-level claim scope.
Use it as the gate for acoustic manuscript language. In the current tracked
snapshot, `5gs_22C`, `10gs_22C`, and `15gs_20C` are mixed-window snapshots due
to overlap-blocked states, while `25gs_20C` is an exploratory legacy-window
snapshot because no pass-quality AE windows are available. Until the trigger
and sensor-coupling audits are completed, AE correlations should be treated as
screening diagnostics rather than quantitative regime-classifier evidence.

The synthesis step also writes
`outputs\multimodal\cross_case_synthesis\cross_case_ae_readiness_matrix.csv`.
This matrix is the stricter acoustic-readiness gate. It requires enough
pass-quality AE windows, enough nonblocked states, complete contiguous-window
provenance, trigger-timing verification, and sensor-coupling verification
before a case can support quantitative AE interpretation. In the current
tracked snapshot, no case is quantitative-ready: all cases have zero
pass-quality AE windows, the tracked summaries lack contiguous-window
provenance, three cases include overlap-blocked states, and trigger/coupling
verification remains open.

The synthesis step also writes
`outputs\multimodal\cross_case_synthesis\cross_case_ae_verification_status.csv`
and
`outputs\multimodal\cross_case_synthesis\cross_case_ae_remediation_plan.csv`.
The verification-status table records case-level trigger synchronization and AE
sensor-coupling evidence when such a CSV is supplied to
`scripts\synthesize_multimodal_results.py --ae-verification-status`. Without
that supplied evidence, all four tracked cases remain unverified. The
remediation plan ranks cases by what blocks quantitative AE use. In the current
tracked snapshot, `5gs_22C`, `10gs_22C`, and `15gs_20C` are priority-1 because
they include overlap-blocked AE windows, while `25gs_20C` is priority-2 because
it lacks contiguous-window provenance. The `15gs_20C`/`55 CHF` state remains the
specific waveform window to inspect after rerunning contiguous windows.

The synthesis step also writes
`outputs\multimodal\cross_case_synthesis\cross_case_claim_evidence_matrix.csv`.
This matrix is the manuscript claim-scope gate. It joins the trend, sensitivity,
sampling-uncertainty, thermal-response, AE verification-status, AE
evidence-tier, AE-readiness, and AE remediation artifacts into rows for
supported, screening-only, and unsupported claims. In the current tracked
snapshot, the matrix supports optical heat-flux trend and state-level
thermal-context language with limits, restricts AE to quality-tagged screening
comparisons, and blocks AE regime-classifier, acoustic lead-lag, individual
bubble-statistic, and local optical-thermal registration claims until new
validation artifacts are added.
The ATE package audit now reads the same matrix and checks `main.tex` for
assertive unsupported claim language, allowing explicit limitation or
screening-only wording but reporting stronger unsupported wording as a
submission blocker.

Thermal voltage matching now selects a contiguous, non-overlapping operating
block when repeated voltage levels create multiple candidate windows. New
per-case summaries record `thermal_candidate_rows`, `thermal_window_blocks`,
`thermal_window_selection`, and related timing metadata. The tracked June 2026
output snapshot predates these selector metadata and should be regenerated
before making quantitative AE timing or lead-lag claims.

If the Detectron2 environment is not the default `python`, pass the environment
explicitly:

```powershell
.\scripts\run_multimodal_manuscript_cases.ps1 -PythonExe ".\.venv\Scripts\python.exe"
```

## Validation and Submission Audits

Run the validation-readiness audit after regenerating summaries:

```powershell
$env:PYTHONPATH="src"
python scripts\audit_manuscript_validation.py
```

Run the ATE package audit after regenerating figures or editing Overleaf files:

```powershell
$env:PYTHONPATH="src"
python scripts\audit_ate_submission_package.py
```

The validation audit checks complete-state filtering, active-length threshold
traceability, sampled-frame counts, thermal-window overlap, AE-vapor rank
agreement, heat-flux/visual rank agreement, leave-one-state-out trend
sensitivity, segmentation-validation targets, AE evidence-tier limits, AE
verification status, AE readiness, AE remediation actions, model/evaluation
artifact availability, and the repo-tracked model artifact manifest. The package
audit checks submission-file consistency and now also flags frame-sampling,
thermal-window alignment, trend-summary sync risks, segmentation-validation
plan citation, state-sensitive AE agreement, AE verification status, AE
remediation actions, AE readiness, and acoustic claim-scope limits. It also
enforces claim-language gates derived from
`cross_case_claim_evidence_matrix.csv` so unsupported claim families cannot
quietly re-enter the Overleaf source.

## Current Manuscript Caveats

- The AE state matching is operating-state/provisional, not yet a verified
  trigger-synchronized time alignment.
- Test notes state that AE sensor mounting may have been inadequate for these
  tests; acoustic conclusions should therefore emphasize trends and workflow
  feasibility until coupling and channel response are audited.
- The current AE evidence-tier artifact restricts acoustic statements to
  screening diagnostics because no current case has pass-quality AE windows.
- The current AE-readiness matrix reports zero quantitative-ready cases; trigger
  synchronization, contiguous-window provenance, and AE sensor coupling must be
  verified before quantitative acoustic interpretation.
- The current AE verification-status artifact records zero trigger-verified and
  zero sensor-coupling-verified cases, and the AE remediation plan keeps three
  cases at priority 1 because of overlap-blocked windows.
- The current claim-evidence matrix explicitly blocks AE classifier/timing,
  individual bubble-statistic, and local optical-thermal registration claims.
- The model weight archive and SHA256 checksum are now documented in
  `docs/model_artifact_manifest.csv` and in the manuscript data-availability
  section, but Detectron2 evaluation metrics and manual segmentation validation
  remain pending.
- The segmentation-validation plan now identifies the specific manual-mask
  target states, but those masks and validation metrics are still not complete.
- The current thermal-response check supports state-level heat-flux and mean-HTC
  context, but it does not replace a heat-loss, thermocouple uncertainty,
  pressure-drop, HTC-equation, or camera-registration audit.
- Image-derived vapor fraction is a 2D projected area metric in the camera ROI,
  not calibrated volumetric void fraction.
- Current figures use six to eight sampled frames per state. A final submission should either
  process full image sequences or justify the sampling strategy statistically.
  The current sampling-uncertainty artifact provides a first quantitative audit
  of this limitation but does not replace denser temporal sampling.
- Manual segmentation validation is still needed before making claims about
  individual bubble counts, sizes, or merged-bubble statistics.
