# Causal analysis

```text
data/                 Canonical manually validated CSV inputs, separated by tool
legacy/               Original notebooks and saved outputs retained for provenance
rq1_graph_assessment/ Restart-executable RQ1 pipeline and per-tool results
rq3_effect_estimation/ Primary and library-type RQ3 notebooks and results
shared/               Reusable loading, association, and graph code
```

The CSV links inside each `legacy/<tool>/` directory point to the canonical file
under `data/<tool>/`, allowing the moved notebooks to keep their original local
filename. New analyses should import the shared modules rather than copy cells
from the legacy notebooks.

For RQ3, start with `rq3_effect_estimation/README.md`. Its primary and
library-type tool notebooks retain the reporting-policy constructions and add
overlap/balance diagnostics, doubly robust estimation, APK-clustered
uncertainty, and the unobserved-common-cause sensitivity check.
