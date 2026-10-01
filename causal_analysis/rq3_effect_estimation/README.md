# RQ3: effect estimation and robustness assessment

RQ3 asks:

> How can we estimate and assess the causal queries in this context?

The four primary restart-executable notebooks retain the legacy reporting-policy
operationalization: `0` reports developer-written alerts only and `1` reports
developer-written plus third-party alerts. Each notebook uses its tool's
canonical CSV, displays the corresponding RQ1 graph, adjusts for app popularity
and APK size, and writes an individual results report.

Four companion library-type notebooks reproduce the legacy pairwise reporting
policy for Android, Small Libraries, Utilities, and Miscellaneous: developer
alerts versus the same developer alerts plus every alert in the selected
third-party category. They perform no category downsampling and apply the same
current diagnostics, three estimators, clustered uncertainty, and refuters
separately to each category contrast.

## Notebooks

```text
codeql_rq3.ipynb
cognicrypt_rq3.ipynb
cryptoguard_rq3.ipynb
semgrep_rq3.ipynb

codeql_rq3_library_types.ipynb
cognicrypt_rq3_library_types.ipynb
cryptoguard_rq3_library_types.ipynb
semgrep_rq3_library_types.ipynb
```

The primary notebooks run `causal_analysis/shared/rq3_analysis.py`. The
library-type notebooks run `causal_analysis/shared/rq3_library_types.py`, which
delegates estimation and diagnostics to that same primary implementation.
Keeping the notebooks separate makes saved tool and category results
independently inspectable without copying the statistical implementation.

## Analysis components

1. Estimate propensity scores from `app_popularity_encoded` and
   `apk_size_scaled`.
2. Report common-support diagnostics and standardized mean differences before
   adjustment, after the actual nearest-neighbor ATE matching, and after ATE
   inverse-propensity weighting used inside AIPW.
3. Estimate the alert-row ATE as a risk difference using propensity-score
   matching, standardized binomial logistic regression, and doubly robust AIPW.
4. Compare percentile intervals from an alert-row bootstrap with intervals from
   a popularity-stratified APK-cluster bootstrap. The cluster bootstrap samples
   complete APKs and therefore keeps shared developer alerts in both policy
   conditions.
5. Run the four legacy refuters plus an unobserved-common-cause sensitivity
   scenario for every estimator.

The default run uses 1,000 bootstrap replicates and 200 simulations for refuters
that accept a simulation count. Seeds and package versions are recorded in each
tool's `run_metadata.json`.

## Run

From the repository root:

```bash
source venv/bin/activate
jupyter notebook causal_analysis/rq3_effect_estimation/codeql_rq3.ipynb
```

Choose **Restart Kernel and Run All Cells**. Repeat for the other three
primary notebooks. Run the matching `_rq3_library_types.ipynb` notebook for the
four category-specific contrasts. See `NAVIGATION.md` for the complete output
map.

## Interpretation boundary

The estimand is the alert-row precision difference induced by the constructed
reporting policy. It is not the effect of changing whether a SAST engine
analyzes third-party code. Balance diagnostics, multiple estimators,
bootstrapping, and refuters reveal particular weaknesses or sensitivities; they
do not prove that the causal graph or identifying assumptions are correct.
