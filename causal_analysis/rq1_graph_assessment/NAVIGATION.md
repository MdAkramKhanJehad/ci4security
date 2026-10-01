# Navigating the RQ1 analysis

## Start here

1. Open `rq1_analysis.ipynb` to inspect or rerun the complete workflow.
2. Read `RQ1_RESULTS.md` for the graph structure and association findings.
3. Open one of the four files under `graphs/` to view a tool-specific DAG.

## Inputs

```text
slr_directional_claims.csv  Extracted literature claims for paper interpretation
variables.csv               Variable construction and graph roles
configs/<tool>.json         Canonical input CSV for each tool
```

The canonical datasets are stored under:

```text
causal_analysis/data/codeql/
causal_analysis/data/cognicrypt/
causal_analysis/data/cryptoguard/
causal_analysis/data/semgrep/
```

## Code

`rq1_analysis.ipynb` is the only RQ1 entry point. It imports:

```text
causal_analysis/shared/data_loading.py       Reporting-policy transformation
causal_analysis/shared/association_tests.py  Correlations and FDR correction
causal_analysis/shared/graph_construction.py Fixed DAG and SVG rendering
```

`graph_construction.py` contains one common edge specification. It renders the
SVG directly from memory, so the workflow does not create intermediate graph
source files.

## Graphs

```text
graphs/causal_graph.svg
```

The shared graph has the domain-specified directions. Tool-specific Spearman
correlations and Benjamini-Hochberg-adjusted classifications are reported in
the results tables rather than printed on the graph.

## Results

Each `results/<tool>/` directory contains:

```text
association_checks.csv       Coefficients, p-values, BH q-values, interpretation
dataset_summary.json         Alert, provenance, and APK counts
reporting_policy_summary.csv Counts and raw precision for both policies
causal_graph.md              Tool-specific graph description and edge list
run_metadata.json            Input hash, graph structure, versions, and timestamp
```

The three `results/all_tools_*.csv` files combine the tool-level results.

## Non-interactive execution

Run from the repository root using the project virtual environment:

```bash
source venv/bin/activate
export JUPYTER_CONFIG_DIR=/tmp/causec-jupyter-config
export JUPYTER_DATA_DIR=/tmp/causec-jupyter-data
export JUPYTER_RUNTIME_DIR=/tmp/causec-jupyter-runtime
python -c 'import nbformat; from nbclient import NotebookClient; p="causal_analysis/rq1_graph_assessment/rq1_analysis.ipynb"; n=nbformat.read(p, as_version=4); NotebookClient(n, timeout=600, kernel_name="python3").execute(cwd="."); nbformat.write(n, p)'
```
