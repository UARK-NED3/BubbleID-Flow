# Key Figures for the BubbleID-Flow Multimodal Manuscript

## Figure 1. Experimental Facility and Data Streams

**Purpose:** Establish the physical experiment and show why the dataset is multimodal.

**Panel plan:**

- Flow-loop schematic with pump, preheater, heated microchannel test section, condenser/chiller, and DAQ.
- Test-section photograph or schematic with heater, flow direction, thermocouple locations, AE sensor locations, and camera field of view.
- Test matrix table: `5gs_22C`, `10gs_22C`, `15gs_20C`, `25gs_20C`.

**Status:** Needs polished schematic. Information is available from visit summary slides and SOP documents.

## Figure 2. BubbleID-Flow Vision Workflow

**Purpose:** Show how raw images become quantitative vapor metrics.

**Panel plan:**

- Raw ROI image.
- Mask R-CNN bubble mask.
- Overlay.
- Streamwise projected vapor area fraction profile.

**Available source:** Existing BubbleID-Flow outputs and `plot_vapor_fraction_profile.py`.

## Figure 3. Baseline Integrated Case: `15gs_20C`

**Purpose:** Demonstrate the complete image + thermal + acoustic analysis pipeline for one case.

**Current file:**

```text
outputs/multimodal/15gs_20C_baseline/15gs_20C_integrated_baseline_panel.png
```

**Panel contents:**

- Heat flux versus test-relative time.
- Projected vapor area fraction versus voltage state.
- Mean HTC and heat flux versus voltage state.
- AE hit rate and AE absolute-energy rate versus voltage state.

**Story:** Vapor coverage increases strongly above about `45 V`, coincident with increased thermal forcing and elevated AE activity.

## Figure 4. Representative Bubble Masks Across the `15gs_20C` Sweep

**Purpose:** Visually anchor the quantitative trend in Figure 3.

**Current file:**

```text
outputs/multimodal/15gs_20C_baseline/15gs_20C_representative_overlay_sheet.png
```

**Story:** The vapor-covered region grows downstream and occupies more of the near-wall band as voltage increases from onset toward CHF-adjacent states.

## Figure 5. Cross-Case Multimodal Signatures

**Purpose:** Show that the trend is not unique to one case.

**Current file:**

```text
outputs/multimodal/cross_case_synthesis/cross_case_multimodal_story.png
```

**Panel contents:**

- Projected vapor area fraction versus heat flux.
- AE absolute-energy rate versus projected vapor area fraction.
- Mean HTC versus projected vapor area fraction.
- Active vapor length fraction versus heat flux.

**Story:** Image-derived vapor coverage and active vapor length generally rise with heat flux across the four operating cases; AE energy broadly rises with vapor activity but exhibits case-specific scatter, which is physically reasonable because sensor coupling, event intermittency, and flow condition affect AE transfer.

## Figure 6. Normalized Multimodal State Map

**Purpose:** Provide a compact overview of all states and all modalities.

**Current file:**

```text
outputs/multimodal/cross_case_synthesis/cross_case_state_map.png
```

**Recommended placement:** Supplementary figure or late Results figure.

**Story:** High-voltage/CHF-adjacent states cluster as high heat-flux, high visual-vapor, and high thermal-response states, while AE energy highlights some but not all of the same transitions.

## Figure 7. Methodological Limitation and Validation Panel

**Purpose:** Make the paper defensible by showing segmentation strengths and failure modes.

**Panel plan:**

- Example accurate masks.
- Example merged bubbles.
- Example onset-state false positive.
- Manual annotation comparison for a held-out annotated frame.

**Status:** Needed before journal submission.

## Figure 8. Synchronization and Signal-Window Audit

**Purpose:** Strengthen the acoustic claims.

**Panel plan:**

- Thermal voltage/power trace with state windows.
- AE hit density or energy trace with same windows.
- Image-folder state labels aligned to voltage windows.

**Status:** Needed before making lead/lag claims.
