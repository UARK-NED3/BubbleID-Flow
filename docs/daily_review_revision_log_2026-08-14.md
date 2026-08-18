# Daily Review, Revision, and Verification Log -- 2026-08-14

## Reviewer Comments

1. The introduction cited several ML papers but did not synthesize the established flow-boiling optical measurement literature or distinguish projected coverage from volumetric void fraction.
2. The manuscript risked presenting fine-tuning as the main innovation instead of addressing practical field pain points: measurement definition, dense/coalesced interfaces, tracking error, temporal dependence, validation leakage, and thermal/multimodal provenance.
3. A stale facility-figure caption said that acoustic-emission data were excluded, although the manuscript now contains a timestamp-registered AE state screen.
4. The package lacked a visible, evidence-bounded plan for advancing from union coverage to spatial, interfacial, bubble-dynamics, and multimodal quantities.

## Repeated Issues

The literature/claim-boundary concern recurs from prior reproducibility reviews: a same-sequence segmentation reconstruction and a large frame count do not establish transferable bubble dynamics, volumetric void fraction, or causal optical--thermal inference. The revision therefore changes the measurement framing and implementation roadmap rather than only adding caveat text.

## Changes Made

- Rewrote the Introduction as a mechanism- and measurement-driven synthesis of conventional flow-boiling imaging, ML segmentation/tracking, and the remaining validation gap.
- Added four verified references: photographic void-fraction processing, optical quantification of bubble/dryout/interface metrics, flow-regime/void-fraction segmentation, and VISION-iT's error-aware detection/tracking framework.
- Defined the paper's output as union-mask projected vapor coverage and stated why it is not volumetric void fraction.
- Added a state-trends discussion and a staged optical-analysis roadmap. Streamwise coverage and pixel-domain interface metrics are identified as the next feasible additions; tracking, dimensional statistics, volumetric void fraction, and causal multimodal analysis remain validation-gated.
- Corrected the AE facility caption to reflect the actual timestamp-registered screening boundary.

## Remaining Risks

- New references support the literature synthesis but do not improve the current same-sequence split, low instance AP, absent optical calibration, or lack of common trigger.
- No new spatial/interface metric is reported in the manuscript until the ROI geometry, algorithm, and case-level validation are implemented and checked.
- The added bibliographic records were cross-checked against DOI/publisher metadata; they still require the normal final reference-format check in the compiled journal style.

## Verification Completed

- `latexmk -pdf -outdir=tmp_latex_check_final -interaction=nonstopmode -halt-on-error main.tex`: passed in an isolated directory; the 22-page manuscript has no unresolved citation or cross-reference warnings after the final pass.
- The canonical `main.pdf` was locked by another Windows process, so it was not overwritten. The verified current PDF is `overleaf_applied_thermal_engineering/tmp_latex_check_final/main.pdf`.
- Rendered and visually inspected PDF pages 2--3, which contain the revised literature synthesis. Text, numbered citations, margins, and page transition were legible and free of overlap.
- `PYTHONPATH=src C:\\Users\\hanhu\\Anaconda3\\envs\\bubbleid\\python.exe -m pytest -q tests`: 40 passed.
- `git diff --check`: passed. The repository has substantial pre-existing modified and untracked content; no unrelated files were reverted or staged.
