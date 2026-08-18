# Applied Thermal Engineering Reviewer Response: 2026-08-13

Canonical manuscript: `overleaf_applied_thermal_engineering/main.tex`

## Overall response

The paper was re-scoped from an optical/thermal/acoustic diagnostic study to an
auditable machine-vision measurement study with traceable thermal context. New
analysis was performed for segmentation baselines, temporal dependence,
thermal-source provenance, forcing confounding, and held-out optical--thermal
association. Unsupported HTC, vapor-quality, friction, energy-balance, CHF, and
acoustic claims were removed rather than retained behind caveats.

## Major comments and actions

1. **The thermal contribution was underdeveloped.**
   Addressed with documented FC-72 geometry, electrical heat-flux and mass-flux
   equations, contiguous voltage-window selection, seven-location temperature
   summaries, and a cross-validated temperature-response test. The result is
   negative: projected coverage does not improve held-out temperature accuracy
   beyond heat flux, mass flux, and inlet subcooling.

2. **The facility and operating conditions were insufficiently documented.**
   Corrected the working fluid from deionized water to FC-72 and added the 2.5 mm
   by 5.0 mm channel, 114.6 mm heated length, 3.33 mm hydraulic diameter, seven
   sensor coordinates, mass-flux ranges, heat-flux range, imaging rate, ROI, and
   unmatched-state rule.

3. **Thermal reduction and uncertainty were not reproducible.**
   Added `scripts/audit_thermal_reduction.py` and a state-level audit table.
   Electrical heat flux is reconstructed from measured power and heated area to
   numerical precision. The source does not support defensible HTC, quality,
   friction, or energy-balance results because calibration, heat loss, property
   sources, and reduction details are incomplete; these endpoints are excluded.
   Within-window standard deviation is explicitly temporal variability, not
   instrument uncertainty. A propagated measurement-uncertainty budget remains
   blocked until instrument and calibration records are supplied.

4. **The image split was not independent and the threshold appeared tuned on the
   holdout.**
   The split audit now reports that 25 of 26 holdout images have a training image
   within one source-sequence index. The archived 0.30 operating threshold is
   retained as an existing workflow setting; the holdout sweep is labeled post
   hoc sensitivity and not model selection. A Gaussian baseline is fit on 77
   training images and calibrated on 27 sequence-grouped training images only.
   Experiment-held-out validation remains a required new-data action.

5. **The optical state streams were not consistently reproduced.**
   The paper now distinguishes 37 archived state summaries from four complete
   45 V sequence reruns. The complete-sequence means agree with archived values
   to 0.00085 MAE. A checkpointed all-state job also completed three low-voltage
   5 g/s states; their full-sequence means differ from the archived summaries by
   0.00115--0.00296. Thirty states still lack complete reruns.

6. **Independent-frame Student-t intervals ignored temporal autocorrelation.**
   Replaced primary intervals with a 5000-resample circular moving-block
   bootstrap. Integrated autocorrelation times are 9.6--25.0 frames and effective
   sample sizes are 3.5--11.2, making intervals 2.0--3.6 times wider than the
   independent-frame diagnostic.

7. **Simple and learned baselines were missing.**
   Added fixed Otsu morphology and a training-only Gaussian pixel classifier.
   Holdout coverage MAE is 0.1891, 0.0327, and 0.0051 for Otsu, Gaussian, and
   Mask R-CNN, respectively.

8. **Optical--thermal correlations were confounded by the voltage sweep.**
   Added an explicit confounding audit: voltage and heat flux have Spearman
   correlation 1.0 in all four cases. Ridge models evaluated by leave-one-state-
   out and leave-one-case-out validation show no incremental temperature
   accuracy from projected coverage.

9. **The term CHF-adjacent was undefined.**
   Removed it. Folder names are identified as operator labels without an
   objective onset, dryout, or CHF criterion. Final folders are called
   operator-labeled endpoints and are not used to claim CHF.

10. **The acoustic-emission analysis was immature.**
    Removed acoustic data from the quantitative study, abstract, keywords,
    results, conclusions, highlights, and graphical abstract. The archive is
    acknowledged only to explain scope; future use requires trigger and coupling
    verification.

11. **The literature review was too narrow.**
    Added recent primary studies on U-Net and deep-learning bubble segmentation,
    heat-flux estimation, thermal-field reconstruction, and the 2026 large-scale
    ATE mini-channel study. The paper is positioned as a small-data audit and
    claim-boundary study rather than a larger predictive contribution.

12. **Repository-level reproducibility was incomplete.**
    Added deterministic analysis scripts, tests, manifests, source hashes,
    baseline outputs, temporal summaries, thermal audit outputs, association
    outputs, and a package audit aligned with the revised scope. Eleven small
    evidence artifacts are allowlisted for version control; raw data, weights,
    and bulk outputs remain excluded. The OSF model link and checkpoint SHA256
    are retained.

## Minor comments

- Standardized the endpoint as projected vapor coverage and defined it as a
  two-dimensional union-mask pixel fraction, not volumetric void fraction.
- Added uncertainty and variability definitions to tables and captions.
- Rebuilt the facility schematic, optical plots, baseline plot, association
  plot, highlights, graphical abstract, cover letter, and Overleaf inventory.
- Abrar Fahim is first author; the requested author order and affiliations are
  retained. Stephen Pierson's and Chirag Kharangate's CRediT roles, grant numbers,
  competing-interest confirmation, and contributor approvals remain human gates.

## Re-review verdict

The revised manuscript addresses every reviewer comment with analysis, scope
correction, or an explicit new-evidence gate. It is substantially stronger and
internally auditable for same-sequence projected-coverage measurement. It is not
yet submission-ready because experiment-held-out validation, the remaining 30
state-sequence reruns, propagated thermal measurement uncertainty, and author/funding
confirmations cannot be manufactured from the supplied archive.
