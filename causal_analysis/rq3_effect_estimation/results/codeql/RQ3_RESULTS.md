# CodeQL: RQ3 results

## Analysis definition

- Dataset: `/Users/mkhan04/Desktop/projects/CauSec/ci4security/causal_analysis/data/codeql/alerts_with_lib_category_and_apk_size_codeql.csv`
- Treatment: `reporting_policy` (`0` = developer-only; `1` = developer plus third-party)
- Outcome: binary `verdict`; all reported effects are ATE risk differences
- Adjustment variables: `app_popularity_encoded`, `apk_size_scaled`
- Alert-level rows: 22,055
- Unique APKs: 488
- Bootstrap simulations per uncertainty method: 1000
- Refuter simulations where applicable: 200
- Causal graph: `/Users/mkhan04/Desktop/projects/CauSec/ci4security/causal_analysis/rq1_graph_assessment/graphs/codeql_causal_graph.svg`

Developer-written alerts are shared across both policy conditions, and
third-party alerts occur only in the inclusive condition, matching the legacy
binary-treatment construction.

## 1. Overlap and post-matching balance

The propensity model predicts reporting policy from app popularity and APK
size. Common support is the intersection of the observed propensity-score
ranges in the two policy conditions.

| Policy condition | Rows | Propensity range | Outside common support |
|---|---:|---:|---:|
| developer_only | 554 | 0.9667–0.9799 | 0 (0.00%) |
| developer_plus_third_party | 21,501 | 0.9651–0.9800 | 227 (1.06%) |

Nearest-neighbor PSM uses replacement, as in DoWhy's legacy-compatible ATE
implementation. It leaves no row formally unmatched. As a match-quality
diagnostic, 14 treated-to-control
pairs and 0 control-to-treated
pairs exceed a 0.2-SD logit-propensity caliper. These pairs are reported rather
than silently discarded.

| Covariate | SMD before | SMD after PSM | SMD after AIPW weighting |
|---|---:|---:|---:|
| `app_popularity_encoded` | 0.1348 | -0.0293 | 0.0034 |
| `apk_size_scaled` | 0.0125 | -0.0818 | 0.0042 |

Absolute SMD below 0.1 is used as a descriptive balance threshold. See
`balance.csv` for the absolute values and threshold flags. The AIPW column
diagnoses the inverse-propensity-weighted component of the doubly robust
estimator; it is not a separate effect estimate.

## 2. Effect estimates and uncertainty

All estimators target the same alert-row ATE on the risk-difference scale. The
logistic estimate is obtained by standardizing binomial-model predictions under
both policies. The doubly robust estimate uses the same binomial outcome model
and a logistic propensity model in an augmented inverse-probability-weighted
estimator.

| Estimator | ATE | Row-bootstrap 95% CI | APK-cluster-bootstrap 95% CI | Row width | Cluster width |
|---|---:|---:|---:|---:|---:|
| Propensity-score matching | -0.0573 | [-0.0955, -0.0234] | [-0.1098, -0.0295] | 0.0721 | 0.0803 |
| Logistic-regression adjustment | -0.0641 | [-0.0796, -0.0459] | [-0.0878, -0.0365] | 0.0337 | 0.0513 |
| Doubly robust (AIPW) | -0.0596 | [-0.0770, -0.0395] | [-0.0853, -0.0309] | 0.0376 | 0.0545 |

The row bootstrap resamples individual alert rows within popularity-policy
strata. The clustered bootstrap resamples complete APKs within popularity
strata and retains every selected APK's rows across both policy conditions.
1 APK has conflicting popularity values in the input. It is retained as one complete cluster in a disclosed composite stratum; see `apk_cluster_diagnostics.csv`.

## 3. Refutation and sensitivity checks

The four legacy checks are retained: random common cause, placebo treatment,
data subset, and dummy outcome. The `add_unobserved_common_cause` check is added
using direct simulation with 0.05 binary-flip strength on both treatment and
outcome. Its result is a sensitivity scenario, not proof that unmeasured
confounding is absent.

| Estimator | Refuter | New effect | p-value | Significant refuter change | Execution status |
|---|---|---:|---:|---:|---|
| Propensity-score matching | `random_common_cause` | -0.0573 | 1.0000 | False | success |
| Propensity-score matching | `placebo_treatment_refuter` | 0.0075 | 0.7800 | False | success |
| Propensity-score matching | `data_subset_refuter` | -0.0743 | 0.2200 | False | success |
| Propensity-score matching | `dummy_outcome_refuter` | -0.0165 | 0.9200 | False | success |
| Propensity-score matching | `add_unobserved_common_cause` | 0.6277 | NA | NA | success |
| Logistic-regression adjustment | `random_common_cause` | -0.0641 | 0.9000 | False | success |
| Logistic-regression adjustment | `placebo_treatment_refuter` | 0.0006 | 0.9100 | False | success |
| Logistic-regression adjustment | `data_subset_refuter` | -0.0643 | 0.9100 | False | success |
| Logistic-regression adjustment | `dummy_outcome_refuter` | -0.0052 | 0.8450 | False | success |
| Logistic-regression adjustment | `add_unobserved_common_cause` | 0.5047 | NA | NA | success |
| Doubly robust (AIPW) | `random_common_cause` | -0.0596 | 1.0000 | False | success |
| Doubly robust (AIPW) | `placebo_treatment_refuter` | 0.0003 | 0.9100 | False | success |
| Doubly robust (AIPW) | `data_subset_refuter` | -0.0593 | 0.8600 | False | success |
| Doubly robust (AIPW) | `dummy_outcome_refuter` | 0.0043 | 0.9600 | False | success |
| Doubly robust (AIPW) | `add_unobserved_common_cause` | 0.5133 | NA | NA | success |

Complete refuter diagnostics, including relative changes, sign changes, and
errors, are stored in `refuter_results.csv`.
`success` means that the refuter executed; it does not mean that the estimate
passed the refuter. The significant-change column records DoWhy's test result
where that refuter supplies one.

## Interpretation boundary

- PSM, regression, and doubly robust estimation use the same treatment,
  outcome, adjustment variables, target population, and risk-difference scale.
- Developer-alert duplication and multiple alerts per APK make row-independent
  intervals optimistic when within-APK dependence is material.
- The APK-cluster bootstrap addresses uncertainty from that dependence but does
  not change the alert-level estimand or repair structural treatment overlap.
- Refuters test sensitivity to specific perturbations; passing them does not
  establish that the causal assumptions are true.
- The report preserves the legacy reporting-policy operationalization. Results
  should be interpreted as the effect of changing the reported alert set, not
  as an intervention on the SAST engine's method-level analysis behavior.
