# Key Figures for the BubbleID-Flow ATE Manuscript

The canonical figure package is the flat directory
`overleaf_applied_thermal_engineering`. Numerical plots are generated from the
Aug. 9 checkpoint evidence by `scripts/prepare_aug9_optical_results.py`.

## Figure 1. Experimental Facility and Data Streams

Establishes the loop, image, thermal, and acoustic data streams and the four
operating cases. The camera-to-heater and camera-to-thermocouple registration is
not calibrated, so the figure supports facility context rather than local
optical-thermal mapping.

## Figure 2. Annotation Dataset Preparation

Directly uses Abrar Fahim's schematic showing frame selection, Labelme
annotation, near-wall ROI cropping, and COCO conversion. The manuscript states
that `bubble` and `bubble_cluster` labels are merged into one vapor-region class.

File: `Figure_2_dataset_preparation_pipeline.pdf`.

## Figure 3. Fine-Tuning Architecture

Directly uses Abrar Fahim's Mask R-CNN fine-tuning schematic. The caption and
methods provide the audited settings: ResNet-50 FPN, 2000 iterations, batch size
1, learning rate `2.5e-4`, anchor sizes 8-128 px, and one output class.

File: `Figure_3_finetuning_architecture.pdf`.

## Figure 4. Updated Model Outputs

Shows raw and predicted 45 V ROIs for all four cases using the Aug. 9 checkpoint,
score threshold 0.30, and 300 detections per image. It visually anchors the
combined-mask metric and documents merge, missed-small-structure, and enclosed-
liquid failure modes.

Source: `outputs/aug9_model_analysis/Figure_4_aug9_model_outputs.pdf`.

## Figure 5. Updated Optical Results

Remade in the manuscript's Matplotlib style rather than using the supplied
OriginLab plots. Panels show all 37 provided state summaries versus voltage,
matched heat flux, every available 45 V frame, and the direct 45 V reproduction
comparison. This is the primary quantitative figure.

Source: `outputs/aug9_model_analysis/Figure_5_aug9_optical_results.pdf`.

## Figure 6. Thermal and Acoustic Context

Remade in the manuscript style. It joins updated optical coverage to heat flux,
mean HTC, and quality-tagged AE energy. Open markers denote caution windows and
crosses denote overlap-blocked windows. AE remains screening-level because
trigger synchronization and sensor coupling are unverified.

Source: `outputs/aug9_model_analysis/Figure_6_aug9_multimodal_context.pdf`.

## Figure 7. Synchronization Audit

Retains the state-window audit for the 15 g/s case. It explains why no acoustic
lead-lag or regime-classification claim is made.

## Graphical Abstract

Regenerated from the Aug. 9 representative ROI, mask overlay, and heat-flux plot.
It reports the internal-holdout combined-mask metrics and 45 V reproduction MAE,
without the superseded active-vapor-length metric.

Source: `outputs/aug9_model_analysis/Graphical_Abstract.pdf`.
