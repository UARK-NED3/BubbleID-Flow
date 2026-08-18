# Flow-Boiling Optical Analysis Roadmap

## Purpose

BubbleID-Flow currently reports a validated-in-context **projected vapor coverage**: the fraction of a fixed image ROI occupied by the union of accepted vapor masks. It is not a volumetric void fraction, dryout fraction, bubble-size distribution, or flow-regime label. This roadmap converts the literature's useful optical outputs into staged additions with explicit data and validation requirements.

## Current Evidence Boundary

- The archived Mask R-CNN checkpoint and 130 annotated frames support same-sequence union-mask reconstruction only; the 26-image holdout is not independent by source sequence.
- The 45 V sequence reruns support frame-level projected-coverage uncertainty after autocorrelation adjustment.
- The camera ROI has no documented spatial registration to the heated wall or pixel-scale calibration.
- Instance AP is insufficient to treat individual bubble count, size, shape, or tracks as validated measurements.

## Priority Additions

| Priority | Analysis | Scientific value | Required implementation and validation | Current status |
| --- | --- | --- | --- | --- |
| 1 | Streamwise projected-coverage profile | Locates where vapor occupancy grows or recedes along the viewed channel. | Partition the fixed ROI into documented streamwise bins; report mask-union coverage and moving-block intervals; manually check representative bins across cases. | Feasible after ROI-coordinate review; not yet implemented. |
| 1 | Projected interface-length density | Provides an image-domain descriptor of liquid-vapor complexity beyond area alone. | Define contour extraction and pixel connectivity; calibrate pixels per length or report pixel-normalized values; quantify sensitivity to mask threshold and ROI borders. | Feasible only as a pixel-domain metric until calibration is recovered. |
| 2 | Mask-derived regime descriptors | Supports transparent screening of bubbly/elongated/continuous-vapor image states without asserting a universal flow-regime map. | Pre-register definitions, annotate complete held-out operating cases, and validate by case-level split; report ambiguity and failures. | Requires new annotations and an independent split. |
| 2 | Bubble size, aspect ratio, count, and trajectories | Enables comparison with bubble-dynamics literature and links to coalescence, transport, and wall rewetting. | Improve instance masks and tracking, exclude clipped/merged objects by documented rules, recover pixel calibration, and validate tracks/objects on held-out videos. | Blocked by low instance AP and absent calibration. |
| 3 | Volumetric void fraction or vapor-layer thickness | Connects imaging to a transport quantity used in flow-boiling models. | Establish channel-depth/viewing geometry assumptions and validate against an independent void-fraction or thickness measurement, or use a defensible multi-view reconstruction. | Not supported by the present 2D ROI. |
| 3 | Optical--thermal or optical--AE coupling | Tests whether interfacial changes contain information beyond the imposed operating controls. | Common trigger or verified clock synchronization, sensor coupling/calibration, replicated operating paths, and held-out-run analysis controlling for heat flux, mass flux, and subcooling. | Current result is timestamp-registered state screening only. |

## Design Principle

Each added descriptor must have a definition, units or pixel-domain status, ROI and border rules, model and threshold version, a case-level validation split, and an uncertainty treatment consistent with frame serial dependence. A new model output is not a new physical measurement until those links are demonstrated.
