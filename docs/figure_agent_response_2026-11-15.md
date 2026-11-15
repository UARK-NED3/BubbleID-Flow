# Figure-Agent Handover Response

This response answers `questions_for_figure_agent.md` against the reconciled
repository state. It distinguishes measurements reproduced from the released
checkpoint from provenance inferred from the older June outputs.

## 1. Released checkpoint

The manuscript optical results use the checkpoint whose SHA-256 is:

```text
6f60969ce876f57a78b53fc61895c99b92cb2e1b6f0e0b30f01fa301236042cd
```

The file is `ModelWeights/model_final.pth` in the Zenodo dataset
([10.5281/zenodo.22235802](https://doi.org/10.5281/zenodo.22235802)). In the
local release copy used for a direct smoke run, its full path was:

```text
D:\ned3-018_BubbleID-Flow\ned3-018_BubbleID-Flow\ModelWeights\model_final.pth
```

It is 351,011,891 bytes and stores `iteration = 1999`. The original August
figure-generation manifest identifies a workstation copy with the same
SHA-256; the checksum, rather than its private path, establishes identity.

## 2. Table 3 sequence means

The complete-sequence values are in
`outputs/aug9_model_analysis/aug9_temporal_summary_45V.csv`. The corresponding
per-frame values are in
`outputs/aug9_model_analysis/aug9_temporal_vapor_fraction_45V.csv`. They are:

| Case | Frames | Mean vapor area fraction | Integral correlation time (frames) | Effective sample size |
| --- | ---: | ---: | ---: | ---: |
| 5 g/s, 22 °C | 100 | 0.12897 | 10.19 | 9.82 |
| 10 g/s, 22 °C | 108 | 0.10882 | 9.64 | 11.20 |
| 15 g/s, 20 °C | 88 | 0.06556 | 25.00 | 3.52 |
| 25 g/s, 20 °C | 95 | 0.01378 | 9.84 | 9.66 |

Thus the regenerated 25 g/s, 45 V sequence mean is **0.01378**. The canonical
37-state table records the archived August state-summary value as 0.014231 for
the same case and voltage. The small difference is expected because the first
is the mean of the current checkpoint's 95-frame sequence and the latter is an
archived state summary, not the June `outputs/multimodal/` value of 0.0778.

## 3. Data files and their scope

| File | Rows | Scope | Check-in filesystem time |
| --- | ---: | --- | --- |
| `outputs/aug9_model_analysis/canonical/aug9_state_vapor_area_fraction.csv` | 37 | One August state summary per operating condition | 2026-11-15T04:52:35Z |
| `outputs/aug9_model_analysis/aug9_temporal_vapor_fraction_45V.csv` | 391 | Per-frame current-checkpoint measurements at 45 V: 100, 108, 88, and 95 frames | 2026-11-15T04:52:35Z |
| `outputs/aug9_model_analysis/aug9_temporal_summary_45V.csv` | 4 | Complete-sequence means, autocorrelation correction, and confidence intervals | 2026-11-15T04:52:35Z |
| `outputs/aug9_model_analysis/full_sequences/full_sequence_frame_metrics.csv` | 290 | Partial archival material: only the 5 g/s case, 25/27.5/30 V | 2026-11-15T04:52:35Z |
| `outputs/aug9_model_analysis/full_sequences/full_sequence_state_summary.csv` | 3 | Summaries for the same partial 5 g/s material | 2026-11-15T04:52:35Z |

The dates above are Git-checkout modification times, not evidence of the
original August generation time. The relevant provenance commit is
`19c0e5aa46a15fe71a778af227012039791dee9a` (2026-11-14T22:49:14-06:00).
Only the 45 V table is a complete current-checkpoint per-frame record for all
four cases. Do not represent the three-state `full_sequences` folder as a
complete 37-state rerun.

## 4. Current source for manuscript figures

All source scripts below are now in `origin/main`. They accept
`--figure-width-in`; use `7.0` for the supplied ASME two-column `figure*`
layout or `5.40` only when the final LaTeX float is one-column wide. Source and
LaTeX widths must match, so that font sizes are not silently scaled.

| ASME figure | Script | Output stem to use |
| --- | --- | --- |
| 4: model outputs | `scripts/prepare_aug9_optical_results.py` | `--model-figure-stem Figure_4_model_outputs` |
| 5: robustness | `scripts/analyze_segmentation_robustness.py` | `--figure-stem Figure_5_segmentation_robustness` |
| 6: baseline comparison | `scripts/evaluate_segmentation_baselines.py` | `--figure-stem Figure_6_segmentation_baselines` |
| 7: optical results | `scripts/prepare_aug9_optical_results.py` | `--optical-figure-stem Figure_7_optical_results` |
| 8: thermal association | `scripts/analyze_optical_thermal_association.py` | `--figure-stem Figure_8_thermal_association` |

The former `Figure_5_aug9_optical_results` and
`Figure_6_optical_thermal_association` names belong to the earlier manuscript
numbering. Output-stem options now avoid copy-and-rename steps.

## 5. Figure 7 label and physical figure width

The Figure 7(d) label is now `State-summary vapor area fraction`; it no longer
uses “Archived”. The plotting scripts do not use `bbox_inches="tight"` for the
data figures, because tight cropping alters the PDF media box and rescales
type after `\includegraphics`. Shared legends are reserved inside the figure
canvas.

A current-checkpoint smoke run at `--figure-width-in 7.0` produced 504-point
(7.0-inch) PDF media boxes for the model-output, optical-results, and thermal
association figures. This was visually checked after export. The output
figures must be included at their native width, for example:

```latex
\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth]{figures/Figure_7_optical_results.pdf}
\end{figure*}
```

## 6. Separation from the June multimodal outputs

Active manuscript optical quantities must come from the canonical August table
and the current-checkpoint 45 V sequence table above, not from
`outputs/multimodal/`. The current optical script accepts
`--combined-summary` only to provide thermal/acoustic context for its
non-manuscript multimodal-context figure. It drops the legacy
`vapor_area_fraction_mean` field before that context is assembled.

The June CSVs lack a recorded weights hash, so the assertion that they used an
earlier checkpoint is an inference from their June date, their differing
values, and the overlay artifact. It is a strong working explanation, not a
directly recorded provenance fact. The manuscript and reproduction guide must
therefore label those files as superseded and not use them as a numerical
source.

## 7. Left-edge detection check

A direct run of the released checkpoint on one representative 45 V frame per
case produced zero mask coverage in the leftmost 10% of the ROI for the four
checked images. This supports the conclusion that the prominent June edge
artifact is absent in those current-checkpoint examples. It is not a
full 37-state, every-frame artifact audit and must not be described as one.

## Regeneration commands

Set the repository root as the working directory. The release data paths below
are local examples; replace them with the corresponding Zenodo extraction on
another machine.

```powershell
$env:PYTHONPATH = "$PWD;$PWD\src"
$data = 'D:\ned3-018_BubbleID-Flow\ned3-018_BubbleID-Flow'
$out = 'outputs\aug9_model_analysis'

python scripts\prepare_aug9_optical_results.py `
  --state-vapor-table "$out\canonical\aug9_state_vapor_area_fraction.csv" `
  --combined-summary "outputs\multimodal\cross_case_synthesis\combined_multimodal_state_summary.csv" `
  --image-root "$data\MultimodalData\Images" `
  --weights "$data\ModelWeights\model_final.pth" `
  --output-dir "$out" `
  --figure-width-in 7.0 `
  --model-figure-stem Figure_4_model_outputs `
  --optical-figure-stem Figure_7_optical_results

python scripts\analyze_optical_thermal_association.py `
  --optical-summary "$out\canonical\aug9_state_vapor_area_fraction.csv" `
  --thermal-summary "$out\thermal_audit\thermal_state_audit.csv" `
  --temporal-summary "$out\aug9_temporal_summary_45V.csv" `
  --output-dir "$out\optical_thermal_association" `
  --figure-width-in 7.0 `
  --figure-stem Figure_8_thermal_association
```

The robustness and baseline scripts require the corresponding COCO annotations
and archived predictions. Their input and output mapping is documented in
`docs/manuscript_reproducibility.md`.
