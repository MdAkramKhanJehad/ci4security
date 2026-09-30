# RQ1 results: domain-specified causal graphs and empirical association evidence

## Research question

> How can evidence from SAST literature and empirical constraints be used to
> formulate and assess causal graphs for SAST design assumptions?

RQ1 combines two forms of evidence. The SLR and general SAST domain knowledge
specify the variables and edge directions. Tool-specific association analyses
then show whether the corresponding marginal relationships are visible in each
dataset. Association evidence supplements the domain model; it does not by
itself establish causal direction.

## Analysis scope and variable operationalization

The analysis is performed separately for CodeQL, CogniCrypt, CryptoGuard, and
Semgrep. The same variable definitions and graph-construction procedure are
used for all four tools.

| Role | Variable | Operationalization |
|---|---|---|
| Treatment | `reporting_policy` | `0`: report developer-written alerts only; `1`: report developer-written and third-party alerts |
| Confounder/context variable | `app_popularity_encoded` | Ordinal encoding of the 11 APK popularity categories |
| Confounder/context variable | `apk_size_scaled` | Robust-scaled APK size |
| Alert provenance | `reported_alert_is_third_party` | `0`: developer-written alert; `1`: third-party alert |
| Outcome | `verdict` | `1`: true positive; `0`: false positive; its mean is precision |

The reporting-policy construction follows the legacy binary experiment. Every
developer-written alert appears in both policy conditions, whereas a
third-party alert appears only under the inclusive policy. RQ1 evaluates the
resulting graph structure and associations. APK-level estimands, adjustment,
and uncertainty are deferred to RQ3.

## Graph-construction procedure

The procedure was applied identically to every tool:

1. Load and validate the tool's canonical alert CSV.
2. Construct the two reporting-policy conditions.
3. Encode popularity, robust-scale APK size, and derive binary alert provenance.
4. Run two-sided Spearman association tests for the numeric and binary
   variables.
5. Run a chi-square test and calculate Cramer's V for rule ID and verdict.
6. Apply Benjamini-Hochberg correction across the 11 tests within each tool.
7. Classify an association as detected when the adjusted value is (q < 0.06).
8. Render the common domain-specified DAG and report the tool-specific
   association evidence separately in the results tables.

The significance threshold affects only the empirical annotation. It does not
orient an edge. Edges in the current graphs are retained when their association
is not detected because the displayed structure is domain-specified; those
cases are reported explicitly below.

## Common domain-specified graph

All four tool graphs contain the following directed edges:

```text
app_popularity_encoded -> apk_size_scaled
app_popularity_encoded -> reported_alert_is_third_party
app_popularity_encoded -> verdict
apk_size_scaled -> reported_alert_is_third_party
apk_size_scaled -> verdict
reporting_policy -> reported_alert_is_third_party
reporting_policy -> verdict
reported_alert_is_third_party -> verdict
```

This structure expresses the study assumptions that app popularity and APK size
can affect alert provenance and correctness, that reporting policy determines
which provenance categories appear in the reported alert set, and that
provenance can affect precision. The direct `reporting_policy -> verdict` edge
represents the reporting-policy causal query. The directions are domain
assumptions and are not learned from the correlations.

## Dataset summary

| Tool | Original alerts | Policy-expanded rows | Developer alerts | Third-party alerts | APKs |
|---|---:|---:|---:|---:|---:|
| CodeQL | 21,501 | 22,055 | 554 | 20,947 | 488 |
| CogniCrypt | 5,675 | 6,173 | 498 | 5,177 | 324 |
| CryptoGuard | 15,272 | 16,590 | 1,318 | 13,954 | 354 |
| Semgrep | 14,590 | 16,350 | 1,760 | 12,830 | 535 |

The difference between original alerts and policy-expanded rows is the number
of developer-written alerts repeated in the developer-only condition.

## Association results

Table cells report Spearman's rho followed by the BH-adjusted q-value. `A`
means associated at (q < 0.06), and `ND` means that an association was not
detected at that threshold.

