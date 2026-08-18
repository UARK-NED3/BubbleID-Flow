# Superseded Markdown Manuscript Snapshot

> **Status (2026-08-09):** This historical Markdown draft contains results from
> an earlier checkpoint and sampled-frame analysis. It is retained for revision
> provenance only. Do not use its numerical values, active-vapor-length claims,
> or figure links for submission. The canonical, updated Applied Thermal
> Engineering manuscript is `overleaf_applied_thermal_engineering/main.tex`;
> its figures and evidence tables are under `outputs/aug9_model_analysis`.

# Multimodal Diagnostics of Flow Boiling Using BubbleID-Flow, Acoustic Emission, and Thermal Measurements

## Authors

Mohammad Ishraq Hossain, Daniel Curl, Farshad Barghi Golezani, Han Hu, and collaborators.

## Abstract

Flow boiling experiments generate coupled visual, thermal, and acoustic signatures, but these data streams are often analyzed separately. This manuscript develops a preliminary multimodal workflow that combines computer-vision bubble segmentation, acoustic-emission features, and reduced thermal-fluid measurements from heated microchannel flow boiling tests. BubbleID-Flow, a flow-boiling adaptation of BubbleID, is used to segment bubbles from high-speed images and compute projected vapor area fraction and vapor-covered streamwise length. These image-derived metrics are fused with heat flux, local heat-transfer coefficient, pressure-drop-related quantities, and acoustic-emission hit/energy metrics for four operating cases: `5gs_22C`, `10gs_22C`, `15gs_20C`, and `25gs_20C`. In the baseline `15gs_20C` case, projected vapor area fraction increases from low values at onset and intermediate states to approximately `0.28` near the CHF-adjacent state, while heat flux rises to approximately `36 W/cm2`. Cross-case synthesis shows that vapor coverage and vapor-covered streamwise length generally increase with heat flux; case-level Spearman rank checks give `rho_s = 0.57` to `0.89` for heat flux versus projected vapor area and `0.89` to `0.99` for heat flux versus active vapor length. AE absolute-energy trends are reported with window-quality labels; the AE-readiness matrix finds no current case ready for quantitative acoustic interpretation because pass-quality windows, contiguous-window provenance, trigger verification, and sensor-coupling verification are missing. The result is a reproducible analysis framework for linking optical vapor morphology, nonintrusive acoustic sensing, and thermal performance in flow boiling. The present analysis is preliminary because image/thermal/acoustic synchronization and segmentation uncertainty require further audit before quantitative lead-lag or prediction claims are made.

## 1. Introduction

Flow boiling is attractive for high-heat-flux thermal management because latent heat transport and bubble-induced mixing can remove large heat loads from compact heated surfaces. The same coupled physics also make flow boiling difficult to model and diagnose: local wall temperature, vapor distribution, pressure drop, and interfacial dynamics evolve together, especially near onset and CHF-adjacent conditions. A manuscript based only on thermal data risks missing the mechanisms behind changes in heat-transfer coefficient, while a manuscript based only on visualization risks underusing the available heat-transfer and acoustic information.

Prior work by Kharangate and collaborators has established a strong foundation for flow-boiling heat transfer, CHF mechanisms, visualization, and modeling in rectangular or microchannel configurations. The Case Western Reserve University Two-Phase Flow and Thermal Management Lab publication list includes recent studies on flow-boiling CHF and heat transfer with one-sided heating, PIV-based investigation of flow during flow boiling, and machine-learning boiling prediction from autonomous vision data. BubbleMask and related autonomous-vision studies show how high-speed images can be transformed into physically meaningful bubble features for flow-boiling prediction. In parallel, acoustic-emission approaches have been developed for phase-change diagnostics. NASA's "Acoustic Insights into Flow Condensation Mechanisms" project describes acoustic, modal, optical, and thermofluidic sensing for detecting condensation regime transitions, and recent APS work from Sun and collaborators focuses on AE sensing for flow condensation regime identification and local heat-transfer characterization.

