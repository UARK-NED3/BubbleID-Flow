# CWRU Test 17 Multimodal Screening, 2026-08-13

## Scope and reviewer finding

The manuscript previously excluded the archived acoustic-emission (AE) files
because common-trigger synchronization and sensor coupling were unverified.
That exclusion was correct for time-resolved or causal claims, but the archive
does support a more limited, reproducible state-level screen when the
registration evidence is made explicit.

## Revision

- Added reusable EasyAE HIT/TIME parsers and a bounded WFS-prefix reader in the
  sibling AELab repository at `flow-boiling-ae/analysis/cwru_test17.py`.
  The reader uses `decode-wfs` message definitions and its count-to-voltage
  calibration without loading multi-gigabyte WFS files into memory.
- Added a BubbleID-Flow bridge at
  `scripts/analyze_cwru_multimodal_screening.py` and regenerated the 10 g/s
  state tables and `Figure_S1_timestamp_registered_multimodal_screening.pdf`
  under `outputs/aug9_model_analysis/multimodal_screening/`.
- Added a compact 10 g/s timestamp-registered screening method, result, figure,
  limitations, and software citations to the ATE manuscript.

## Directly verified data and registration

- Case: CWRU Test 17, `10gs_22C` (archive case folder `1`).
- Thermal start timestamp: `2025-10-17T11:41:47.605`.
- EasyAE start timestamp: `2025-10-17T11:42:13.000`.
- Applied archive offset: AE minus thermal start = `25.395 s`.
- Seven thermal state intervals (25--55 V, excluding the unmatched 45 V state)
  were shifted by that offset before selecting HIT and TIME records.
- WFS check: 512 decoded records, two channels, 1 MHz sample rate.

This is timestamp registration only. The archive does not establish a common
hardware trigger, clock uncertainty, calibrated sensor coupling, acoustic
source localization, or a physical acoustic-energy calibration.

## Observed screening result

Across the imposed 10 g/s voltage ramp, projected coverage reached 0.197 at
52.5 V and then fell to 0.076 at 55 V. At the same registered states, channel
1/channel 2 ASL rose from 24.38/23.38 dBAE to 35.49/37.61 dBAE and HIT rate
rose from 1.92/2.12 to 928/638 s^-1. This supports a descriptive multimodal
state screen only; it does not establish correlation free of voltage-ramp
confounding or synchronized optical--acoustic coupling.

## Verification

```powershell
# AELab synthetic parser and bounded WFS test
C:\Users\hanhu\Anaconda3\envs\bubbleid\python.exe -m pytest -q flow-boiling-ae\analysis\test_cwru_test17.py

# BubbleID-Flow regression tests
C:\Users\hanhu\Anaconda3\envs\bubbleid\python.exe -m pytest -q tests

# Manuscript compile
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

Results: the AELab test passed, all 40 BubbleID-Flow tests passed, and the
21-page PDF compiled with resolved references. Pages 15--17 were rendered and
visually inspected. The PDF has ordinary underfull-box warnings only.

## Remaining requirements before stronger AE claims

1. Use a common hardware trigger or a documented synchronization pulse across
   imaging, thermal DAQ, and EasyAE; quantify residual offset and drift.
2. Perform and archive pre/post-test coupling checks, sensor calibration, and
   geometry-specific propagation characterization.
3. Collect replicated, independently randomized operating states so voltage,
   heat flux, and optical state are not rank-confounded.
4. Define an acoustic endpoint and its physical units before reporting energy,
   source, regime, or predictive claims.
