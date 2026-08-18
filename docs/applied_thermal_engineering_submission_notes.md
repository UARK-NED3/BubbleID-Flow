# Applied Thermal Engineering Submission Notes

## Package Location

The Overleaf-ready source package is:

```text
overleaf_applied_thermal_engineering
```

The package is intentionally flat because Elsevier Editorial Manager does not
process LaTeX submissions containing subfolders.

## Current Figure Set

The Aug. 9 model figures and graphical abstract are generated with:

```powershell
python scripts\prepare_aug9_optical_results.py --help
```

The current outputs are written under:

```text
outputs\aug9_model_analysis
```

and copies the PDF files into:

```text
overleaf_applied_thermal_engineering
```

The package contains:

- `Figure_1_facility_data_streams.pdf`
- `Figure_2_dataset_preparation_pipeline.pdf`
- `Figure_3_finetuning_architecture.pdf`
- `Figure_4_aug9_model_outputs.pdf`
- `Figure_5_aug9_optical_results.pdf`
- `Figure_6_segmentation_baselines.pdf`
- `Figure_7_optical_thermal_association.pdf`
- `Graphical_Abstract.pdf`

## Reproducible Package Audit

Run the package audit before uploading to Editorial Manager:

```powershell
python scripts\audit_ate_submission_package.py
```

The audit writes:

```text
docs\ate_submission_package_audit.md
```

It checks Overleaf figure inclusion, abstract and highlight length, citation-key
consistency, required declaration sections, segmentation baselines,
same-sequence holdout evidence, moving-block temporal uncertainty, thermal-source
provenance, voltage/heat-flux confounding, cross-validated incremental optical
information, claim-scope wording, and synchronization between manuscript numbers
and generated CSV/JSON outputs. It also checks that the small evidence artifacts
are not hidden by git ignore rules.

## ATE Requirements Reflected In The Package

- `main.tex` uses the Elsevier `elsarticle` class with numerical citations.
- Abstract is under 250 words.
- Keywords list contains seven keywords.
- `highlights.tex` contains five highlights, each under 85 characters.
- The graphical abstract is provided as a separate file.
- Figures are separate files with logical names.
- Figure 7 reports complete 45 V frame sequences and a same-model state-mean
  reproduction comparison; Figure 8 reports the optical--thermal confounding and
  cross-validation test.
- The Mask R-CNN model weights are cited in `main.tex` through the OSF project,
  direct download URL, and SHA256 checksum recorded in
  `docs/model_artifact_manifest.csv`.
- The manuscript includes CRediT, funding, competing-interest, data-availability,
  and generative-AI disclosure sections.

## Items To Verify Before Live Submission

- Final author list, author order, affiliations, and corresponding-author email.
- Funding grant numbers and sponsor-role language.
- Conflict-of-interest declarations from every author.
- Public repository URL and final data-availability wording.
- Whether the internal-holdout COCO and combined-mask evaluation files should be
  archived as supplementary evidence.
- Figure permissions for photographs extracted from the CWRU visit deck.
- Acoustic data remain excluded unless trigger alignment and coupling are verified.
- Complete-sequence optical reruns are still needed for the 33 non-45 V states.
- Experiment-held-out masks remain necessary before claiming cross-case or
  cross-experiment segmentation generalization.
- Heat-transfer coefficient, quality, friction, and energy-balance results remain
  excluded until the reduction, calibration, heat loss, and uncertainty chain is
  independently reconstructed.
