# ATE Submission Package Audit

Generated: 2026-08-18 08:08:05

## Summary

- BLOCKER: 6
- WARN: 9
- PASS: 53

## Metrics

- Abstract word count: 250
- Keyword count: 7 (Flow boiling, Computer vision, Projected vapor coverage, Mask R-CNN, FC-72, Temporal uncertainty, Reproducibility)
- Citation keys used: 19
- Bibliography entries: 23
- Highlight count: 5
- Highlight 1 length: 72 characters
- Highlight 2 length: 71 characters
- Highlight 3 length: 70 characters
- Highlight 4 length: 74 characters
- Highlight 5 length: 74 characters
- Optical states: 37
- Baseline coverage MAE: Mask R-CNN=0.0051, Otsu morphology=0.1891, Pixel Gaussian=0.0327
- Temporal effective sample size range: 3.52 to 11.20
- Additional complete state sequences: 3
- Thermally matched states: 36
- Maximum heat-flux reconstruction delta: 1.421e-14 W/cm2
- 5 g/s peak coverage: 0.247
- 15 g/s peak coverage: 0.190
- 10 g/s peak coverage: 0.197
- 25 g/s peak coverage: 0.113
- 45 V reproduction MAE: 0.00085
- holdout mean IoU: 0.652
- holdout mean Dice: 0.769
- holdout projected-area MAE: 0.0051
- same-index holdout images: 10
- adjacent-index holdout images: 25
- Versioned current evidence artifacts visible to git: 13 of 13

## Findings

