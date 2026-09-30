# Semgrep: RQ3 library-type results

## Analysis definition

Each row compares developer-only reporting with reporting developer alerts plus
one grouped library type. The construction preserves the legacy grouping and
pairwise policy contrast while retaining every eligible source row. It
estimates alert-row ATE risk differences with PSM, standardized logistic
regression, and doubly robust AIPW.

| Library type | PSM ATE | Logistic ATE | Doubly robust AIPW ATE | Same direction? |
|---|---:|---:|---:|---|
| Android | 0.0942 | 0.1026 | 0.1014 | Yes |
| Small_Libraries | 0.0550 | 0.0363 | 0.0365 | Yes |
| Utilities | 0.0293 | 0.0454 | 0.0448 | Yes |
| miscellaneous | 0.0790 | 0.1032 | 0.1025 | Yes |

## Row inclusion

| Library type | Included developer alerts | Included library alerts | Control rows | Inclusive rows |
|---|---:|---:|---:|---|
| Android | 1,760 | 4,769 | 1,760 | 6,529 |
| Small_Libraries | 1,760 | 531 | 1,760 | 2,291 |
| Utilities | 1,760 | 1,743 | 1,760 | 3,503 |
| miscellaneous | 1,760 | 5,787 | 1,760 | 7,547 |

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
