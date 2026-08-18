# Manuscript Validation Readiness Audit

Generated: 2026-08-18 08:08:03

## Summary

- BLOCKER: 3
- WARN: 2
- PASS: 5

## Metrics

- Same-sequence holdout proximity: 25 of 26 images
- Complete regenerated state sequences: 7 of 37
- Model artifact directory checked: C:\Users\hanhu\Box\NED3_Share\0_BubbleID\BubbleID-Flow\detectron2_flow_mrcnn_roi485_70
- Model artifact manifest checked: docs\model_artifact_manifest.csv

## Findings

- **BLOCKER - Experiment-held-out segmentation validation:** The current holdout is one source sequence; a new operating run must be annotated and held out.
- **PASS - Segmentation baselines:** Deep-model coverage error is lower than the training-only learned baseline.
- **BLOCKER - Complete state-sequence validation:** 30 archived state summaries still lack complete regenerated frame outputs.
- **PASS - Temporal dependence:** All common 45 V states use moving-block intervals.
- **BLOCKER - Thermal measurement uncertainty:** Instrument calibration, heat-loss, and uncertainty records are required before derived heat-transfer endpoints can be validated.
- **PASS - Thermal claim boundary:** Unsupported derived thermal endpoints are enumerated and excluded.
- **PASS - Incremental optical validation:** Projected coverage does not improve either cross-validated thermal model.
- **WARN - Spatial registration:** Camera-to-heater and camera-to-sensor registration remain unavailable.
- **WARN - Transition labels:** No objective onset, dryout, or CHF criterion was supplied; operator labels remain non-quantitative.
- **PASS - Model validation artifacts:** Model and eval files are present.
