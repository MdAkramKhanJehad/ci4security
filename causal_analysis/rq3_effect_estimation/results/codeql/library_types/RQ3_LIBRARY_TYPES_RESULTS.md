# CodeQL: RQ3 library-type results

## Analysis definition

Each row compares developer-only reporting with reporting developer alerts plus
one grouped library type. The construction preserves the legacy grouping and
pairwise policy contrast while retaining every eligible source row. It
estimates alert-row ATE risk differences with PSM, standardized logistic
regression, and doubly robust AIPW.

| Library type | PSM ATE | Logistic ATE | Doubly robust AIPW ATE | Same direction? |
|---|---:|---:|---:|---|
| Android | -0.0141 | -0.0214 | -0.0149 | Yes |
| Small_Libraries | -0.0060 | 0.0046 | 0.0053 | No / mixed |
| Utilities | -0.0426 | -0.0473 | -0.0485 | Yes |
| miscellaneous | -0.1319 | -0.1345 | -0.1297 | Yes |

## Row inclusion

| Library type | Included developer alerts | Included library alerts | Control rows | Inclusive rows |
|---|---:|---:|---:|---|
| Android | 554 | 9,345 | 554 | 9,899 |
| Small_Libraries | 554 | 713 | 554 | 1,267 |
| Utilities | 554 | 4,522 | 554 | 5,076 |
| miscellaneous | 554 | 6,367 | 554 | 6,921 |

For every contrast, the inclusive policy contains the developer alerts and the
selected library alerts, while the control policy repeats the developer alerts.
No eligible source alert is sampled out, and no source alert is duplicated by
resampling.

## Diagnostics and robustness outputs

The aggregate CSV files in this directory contain propensity overlap, balance,
matching diagnostics, row and APK-cluster bootstrap intervals, all bootstrap
replicates, software validation, and five refuters for every estimator and
library contrast. The four SVG files show propensity overlap separately for
each contrast.

These are all-row alert-set reporting contrasts. They do not estimate the
effect of modifying the SAST engine to analyze a different set of code.
