# BubbleID To Flow Boiling Adaptation Plan

## Core Hypothesis

BubbleID's Mask R-CNN segmentation backbone can transfer to flow boiling if it is fine-tuned on cropped flow-channel images with representative annotations.

## Expected Dataset Shift

- Bubbles are concentrated near the heated wall rather than distributed over a pool boiling surface.
- Many targets are partial, coalesced, sliding, or elongated.
- Channel walls, glare, metadata overlays, and dark unused image regions create false-positive risks.
- Validation must separate operating conditions or videos to avoid leakage from adjacent frames.

## Pilot Annotation Set

Start with 50-100 frames:

- multiple folders: `5gs_22C`, `10gs_22C`, `15gs_20C`, `25gs_20C`
- multiple heat-flux or condition subfolders
- low-density, dense, coalesced, glare-heavy, and low-contrast frames

## Metrics

- instance mask AP or IoU against manual masks
- bubble count error
- projected vapor area error
- equivalent diameter distribution agreement
- temporal consistency or ID switches after tracking is added
