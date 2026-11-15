BubbleID-Flow manuscript Overleaf package
==========================================

Main file:
  main.tex

Separate editable submission files:
  highlights.tex
  cover_letter.tex
  references.bib
  supplementary.tex

Separate graphical abstract file:
  Graphical_Abstract.pdf

Figure files:
  Figure_1_facility_data_streams.png
  Figure_2_dataset_preparation_pipeline.png
  Figure_3_finetuning_architecture.png
  Figure_4_aug9_model_outputs.pdf
  Figure_5_segmentation_robustness.pdf
  Figure_6_segmentation_baselines.pdf
  Figure_5_aug9_optical_results.pdf
  Figure_7_optical_thermal_association.pdf

Supplementary figure file:
  Figure_8_timestamp_registered_multimodal_screening.pdf

Notes for Overleaf:
  1. Upload all files in this folder to one Overleaf project.
  2. Set main.tex as the main document. Compile supplementary.tex separately when submitting supplementary material.
  3. Use the Elsevier elsarticle class and numerical bibliography style.
  4. Compile with pdfLaTeX/BibTeX on Overleaf.

Journal-format note:
  This source currently uses the Elsevier elsarticle class retained from the
  prior Applied Thermal Engineering package. It is content-complete and
  independently compilable, but must be converted to the official ASME Journal
  of Heat and Mass Transfer template before ASME submission.

Items to verify before live submission:
  - Final author list, order, affiliations, corresponding author, and email.
  - Funding grant numbers and sponsor-role statement.
  - Competing-interest declaration from every author.
  - Public code repository URL and final data-availability wording.
  - Repo-tracked segmentation, temporal, thermal-audit, and association artifacts are current and visible to git.
  - Whether internal-holdout evaluation files should be supplementary files.
  - Experiment-held-out manual masks remain required; the current holdout is a same-sequence reconstruction test.
  - Run scripts\audit_ate_submission_package.py after text edits; it verifies the current evidence package and reports human-confirmation blockers.
  - Whether the submitted version should include the generative-AI disclosure exactly as written.
  - Figure permissions for any setup photographs extracted from the CWRU visit deck.
