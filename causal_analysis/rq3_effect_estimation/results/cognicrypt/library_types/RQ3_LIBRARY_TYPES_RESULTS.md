# CogniCrypt: RQ3 library-type results

## Analysis definition

Each row compares developer-only reporting with reporting developer alerts plus
one grouped library type. The construction preserves the legacy grouping and
pairwise policy contrast while retaining every eligible source row. It
estimates alert-row ATE risk differences with PSM, standardized logistic
regression, and doubly robust AIPW.

| Library type | PSM ATE | Logistic ATE | Doubly robust AIPW ATE | Same direction? |
|---|---:|---:|---:|---|
| Android | -0.0485 | 0.0304 | 0.0296 | No / mixed |
| Small_Libraries | -0.0307 | 0.0666 | 0.0669 | No / mixed |
| Utilities | -0.3753 | -0.3382 | -0.3453 | Yes |
| miscellaneous | -0.1119 | -0.0868 | -0.1048 | Yes |

## Row inclusion

| Library type | Included developer alerts | Included library alerts | Control rows | Inclusive rows |
|---|---:|---:|---:|---|
| Android | 498 | 530 | 498 | 1,028 |
| Small_Libraries | 498 | 208 | 498 | 706 |
| Utilities | 498 | 3,049 | 498 | 3,547 |
| miscellaneous | 498 | 1,390 | 498 | 1,888 |

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
