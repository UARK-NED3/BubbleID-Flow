# Figure and Conclusion Revision Log -- 2026-08-17

## Requested Revisions

- Use Arial, larger final-size text, consistent symbols and colors, nonbold
  external subfigure labels, closed black plotting boxes, and dashed
  guide-to-the-eye trend lines.
- Move the Figure 5(d) legend away from the curves; retain dashed vertical
  markers for the archived 0.30 score threshold.
- Remove titles and standardize the four plot boxes in the optical-results
  figure; keep labels clear of axes and data in subsequent four-plot figures.
- Replace the bulleted conclusion with a connected concluding paragraph.

## Changes Made

- Updated the producing scripts to use Arial for ordinary and math-rendered
  figure text, 9--10 pt final-size labels and ticks, the common
  blue/green/orange/magenta case palette, and black closed axes.
- Regenerated the facility, model-output, robustness, baseline, optical,
  optical--thermal, and timestamp-registered acoustic figures from their
  existing analysis artifacts. Connecting lines now use dashed styles where
  they guide the eye; scatter-only evidence remains unconnected.
- Moved the Figure 5(d) legend below its axes. The vertical 0.30 markers in
  Figure 5(c,d) remain dashed because they identify the archived operating
  setting, not a physical critical threshold.
- Removed plot titles from the optical-results figure, enforced equal plot-box
  aspect ratios, and positioned nonbold `(a)`--`(d)` labels above the axes.
- Rewrote the Conclusions section as a single evidence-bounded paragraph.
- Updated the ATE package audit so its acoustic claim-scope gate verifies the
  manuscript's timestamp-registration and noncausal boundary rather than the
  obsolete requirement to exclude all acoustic data.

## Remaining Risk

- The regenerated data figures contain Arial only. The two project-team
  schematic PDFs still embed the original Calibri and Wingdings elements.
  Their editable PowerPoint source was identified, but this environment lacks
  the required presentation-edit runtime for a safe re-export. The source deck
  was not modified.

## Verification

- Rendered and visually inspected the regenerated robustness, optical-results,
  and optical--thermal figures at final journal scale.
- Audited embedded fonts with `pdffonts`; all regenerated data figures embed
  Arial only.
- Recompiled the manuscript in
  `overleaf_applied_thermal_engineering/tmp_latex_figure_style_2026-08-17`.
- `PYTHONPATH=src C:\Users\hanhu\Anaconda3\envs\bubbleid\python.exe -m pytest -q tests`:
  40 passed.
- `python scripts\audit_ate_submission_package.py`: 0 errors; the six remaining
  blockers are pre-existing author-confirmation, funding, and data-release
  submission placeholders.
- `git diff --check`: passed.
