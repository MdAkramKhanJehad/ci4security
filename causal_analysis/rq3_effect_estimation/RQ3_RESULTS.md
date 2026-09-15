# RQ3 cross-tool results

## Scope

The analysis retains the legacy reporting-policy operationalization. The
treatment contrast is developer-only reporting (`0`) versus reporting
developer-written and third-party alerts (`1`). The outcome is the binary alert
verdict, so an ATE risk difference below zero means that the inclusive policy
has lower alert-level precision; a value above zero means higher precision.

All three estimators use the same alert-row target population, treatment,
outcome, adjustment variables (app popularity and APK size), and effect scale.
The saved runs use 1,000 bootstrap replicates and 200 simulations for refuters
that accept a simulation count.

## Main estimates

| Tool | PSM ATE | Logistic ATE | Doubly robust ATE | APK-cluster uncertainty conclusion |
|---|---:|---:|---:|---|
| CodeQL | -0.0573 | -0.0641 | -0.0596 | All three 95% intervals exclude zero below zero |
| CogniCrypt | -0.3101 | -0.2227 | -0.2383 | All three 95% intervals exclude zero below zero |
| CryptoGuard | 0.0426 | -0.0304 | -0.0229 | All three 95% intervals include zero |
| Semgrep | 0.1086 | 0.1224 | 0.1156 | PSM and AIPW exclude zero above zero; logistic includes zero narrowly |

Exact row-bootstrap and APK-cluster-bootstrap limits are in each tool's
`estimator_results.csv` and generated `RQ3_RESULTS.md`.

## Overlap and balance

Common-support exclusions were limited to the inclusive policy arm: 227 rows
for CodeQL (1.06% of that arm), 144 for CogniCrypt (2.54%), 30 for CryptoGuard
(0.20%), and 13 for Semgrep (0.09%). DoWhy's nearest-neighbor implementation
matches with replacement and applies no caliper, so no row is formally
unmatched. The separate 0.2-SD logit-propensity diagnostic flagged 14, 195,
118, and 0 treated-to-control pairs, respectively.

For every tool, the absolute SMD of both adjustment variables was below 0.1
after PSM and after the AIPW propensity weighting. These results indicate that
the fitted propensity model balances the two measured variables under the
implemented adjustments. They do not establish overlap for unmeasured
variables or validate the causal graph.

## APK-dependent uncertainty

The APK-cluster intervals were wider than the row-bootstrap intervals for every
tool and estimator. The substantive change is clearest for CryptoGuard, where
all clustered intervals include zero, and for Semgrep logistic adjustment,
whose row interval excludes zero but clustered interval barely includes it.
Thus, row-independent uncertainty would overstate support for some conclusions.

The cluster bootstrap resamples complete APKs within popularity strata and
retains all reporting-policy rows for a sampled APK. One CodeQL APK has two
conflicting popularity values in the input. It is kept intact in a disclosed
composite stratum; the point-estimation data are left unchanged for legacy
compatibility.

## Refuters and sensitivity

All five refuters completed for all three estimators and four tools. The random
common-cause, data-subset, and dummy-outcome checks did not report a significant
failure at 0.05 after the seeded data-subset simulation was made
non-degenerate. Placebo treatment also behaved as expected except for
CryptoGuard PSM (p = 0.02), which is additional evidence against relying on
that positive PSM estimate.

The added unobserved-common-cause scenario directly simulates a binary
confounder with 0.05 treatment and outcome flip strengths. Under this specific
scenario, all CodeQL estimates reverse sign and the CryptoGuard PSM estimate
reverses sign. CogniCrypt and Semgrep retain their directions, while their
magnitudes change. This scenario therefore exposes sensitivity; it is not
evidence that unobserved confounding is absent.

## Assessment of the proposed additions

The proposed additions are methodologically appropriate with four
qualifications:

- overlap and balance must be reported for the adjustment actually used; this
  implementation reports both the PSM matched sample and AIPW weighting;
- doubly robust means consistency can survive misspecification of one nuisance
  model under its assumptions, not that the estimate is automatically unbiased;
- whole-APK stratified resampling improves uncertainty accounting but does not
  repair identification or treatment construction;
- refuters assess specified perturbations and sensitivity scenarios, so the RQ
  and paper should say **assess** or **probe robustness**, not claim that they
  validate the causal effect.

Finally, these estimates concern a constructed reported-alert set. They cannot
establish the effect of changing a SAST engine so that it analyzes code it did
not previously analyze.
