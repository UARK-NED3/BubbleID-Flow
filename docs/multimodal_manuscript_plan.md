# Multimodal Flow-Boiling Manuscript Plan

## Working Title

Acoustic and visual signatures of flow boiling regime evolution in a heated microchannel.

## Central Question

Can synchronized thermal, acoustic-emission, and high-speed image analysis reveal the onset,
growth, and critical-transition behavior of flow boiling more clearly than any single
measurement stream alone?

## Available Data

### Test Matrix

The October 17, 2025 CWRU Test 17 data use four main operating conditions:

| Test | Case label | Nominal flow rate | Nominal subcooling |
| --- | --- | ---: | ---: |
| 1 | `10gs_22C` | 10 g/s | 22 degC |
| 2 | `5gs_22C` | 5 g/s | 22 degC |
| 3 | `15gs_20C` | 15 g/s | 20 degC |
| 4 | `25gs_20C` | 25 g/s | 20 degC |

The image folders are organized by case and applied-voltage/onset/CHF state, for example:

- `5gs_22C`: `25`, `27.5`, `30`, `35`, `37.5`, `40`, `42.5`, `45`, `47.5`, `49`, `50`, `52CHF`
- `10gs_22C`: `25V`, `30V`, `35V`, `40V`, `45V`, `50V`, `52.5V`, `55V`
- `15gs_20C`: `25_ONSET`, `30`, `35`, `40`, `45`, `50`, `52.5`, `54`, `55 CHF`
- `25gs_20C`: `30_Onset`, `35`, `40`, `45`, `50`, `55`, `57.5`, `59CHF`

### Image Data

Raw high-speed images are under:

```text
C:\Users\hanhu\Box\NED3_Share\Ishraq Hossain\CWRU\test17_17th Oct_Friday\Test17_Flow_Loop_and_Imaging\Images
```

BubbleID-Flow currently provides:

- ROI-based Mask R-CNN bubble segmentation.
- Binary bubble masks and overlays.
- Projected vapor area fraction profiles along the flow direction.

Candidate image-derived metrics:

- projected vapor area fraction, global and streamwise-resolved
- active boiling length or vapor-front location
- bubble count, area, perimeter, equivalent diameter, and shape descriptors
- connected vapor-cluster length and intermittency
- temporal fluctuation of vapor area fraction across image sequences

### Thermal/Flow Data

Reduced thermal/flow workbooks are under:

```text
C:\Users\hanhu\Box\NED3_Share\Ishraq Hossain\CWRU\test17_17th Oct_Friday\Flow Loop Dataset
```

Representative workbook columns include:

- time
- mass flow rate
- fluid velocity
- power
- total heat flux
- inlet subcooling
- inlet and outlet pressure
- inlet and outlet temperature
- saturation temperature
- local wall temperatures at `x1` to `x7`
- local quality at `x1` to `x7`
- local heat-transfer coefficient at `x1` to `x7`
- friction-factor estimates

Thermocouple streamwise positions documented in the visit summary:

```text
x = [0.0054, 0.0227, 0.0400, 0.0573, 0.0746, 0.0919, 0.1092] m
```

Candidate thermal metrics:

- heat flux
- wall superheat at `x1` to `x7`
- local and average heat-transfer coefficient
- inlet/outlet vapor quality
- pressure drop and inferred friction factor
- onset and CHF-adjacent operating points

### Acoustic Data

Acoustic-emission outputs are organized by test number, with processed figures in:

```text
Plot_Hit
Plot_Time
```

Available hit-based features include:

- rise time
- count
- energy and absolute energy
- duration
- average, reverberation, initiation, centroid, and peak frequency metrics
- RMS
- amplitude
- ASL

Available continuous features include:

- RMS
- threshold
- absolute energy
- ASL

Candidate acoustic metrics:

- windowed RMS and absolute energy
- hit rate
- peak/centroid frequency trends
- broadband spectral energy in physically meaningful frequency bands
- AE intermittency and burst statistics
- channel-to-channel delay or amplitude ratio if synchronization supports it

## Integration Strategy

1. Build a case manifest.
   - Map each case to test ID, flow rate, subcooling, image folders, thermal workbook,
     AE processed files, and waveform-streaming folders.
   - Record voltage or heat-flux state for each image folder.