The present work is distinguished from those streams by integrating all three diagnostic modalities in the same flow-boiling analysis. It is not only a visual bubble-extraction paper, and it is not only an acoustic-sensing paper. The intended contribution is a fused workflow in which BubbleID-Flow provides spatial vapor metrics, acoustic emission provides high-bandwidth signatures of interfacial activity, and reduced thermal data provide heat-transfer context. This multimodal framing is especially useful for building diagnostic indicators that can be robust when one modality is limited, for example when optical access is restricted or when AE signals require physical interpretation.

## 2. Experimental Data and Test Matrix

The current analysis uses October 17, 2025 CWRU Test 17 data from a heated microchannel two-phase flow loop with high-speed imaging and acoustic-emission sensing. The working fluid is deionized water. Four main operating cases are analyzed:

| Case | Nominal mass flow rate | Nominal inlet subcooling | Test folder |
| --- | ---: | ---: | --- |
| `5gs_22C` | 5 g/s | 22 degC | `2` |
| `10gs_22C` | 10 g/s | 22 degC | `1` |
| `15gs_20C` | 15 g/s | 20 degC | `3` |
| `25gs_20C` | 25 g/s | 20 degC | `4` |

The image folders are organized by applied-voltage or transition state, including onset and CHF-adjacent labels. The reduced thermal workbooks contain time, mass flow rate, fluid velocity, power, total heat flux, inlet subcooling, pressures, saturation temperature, local temperatures at seven streamwise locations, vapor quality estimates, and heat-transfer coefficient estimates. Acoustic-emission files include EasyAE hit features such as hit count, duration, amplitude, RMS, frequency metrics, and absolute energy. The current analysis uses the hit-based acoustic features for the first integrated manuscript pass.

The raw optical, thermal, and acoustic data are stored outside git under
`C:\Users\hanhu\Box\NED3_Share\Ishraq Hossain\CWRU\test17_17th Oct_Friday`.
Preliminary acoustic/thermal analysis files and experimental setup photographs
for the manuscript setup figure are stored under
`C:\Users\hanhu\Box\NED3_Share\0_NSF_CASIS_FBCE_Project\CWRU_visit_Oct_13_17_2025`,
including `CWRU_Oct_2025_Visit_Summary.pptx`.

## 3. Methods

### 3.1 BubbleID-Flow Image Analysis

BubbleID-Flow uses a Detectron2 Mask R-CNN model fine-tuned from manually annotated flow-boiling images. The current manuscript results use the local model folder `C:\Users\hanhu\Box\NED3_Share\0_BubbleID\BubbleID-Flow\detectron2_flow_mrcnn_roi485_70`, with `model_final.pth` as the inference weights. The same weight file is documented in `docs/model_artifact_manifest.csv` with its OSF archive URL and SHA256 checksum, while Detectron2 evaluation metrics and a held-out manual-mask validation panel remain pending. The present model analyzes a near-wall ROI defined as `0,485,1024,70`, which focuses on the region where vapor structures are visible in the current camera view. For each image, the model produces instance masks that are combined into a binary projected vapor mask. The principal image-derived metric is the projected vapor area fraction,

```text
alpha_A = bubble-mask pixels / total ROI pixels.
```

The analysis also computes an active vapor length fraction by identifying streamwise columns whose local vapor occupancy exceeds `0.05`. This quantity estimates the fraction of the field of view containing appreciable vapor activity.

### 3.2 Thermal Analysis

Thermal state summaries are obtained from the reduced Excel workbooks. The image-folder voltage labels are matched to thermal rows using the absolute voltage in the thermal input workbook with a tolerance of `+/-0.75 V`. For each matched state, the workflow calculates mean heat flux, mean power, mean inlet subcooling, mean pressure drop, mean heat-transfer coefficient across the seven streamwise locations, and downstream vapor quality estimate.

### 3.3 Acoustic-Emission Analysis

