# Baseline Multimodal Result: `15gs_20C`

## Purpose

This note records the first integrated BubbleID-Flow analysis combining image-derived
vapor metrics, reduced thermal data, and acoustic-emission hit features for the
`15gs_20C` case.

## Inputs

- Image root:
  `C:\Users\hanhu\Box\NED3_Share\Ishraq Hossain\CWRU\test17_17th Oct_Friday\Test17_Flow_Loop_and_Imaging\Images\15gs_20C`
- Reduced thermal workbook:
  `C:\Users\hanhu\Box\NED3_Share\Ishraq Hossain\CWRU\test17_17th Oct_Friday\Flow Loop Dataset\15gs_20C\15gs_20C.xlsx`
- Thermal input workbook with voltage:
  `C:\Users\hanhu\Box\NED3_Share\Ishraq Hossain\CWRU\test17_17th Oct_Friday\Flow Loop Dataset\15gs_20C\15gs_20C_IN_with_units.xlsx`
- Acoustic-emission hit file:
  `C:\Users\hanhu\Box\NED3_Share\Ishraq Hossain\CWRU\test17_17th Oct_Friday\3\HIT_15gs_20C.TXT`
- Segmentation model:
  `outputs\detectron2_flow_mrcnn_roi485_70\model_final.pth`

## Analysis Settings

- ROI: `0,485,1024,70`
- Mask R-CNN score threshold: `0.30`
- Image sample: 8 evenly spaced frames per voltage state
- Thermal state matching: rows where `abs(voltage) ± 0.75 V` around the image-folder voltage
- AE state matching: provisional test-relative time windows from thermal state matching

## Outputs

- Integrated figure:
  `outputs\multimodal\15gs_20C_baseline\15gs_20C_integrated_baseline_panel.png`
- Representative mask overlay sheet:
  `outputs\multimodal\15gs_20C_baseline\15gs_20C_representative_overlay_sheet.png`
- State summary CSV:
  `outputs\multimodal\15gs_20C_baseline\15gs_20C_multimodal_state_summary.csv`
- Per-frame image metrics:
  `outputs\multimodal\15gs_20C_baseline\15gs_20C_image_frame_metrics.csv`

## First Observations

The thermal forcing increases monotonically through the sweep, reaching roughly
`36 W/cm2` near the `55 CHF` state. The image-derived projected vapor area
fraction is low-to-moderate in the early states and then rises strongly above
about `45 V`, reaching roughly `0.28` at the CHF-adjacent state. This is
consistent with visual growth of the vapor-covered region in the representative
mask overlays.

The acoustic hit-rate and absolute-energy trends show strong activity over the
boiling sweep, with acoustic energy increasing toward high-voltage states.
However, the AE-to-thermal matching in this first pass assumes a shared
test-relative time base. That assumption must be verified using acquisition
trigger metadata or another synchronization marker before making manuscript
claims about exact AE lead/lag behavior.

## Current Limitations

- The `25_ONSET` representative overlay includes a visible false-positive or
  over-segmented region near the left side of the cropped ROI.
- Only 8 frames per state were sampled for this first pass.
- The image model may merge dense adjacent bubbles, so bubble count and size
  distributions should be treated more cautiously than total vapor coverage.
- AE alignment is provisional.
- Camera pixel-to-length calibration and camera field-of-view location relative
  to thermocouple positions still need to be verified.

## Manuscript Use

This baseline case is suitable as the first demonstration figure for the
multimodal workflow section. It supports a preliminary result narrative:

1. Heat flux and wall heat-transfer metrics rise with applied voltage.
2. BubbleID-Flow detects increasing vapor coverage downstream as heat input
   rises.
3. Acoustic-emission energy/activity changes over the same operating sweep.
4. The integrated metrics can be used to compare onset, developed boiling, and
   CHF-adjacent states once synchronization and segmentation uncertainty are
   tightened.
