# cognicrypt: RQ1 causal graph

Status: **domain-specified DAG with tool-specific empirical association checks**.

The graph uses `reporting_policy` as the treatment, alert verdict as the outcome, and app popularity and APK size as domain-specified confounders affecting reported alert provenance and verdict. Association results describe empirical compatibility but do not determine arrow direction.

## Edges

- `app_popularity_encoded -> apk_size_scaled`
- `app_popularity_encoded -> reported_alert_is_third_party`
- `app_popularity_encoded -> verdict`
- `apk_size_scaled -> reported_alert_is_third_party`
- `apk_size_scaled -> verdict`
- `reporting_policy -> reported_alert_is_third_party`
- `reporting_policy -> verdict`
- `reported_alert_is_third_party -> verdict`

The tool's Spearman correlations and Benjamini-Hochberg-adjusted significance results are stored separately in `association_checks.csv`. APK-level comparisons and causal-effect estimation are deferred to RQ3.