2. Establish time/condition alignment.
   - Use thermal workbook timestamps and DC power/voltage levels to identify quasi-steady
     windows corresponding to each image folder.
   - Use AE time stamps or sample-index ranges to extract matching windows.
   - Treat image folders without exact timestamps as operating-condition matched until
     synchronization metadata are verified.

3. Compute image metrics.
   - Run BubbleID-Flow masks for representative frames or complete sequences.
   - Compute global and streamwise projected vapor area fraction.
   - Extract bubble count and size distributions when instance masks are reliable enough.

4. Compute thermal metrics.
   - Use existing reduced workbooks for heat flux, local HTC, quality, wall temperature,
     subcooling, and pressure drop.
   - Recalculate only if equations or units need auditing.

5. Compute acoustic metrics.
   - Start with processed hit/time outputs for robust first-pass trends.
   - Add waveform spectrograms and band power only for selected baseline cases and transition
     cases to avoid a manuscript becoming a signal-processing catalog.

6. Fuse metrics by operating state.
   - Compare image vapor fraction, acoustic energy/RMS/hit rate, and thermal HTC/quality
     across increasing voltage or heat flux.
   - Identify onset, developed boiling, and CHF-adjacent behavior.
   - Use correlation and lead/lag analysis only after synchronization is verified.

## Candidate Manuscript Figures

1. Experimental setup and sensor layout.
   - Flow-loop schematic, test-section image, heater/sensor locations, AE channel locations,
     and camera field of view.

2. Data-fusion workflow.
   - Raw images to BubbleID-Flow masks, AE waveforms/features, thermal workbooks, and fused
     operating-state table.

3. Baseline case demonstration.
   - One case, likely `15gs_20C`, showing thermal time trace, AE metric, representative image,
     bubble mask, and vapor fraction profile.

4. Boiling progression with increasing heat input.
   - Representative masks and vapor profiles across voltage states from onset to CHF-adjacent
     operation.

5. Thermal response versus visual vapor metrics.
   - Local HTC or wall superheat compared with global/projected vapor area fraction and
     vapor-front location.

6. Acoustic response versus visual vapor metrics.
   - AE RMS, absolute energy, hit rate, or frequency-band energy compared with image-derived
     vapor fraction.

7. Cross-condition map.
   - Flow rate/subcooling effects on onset, vapor development, AE activity, and heat-transfer
     behavior.

## Manuscript Structure

1. Introduction
   - Motivation: multiphysics diagnostics for flow boiling and thermal management.
   - Gap: visual, thermal, and acoustic diagnostics are often analyzed separately.
   - Contribution: integrated computer-vision, AE, and thermal analysis of flow boiling.

2. Experimental Methods
   - Flow loop, working fluid, test section, heating, flow control, and instrumentation.
   - High-speed imaging and BubbleID-Flow segmentation workflow.
   - AE sensing and signal processing.
   - Thermal data reduction and uncertainty considerations.

3. Data Integration Methods
   - Case manifest and synchronization assumptions.
   - Image-derived vapor metrics.
   - Acoustic metrics.
   - Thermal metrics.
   - Fusion and statistical comparison methods.

4. Results and Discussion
   - Baseline case.
   - Evolution from onset to developed boiling.
   - Thermal-image coupling.
   - Acoustic-image coupling.
   - Cross-condition comparison and limitations.

5. Conclusions
   - Key findings about diagnostic coupling.
   - Practical value of BubbleID-Flow plus AE/thermal sensing.
   - Next steps for better synchronization, annotation, and uncertainty quantification.

## Immediate Next Steps

1. Create a machine-readable manifest for the four test cases and all image voltage folders.
2. Choose one baseline case, recommended: `15gs_20C`.
3. For that case, compute image vapor fraction profiles for all image folders.
4. Load the corresponding reduced thermal workbook and extract heat flux, HTC, pressure drop,
   and quality at matching operating states.
5. Load processed AE hit/time data and compute windowed metrics for matching states.
6. Produce a first integrated figure panel for the baseline case.
7. Draft the Methods and baseline Results sections once the first integrated panel is verified.

## Open Items To Verify

- Exact timestamp or trigger relationship between image acquisition, thermal DAQ, and AE DAQ.
- Whether image folder names correspond directly to applied voltage, heat flux plateau, or
  another operating-state marker.
- Camera pixel-to-length calibration and field-of-view location relative to thermocouple
  positions.
- AE sensor channel placement and coupling quality for each test.
- Thermal uncertainty, heat-loss correction, and whether existing calculated quantities should
  be independently audited before publication.