The first-pass acoustic analysis uses EasyAE hit tables. The script parses the hit file after the EasyAE header and computes hit rate, channel-specific hit rate, mean amplitude, and absolute-energy rate over thermal voltage windows. This alignment is provisional because the exact trigger/timestamp relationship between imaging, thermal acquisition, and AE acquisition still needs to be verified. Test notes also state that AE sensor mounting may have been inadequate, so absolute magnitudes and channel comparisons should be treated cautiously until coupling is audited. Therefore, this manuscript draft interprets AE trends as operating-state-matched signatures rather than precise temporal lead/lag behavior.

### 3.4 Multimodal Fusion

For each operating state, image, thermal, and acoustic metrics are merged into a state-level table. The workflow produces two levels of analysis: a baseline case figure for `15gs_20C` and cross-case synthesis figures for all four operating cases. The baseline figure demonstrates the full data pipeline, while the cross-case figure tests whether the same trends persist across mass flow rate and subcooling conditions.

Cross-case figures use only complete multimodal states with image metrics, matched thermal rows, and matched AE features. States without a thermal match remain in the raw state-summary files for traceability but are excluded from cross-modal plots and headline comparisons. In the current output snapshot, this rule excludes the `10gs_22C`/`45V` image state because no thermal rows are matched within the `+/-0.75 V` window.

The cross-case synthesis now writes `cross_case_trend_summary.csv`, which records state counts, AE-window quality counts, heat-flux/visual rank correlations, quality-gated vapor/AE rank correlations, and the state that reaches the maximum projected vapor area in each case. It also writes `cross_case_trend_sensitivity.csv`, which performs leave-one-state-out Spearman checks so the manuscript can distinguish robust optical trends from AE conclusions controlled by one influential state. These tables are the source for manuscript statements about monotonicity, AE agreement, and state sensitivity.

The synthesis also writes `cross_case_sampling_uncertainty.csv`, which recomputes optical sampling uncertainty from the per-frame image metrics. It reports Student-t 95% confidence-interval half-widths for the sampled mean projected vapor area and active vapor length in each image state. In the current snapshot, 29 image states carry a sampling warning, mostly because fewer than eight frames were available, but only four states exceed the 25% relative confidence-interval threshold for projected vapor area. The largest relative projected-vapor interval is `25gs_20C/35`, with an absolute half-width of `0.043`, or `38%` of the sampled mean.

The synthesis also writes `cross_case_segmentation_validation_plan.csv`, which
selects held-out manual-mask targets across onset or low-vapor, developed,
high-vapor or CHF-adjacent, and high-uncertainty states. This artifact is a
validation worklist rather than completed evidence; individual bubble-count,
size, coalescence, and instance-separation claims remain blocked until those
manual masks and segmentation metrics are archived.

The synthesis also writes `cross_case_thermal_response_checks.csv`, which
checks whether the reduced thermal rows provide defensible state-level context
for the heat flux and mean HTC quantities used in the figures. The artifact
supports state-level thermal interpretation in the current snapshot, but it
does not validate local optical-thermal registration, heat-loss correction,
thermocouple uncertainty, or HTC-equation details.

The synthesis now also writes `cross_case_ae_evidence_tiers.csv`. This table converts AE-window quality, pass-level window counts, overlap blockers, and leave-one-state-out sensitivity into a case-level claim scope. In the current tracked snapshot, `5gs_22C`, `10gs_22C`, and `15gs_20C` are classified as mixed-window snapshots because they contain overlap-blocked AE states, while `25gs_20C` is classified as an exploratory legacy-window snapshot because no pass-quality AE windows are available. Therefore, AE correlations should be reported as screening diagnostics only, not as evidence for a quantitative acoustic regime classifier.

