Applied Thermal Engineering Overleaf / Editorial Manager package
================================================================

Main file:
  main.tex

Separate editable submission files:
  highlights.tex
  cover_letter.tex
  references.bib

Separate graphical abstract file:
  Graphical_Abstract.pdf

Figure files:
  Figure_1_facility_data_streams.pdf
  Figure_2_dataset_preparation_pipeline.pdf
  Figure_3_finetuning_architecture.pdf
  Figure_4_aug9_model_outputs.pdf
  Figure_5_segmentation_robustness.pdf
  Figure_6_segmentation_baselines.pdf
  Figure_5_aug9_optical_results.pdf
  Figure_7_optical_thermal_association.pdf

Notes for Overleaf:
  1. Upload all files in this folder to one Overleaf project.
  2. Set main.tex as the main document.
  3. Use the Elsevier elsarticle class and numerical bibliography style.
  4. Compile with pdfLaTeX/BibTeX on Overleaf.

Notes for Elsevier Editorial Manager:
  1. Keep all files at this same folder level. EM does not process LaTeX subfolders.
  2. Upload main.tex, references.bib, highlights.tex, and any .bbl/.bst/.sty files as Manuscript items if requested.
  3. Upload each Figure_*.pdf and Graphical_Abstract.pdf as Figure/Graphical Abstract items.
  4. Do not upload duplicate figure basenames with different extensions.

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
