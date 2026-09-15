# Navigating the RQ3 analysis

## Start here

1. Open the notebook named for the SAST tool.
2. Read `results/<tool>/RQ3_RESULTS.md` for its concise, generated report.
3. Open `results/<tool>/propensity_overlap.svg` for its overlap plot.
4. Use the CSV files for exact values and submission tables.

## Inputs

```text
../data/<tool>/alerts_with_lib_category_and_apk_size_<tool>.csv
../rq1_graph_assessment/graphs/<tool>_causal_graph.svg
```

The notebooks do not modify either input. Every result directory contains the
source CSV path, SHA-256 digest, random seed, and software versions in
`run_metadata.json`.

## Shared code

```text
../shared/data_loading.py  Reporting-policy table construction
../shared/rq3_analysis.py  Diagnostics, estimators, bootstrap, and refuters
```

## Per-tool outputs

```text
results/<tool>/RQ3_RESULTS.md          Human-readable tool report
results/<tool>/propensity_scores.csv   Row scores, support, PSM/AIPW weights
results/<tool>/overlap_summary.csv     Policy-group score ranges and support
results/<tool>/balance.csv             SMDs before and after adjustment
results/<tool>/matching_diagnostics.csv Match quality, caliper, and ESS data
results/<tool>/estimator_results.csv    ATEs and row/cluster intervals
results/<tool>/bootstrap_estimates.csv  Replicate-level estimates
results/<tool>/refuter_results.csv      All refuter results and failures
results/<tool>/software_validation.csv  DoWhy versus independent calculations
results/<tool>/apk_cluster_diagnostics.csv APK strata and input inconsistencies
results/<tool>/propensity_overlap.svg   Tool-specific overlap visualization
results/<tool>/dataset_summary.json     Alert and APK counts
results/<tool>/run_metadata.json        Provenance and reproducibility metadata
```

## Reading the uncertainty columns

`row_*` columns treat sampled alert rows as independent within the specified
strata. `cluster_*` columns resample entire APKs within popularity strata and
retain all of an APK's policy-expanded rows. The contrast in interval width
shows the consequence of accounting for APK-level dependence.