The synthesis now also writes `cross_case_ae_readiness_matrix.csv`. This table
turns the recurring synchronization critique into explicit acceptance criteria:
each case must have enough pass-quality AE windows, enough nonblocked states,
complete contiguous-window provenance, verified trigger timing, and verified
sensor coupling before AE features can support quantitative acoustic claims. In
the current tracked snapshot, no case satisfies those criteria. The manuscript
therefore treats AE energy as a quality-tagged screening signal, not as a
calibrated regime classifier or timing measurement.

The synthesis now also writes `cross_case_ae_verification_status.csv` and
`cross_case_ae_remediation_plan.csv`. The verification-status table records
whether trigger synchronization and sensor coupling have been supplied for each
case; the current tracked package records zero trigger-verified and zero
sensor-coupling-verified cases. The remediation plan converts the failed gates
into case-level actions: `5gs_22C`, `10gs_22C`, and `15gs_20C` require
priority-1 contiguous-window reruns because they include overlap-blocked AE
windows, while `25gs_20C` requires a priority-2 provenance rerun before its
legacy screening status can be strengthened.

The synthesis now also writes `cross_case_claim_evidence_matrix.csv`. This matrix converts the generated trend, uncertainty, thermal-response, and AE evidence-tier artifacts into manuscript-safe claim boundaries. In the current snapshot, the optical heat-flux trends and state-level thermal context are supported with limits; AE comparisons are restricted to quality-tagged screening diagnostics; AE regime-classifier or acoustic lead-lag claims, individual bubble statistics, and local optical-thermal registration claims are explicitly marked as not supported until their validation artifacts exist.

## 4. Results

### 4.1 Baseline Case: `15gs_20C`

The baseline `15gs_20C` case shows a clear progression from lower vapor coverage at onset/intermediate states to stronger vapor coverage near the CHF-adjacent state. In the current sampled-frame analysis, the projected vapor area fraction ranges from approximately `0.061` to `0.283`, while heat flux ranges from approximately `7.55` to `36.30 W/cm2`. The representative overlays show that the vapor-covered region expands downstream as voltage increases.

![Baseline integrated panel](../outputs/multimodal/15gs_20C_baseline/15gs_20C_integrated_baseline_panel.png)

The integrated panel links this visual growth to the thermal and acoustic measurements. Mean heat-transfer coefficient increases through much of the sweep and then changes near the highest-voltage state, while AE activity varies strongly over the same operating range. The AE absolute-energy rate increases toward high-voltage states but drops in the final `55 CHF` window in the current provisional alignment, likely because the matched time window includes shutdown or transition behavior. This point is a useful warning: the acoustic signal is promising, but synchronization must be audited before interpreting exact state transitions.

![Representative overlays](../outputs/multimodal/15gs_20C_baseline/15gs_20C_representative_overlay_sheet.png)

### 4.2 Cross-Case Multimodal Trends

Across all four cases, projected vapor area fraction generally increases with heat flux, and active vapor length fraction also increases with heat flux. The `5gs_22C` case shows the largest visual vapor coverage in the current analysis, reaching approximately `0.348`, while `25gs_20C` reaches the highest heat flux, approximately `41.76 W/cm2`, with lower projected vapor coverage in the camera ROI. This difference is physically plausible because increasing mass flow can remove vapor more effectively and shift the relationship between vapor coverage and heat input.

The trend-summary table quantifies this visual interpretation. Spearman rank correlations between heat flux and projected vapor area fraction are positive for every case: `0.57` for `10gs_22C`, `0.85` for `15gs_20C`, `0.81` for `25gs_20C`, and `0.89` for `5gs_22C`. Active vapor length is more monotonic with heat flux, with `rho_s = 0.89` to `0.99` across the four cases. Leave-one-state-out checks keep the optical correlations positive after removing any single state; the maximum absolute change in `rho_s` is `0.14` for projected vapor area and `0.11` for active vapor length. These rank checks support the narrow optical claim that visible vapor occupation rises with thermal forcing in the current dataset, without implying a universal regime threshold.
The active-length statement is now additionally gated by `cross_case_active_threshold_sensitivity.csv`. The current tracked frame metrics predate the new active-threshold sweep, so the active-length trend remains a `phi_thr = 0.05` result until the per-case Detectron2 image summaries are regenerated with threshold-sweep outputs.