| Variable pair | CodeQL | CogniCrypt | CryptoGuard | Semgrep |
|---|---:|---:|---:|---:|
| Popularity / APK size | 0.433; <0.001 A | 0.277; <0.001 A | 0.200; <0.001 A | 0.388; <0.001 A |
| Popularity / reporting policy | 0.021; 0.002 A | 0.051; <0.001 A | 0.031; <0.001 A | 0.114; <0.001 A |
| Popularity / verdict | 0.050; <0.001 A | 0.076; <0.001 A | 0.060; <0.001 A | 0.015; 0.052 A |
| APK size / reporting policy | 0.007; 0.326 ND | 0.051; <0.001 A | 0.065; <0.001 A | 0.013; 0.092 ND |
| APK size / verdict | -0.031; <0.001 A | -0.012; 0.348 ND | -0.089; <0.001 A | -0.021; 0.010 A |
| Reporting policy / verdict | -0.031; <0.001 A | -0.118; <0.001 A | -0.017; 0.030 A | 0.082; <0.001 A |
| Reporting policy / provenance | 0.698; <0.001 A | 0.675; <0.001 A | 0.676; <0.001 A | 0.663; <0.001 A |
| Popularity / provenance | 0.030; <0.001 A | 0.075; <0.001 A | 0.046; <0.001 A | 0.171; <0.001 A |
| APK size / provenance | 0.009; 0.175 ND | 0.076; <0.001 A | 0.096; <0.001 A | 0.020; 0.013 A |
| Provenance / verdict | -0.045; <0.001 A | -0.174; <0.001 A | -0.025; 0.001 A | 0.123; <0.001 A |

Exact coefficients, unadjusted p-values, adjusted q-values, sample sizes, and
classifications are available in
`results/all_tools_association_checks.csv`.

### Evidence for graph edges

- CodeQL had detected associations for seven of the eight displayed edges. The
  APK-size/provenance relationship was not detected (rho = 0.009, q = 0.175).
- CogniCrypt had detected associations for seven of the eight displayed edges.
  The APK-size/verdict relationship was not detected (rho = -0.012, q = 0.348).
- CryptoGuard had detected associations for all eight displayed edges.
- Semgrep had detected associations for all eight displayed edges at the
  specified 0.06 threshold.

The policy/provenance association was the strongest common relationship across
the four graphs (rho = 0.663 to 0.698). This is expected from the reporting-policy
construction: third-party alerts occur only in the inclusive condition. It
should therefore be interpreted as confirmation of the operationalization, not
as independent evidence that the causal model is correct.

Most popularity- and APK-size-related coefficients were small even when their
q-values were below the threshold. Statistical detection should consequently
be distinguished from substantive effect magnitude.

### Rule ID and verdict

Rule ID was associated with verdict for all four tools according to the
chi-square tests. The corresponding Cramer's V values were:

| Tool | Cramer's V | BH-adjusted q-value |
|---|---:|---:|
| CodeQL | 0.708 | <0.001 |
| CogniCrypt | 0.580 | <0.001 |
| CryptoGuard | 0.909 | <0.001 |
| Semgrep | 0.974 | <0.001 |

These results indicate strong differences in verdict distributions among rules.
Rule ID is reported as an effect-modification candidate rather than included in
the current RQ1 graph.

## Descriptive reporting-policy results

| Tool | Developer-only precision | Developer + third-party precision | Raw difference |
|---|---:|---:|---:|
| CodeQL | 0.9513 | 0.8887 | -0.0626 |
| CogniCrypt | 0.7008 | 0.4846 | -0.2162 |
| CryptoGuard | 0.5129 | 0.4817 | -0.0312 |
| Semgrep | 0.5494 | 0.6743 | +0.1249 |

The inclusive policy had lower raw precision for CodeQL, CogniCrypt, and
CryptoGuard and higher raw precision for Semgrep. These values are descriptive
differences between the constructed reporting conditions, not adjusted causal
effect estimates.

## Generated causal graph

- [Causal graph](graphs/causal_graph.svg)

The shared graph contains the common nodes and directions. Tool-specific
coefficients and classifications remain in the association
tables so that the diagrams show only the causal assumptions.

## Interpretation boundaries

- The association tests are marginal and symmetric; they cannot determine
  causal direction.
- A detected association does not prove that an edge is causal.
- Failure to detect an association does not prove that the corresponding causal
  edge is absent.
- The policy-expanded data repeat developer-written alerts and contain multiple
  alerts from each APK. The RQ1 p-values do not account for this APK-level
  dependence.
- The large numbers of alert rows can make very small correlations statistically
  detectable.
- The graph structure should be described as domain-specified and empirically
  annotated, not as uniquely identified from the data.
- APK-level comparison, overlap assessment, causal-effect estimation, and
  clustered uncertainty are reserved for RQ3.

## RQ1 answer

Evidence from the SAST literature and general domain knowledge can be used to
specify a common causal structure for the reporting-policy assumption, while
tool-specific association analyses characterize how strongly the proposed
relationships appear in each dataset. The four tools showed consistent strong
associations between reporting policy and reported provenance, but the
relationships involving app characteristics were generally smaller and varied
by tool. The resulting graphs therefore provide transparent, comparable causal
assumptions annotated with empirical evidence rather than data-derived proof of
the causal structure.