- **PASS - main.tex:** Found overleaf_applied_thermal_engineering/main.tex
- **PASS - references.bib:** Found overleaf_applied_thermal_engineering/references.bib
- **PASS - highlights.tex:** Found overleaf_applied_thermal_engineering/highlights.tex
- **PASS - Abstract:** Abstract is within the 250-word ATE limit.
- **PASS - Keywords:** Keyword count is in a normal journal range.
- **PASS - Required sections:** Found: CRediT authorship contribution statement
- **PASS - Required sections:** Found: Declaration of competing interest
- **PASS - Required sections:** Found: Funding
- **PASS - Required sections:** Found: Data availability
- **PASS - Required sections:** Found: Declaration of generative AI and AI-assisted technologies
- **BLOCKER - Submission placeholder:** Line 293: contains 'contribution roles to be confirmed'.
- **BLOCKER - Submission placeholder:** Line 293: contains 'contribution roles to be confirmed'.
- **BLOCKER - Submission placeholder:** Line 293: contains 'all roles require author confirmation'.
- **BLOCKER - Submission placeholder:** Line 297: contains 'all authors must confirm'.
- **BLOCKER - Submission placeholder:** Line 301: contains 'remain to be verified before submission'.
- **BLOCKER - Submission placeholder:** Line 315: contains 'should be finalized with all contributors'.
- **PASS - Figure package:** Found Overleaf file: Figure_1_facility_data_streams.pdf
- **PASS - Figure inclusion:** Referenced or packaged: Figure_1_facility_data_streams.pdf
- **WARN - Figure outputs:** Missing source output: outputs\ate_submission\figures\Figure_1_facility_data_streams.pdf
- **PASS - Figure package:** Found Overleaf file: Figure_2_dataset_preparation_pipeline.pdf
- **PASS - Figure inclusion:** Referenced or packaged: Figure_2_dataset_preparation_pipeline.pdf
- **WARN - Figure outputs:** Missing source output: outputs\aug9_model_analysis\abrar_schematic_slide_1.pdf
- **PASS - Figure package:** Found Overleaf file: Figure_3_finetuning_architecture.pdf
- **PASS - Figure inclusion:** Referenced or packaged: Figure_3_finetuning_architecture.pdf
- **WARN - Figure outputs:** Missing source output: outputs\aug9_model_analysis\abrar_schematic_slide_2.pdf
- **PASS - Figure package:** Found Overleaf file: Figure_4_aug9_model_outputs.pdf
- **PASS - Figure inclusion:** Referenced or packaged: Figure_4_aug9_model_outputs.pdf
- **WARN - Figure outputs:** Missing source output: outputs\aug9_model_analysis\Figure_4_aug9_model_outputs.pdf
- **PASS - Figure package:** Found Overleaf file: Figure_5_segmentation_robustness.pdf
- **PASS - Figure inclusion:** Referenced or packaged: Figure_5_segmentation_robustness.pdf
- **PASS - Figure outputs:** Found generated file: Figure_5_segmentation_robustness.pdf
- **PASS - Figure package:** Found Overleaf file: Figure_6_segmentation_baselines.pdf
- **PASS - Figure inclusion:** Referenced or packaged: Figure_6_segmentation_baselines.pdf
- **WARN - Figure outputs:** Missing source output: outputs\aug9_model_analysis\segmentation_baselines\Figure_segmentation_baselines.pdf
- **PASS - Figure package:** Found Overleaf file: Figure_5_aug9_optical_results.pdf
- **PASS - Figure inclusion:** Referenced or packaged: Figure_5_aug9_optical_results.pdf
- **WARN - Figure outputs:** Missing source output: outputs\aug9_model_analysis\Figure_5_aug9_optical_results.pdf
- **PASS - Figure package:** Found Overleaf file: Figure_7_optical_thermal_association.pdf
- **PASS - Figure inclusion:** Referenced or packaged: Figure_7_optical_thermal_association.pdf
- **WARN - Figure outputs:** Missing source output: outputs\aug9_model_analysis\optical_thermal_association\Figure_6_optical_thermal_association.pdf
- **PASS - Figure package:** Found Overleaf file: Graphical_Abstract.pdf
- **PASS - Figure inclusion:** Referenced or packaged: Graphical_Abstract.pdf
- **WARN - Figure outputs:** Missing source output: outputs\aug9_model_analysis\Graphical_Abstract.pdf
- **PASS - Citations:** All cited keys exist in references.bib.
- **WARN - Citations:** Unused bib entries: Comelli2024Image, Na2025Thermal, Na2026Resource, Soibam2023Segmentation
- **PASS - Highlights:** Five highlights are present.
- **PASS - Highlight 1:** Within 85 characters.
- **PASS - Highlight 2:** Within 85 characters.
- **PASS - Highlight 3:** Within 85 characters.
- **PASS - Highlight 4:** Within 85 characters.
- **PASS - Highlight 5:** Within 85 characters.
- **PASS - State summaries:** All four cases are present.
- **PASS - Segmentation baselines:** Mask R-CNN outperforms both holdout baselines.
- **PASS - Temporal uncertainty:** All complete sequences use wider autocorrelation-aware intervals.
- **PASS - Partial all-state rerun:** Three additional complete sequences remain separate and traceable.
- **PASS - Thermal provenance:** Electrical heat flux is reconstructed and the single unmatched optical state is explicit.
- **PASS - Forcing confounding:** Voltage and heat flux are perfectly rank-confounded in all cases.
- **PASS - Incremental optical test:** Projected coverage does not improve either cross-validated thermal baseline.
- **PASS - Claim scope:** working fluid: synchronized
- **PASS - Claim scope:** projected quantity: synchronized
- **PASS - Claim scope:** operator labels: synchronized
- **PASS - Claim scope:** thermal exclusions: synchronized
- **PASS - Claim scope:** acoustic claim boundary: synchronized
- **PASS - Figure evidence wording:** Optical figure points to autocorrelation-aware intervals.
- **PASS - Figure evidence wording:** Baseline and optical-thermal figures define their evidence and variability.
- **PASS - Aug. 9 result synchronization:** Checkpoint, holdout, and complete-sequence headline values are synchronized.
- **PASS - Segmentation robustness:** Archived predictions reproduce the selected 0.30/300 coverage metric and include split and threshold audits.
- **PASS - Evidence artifact versioning:** Current manuscript evidence artifacts are versionable.