The thermal-response check supports the state-level thermal context used in the
same figure. Heat flux is monotonic with voltage in all four cases
(`rho_s = 1.00`), and mean HTC has positive rank agreement with heat flux
(`rho_s = 0.83` to `0.89`). These checks justify using heat flux and mean HTC
as reduced state descriptors, while keeping local optical-thermal coupling
claims blocked until registration and uncertainty propagation are completed.

The sampling-uncertainty audit qualifies this claim. Figure 5 now plots the
Student-t 95% confidence-interval half-widths from that audit rather than
frame-to-frame standard deviations. The current frame samples are adequate for
a first-pass state mean, but high relative intervals in `25gs_20C/35`,
`5gs_22C/27.5`, `15gs_20C/40`, and `10gs_22C/30V` show where the optical metric
should be regenerated from denser image sequences before claiming temporal
intermittency or fine state-to-state differences.

![Cross-case multimodal story](../outputs/multimodal/cross_case_synthesis/cross_case_multimodal_story.png)

The AE absolute-energy rate can increase with image-derived vapor activity, but the scatter is substantial and the current tracked windows are quality-limited. Four complete states are blocked for AE interpretation because their voltage-matched windows overlap earlier states; the remaining complete states are caution-level because the tracked summaries predate contiguous-window provenance metadata. After removing overlap-blocked states, Spearman rank agreement between projected vapor area and AE absolute-energy rate is `0.76` for `5gs_22C`, `0.66` for `10gs_22C`, and `0.71` for `25gs_20C`, but only `0.12` for `15gs_20C`. The leave-one-state-out sensitivity check confirms that the weak `15gs_20C` agreement is controlled by the final `55 CHF` state: removing only that state changes `rho_s` from `0.12` to `0.68`. The evidence-tier, AE verification-status, AE-readiness, and AE remediation-plan audits keep these AE relationships in a screening-only scope because every case lacks pass-quality AE windows, no case has supplied trigger/coupling verification, and no case satisfies the quantitative-readiness criteria in the current tracked snapshot. The `55 CHF` point is retained in the analysis but treated as a synchronization/coupling diagnostic flag because it combines high visible vapor coverage with very low matched-window AE energy.

![Cross-case state map](../outputs/multimodal/cross_case_synthesis/cross_case_state_map.png)

The state map now carries the acoustic evidence limits directly: overlap-blocked
AE states are gray in the AE-energy screening column, and the AE quality-weight
column remains on the absolute 0/0.5/1 interpretation scale. This prevents the
figure from implying full acoustic confidence when the current snapshot contains
only caution-level or blocked AE windows.

### 4.3 What the Multimodal Analysis Adds

The visual data identify where vapor is present in the near-wall field of view. The thermal data quantify the energetic forcing and heat-transfer response. The AE data capture high-bandwidth mechanical/interfacial activity that is not visible in a single optical frame. The combination is more informative than any one modality alone: vapor coverage can rise with heat flux, HTC can plateau or decline near transition, and AE energy can reveal intermittent or violent events that are not fully captured by time-averaged image metrics.

## 5. Discussion

The current results support the feasibility of multimodal boiling diagnostics, but several limitations must be addressed before journal submission. First, BubbleID-Flow segmentation is still an early model trained on limited annotations. It performs well enough for projected vapor coverage trends, but individual bubble counts and sizes remain less reliable because dense bubbles can merge and onset-state false positives occur. The segmentation-validation plan now identifies the specific manual-mask targets needed to test those weaknesses, but its current status is `planned_not_complete`. Second, the sampled-frame audit shows that image sampling remains a real uncertainty source rather than only a procedural caveat. Third, AE-to-thermal alignment is provisional and the AE mounting note introduces an additional coupling uncertainty. The AE-readiness matrix now records the missing pass-quality windows, contiguous-window provenance, trigger verification, and sensor-coupling verification that block quantitative acoustic use, while the AE remediation plan identifies the reruns and waveform/sensor checks needed to close those gates. Fourth, image-derived vapor fraction is a 2D projected area metric, not a calibrated 3D void fraction. Fifth, the thermal-response check supports state-level heat-flux and mean-HTC context, but heat-loss correction, pressure-drop reduction, HTC equations, thermocouple uncertainty, and camera-to-thermocouple registration still need independent audit.

These limitations define a productive next phase rather than weakening the manuscript. A strong final paper can frame the present workflow as a reproducible bridge between computer vision, acoustic sensing, and thermal reduction. The distinctive contribution is the integration and comparison of the modalities, not the claim that any single metric is complete.

The generated claim-evidence matrix should be treated as a scope gate during revision. Stronger language about AE classification, timing, individual bubbles, or local optical-thermal coupling should not be added until the matrix status changes from `not_supported_current_snapshot` through new validation evidence and the AE remediation-plan gates are closed.

## 6. Conclusions

1. A BubbleID-Flow Mask R-CNN model can convert high-speed flow-boiling images into projected vapor area fraction and vapor-covered streamwise length metrics.
2. In the baseline `15gs_20C` case, projected vapor area fraction spans approximately `0.061` to `0.283` over the sampled states while heat flux increases from approximately `7.55` to `36.30 W/cm2`.
3. Cross-case analysis shows that projected vapor coverage and active vapor length generally rise with thermal forcing across the four operating cases, with positive heat-flux/visual rank correlations in every case.
4. The reduced thermal rows support state-level heat-flux and mean-HTC context, but not local optical-to-thermocouple coupling claims.
5. AE absolute-energy trends are useful as quality-tagged, state-matched diagnostics in three cases, but the AE-readiness matrix, verification-status table, remediation plan, weak and state-sensitive `15gs_20C` rank agreement, and overlap-blocked windows show that synchronization and acoustic transfer mechanisms must be treated carefully.
6. The integrated workflow distinguishes this study from vision-only flow-boiling analysis and acoustic-only condensation diagnostics by fusing optical, thermal, and AE signatures in a single flow-boiling dataset.

## 7. Immediate Work Before Submission

- Verify image, thermal, and AE synchronization using trigger records or acquisition metadata.
- Regenerate the priority-1 AE cases with contiguous-window provenance and inspect the `15gs_20C`/`55 CHF` waveform window.
- Increase image sampling from 6-8 frames per state to complete image sequences or statistically justified samples.
- Complete the generated segmentation-validation plan and archive manual-mask
  metrics/overlays for the selected states.
- Audit thermal data reduction equations and uncertainty.
- Refine acoustic features with waveform-derived band power or spectrogram metrics for selected states.
- Replace preliminary figures with publication-formatted versions.

## References and Positioning Sources

1. Kharangate lab publication list, including flow boiling/CHF, PIV flow boiling, BubbleMask, and machine-learning boiling prediction work: https://case.edu/engineering/labs/tpftml/publications
2. Huang et al., "Machine Learning Boiling Prediction: From Autonomous Vision of Flow Visualization Data to Performance Parameter Theoretical Modeling," listed at Case Western Reserve University: https://commons.case.edu/facultyworks/1320/
3. Shingote et al., "Investigation of Flow Boiling Critical Heat Flux and Heat Transfer Within a Horizontally Oriented Channel With One-Sided Heating at Three Levels of Subcooled Inlet," Case Western Reserve University: https://commons.case.edu/facultyworks/1100/
4. NASA NTRS, "Acoustic Insights into Flow Condensation Mechanisms": https://ntrs.nasa.gov/citations/20250000264
5. APS DFD 2025 abstract, "Acoustic Sensing for Regime Identification and Local Heat Transfer Characterization of Flow Condensation": https://meetings-archive.aps.org/dfd/2025/k38/10/
