# CauSec: Unboxing the Causal Drivers of SAST Performance

This repository contains the data-processing scripts, manually validated alert
datasets, and causal-analysis notebooks used for the paper:

**CauSec: Unboxing the Causal Drivers of SAST Performance**


## Repository Layout

```text
Assumptions/                              Extracted security assumptions from SAST papers
Results_table/                            Paper result-table images
causal_analysis/
  README.md                               Causal-analysis overview and entry points
  data/<tool>/                            Canonical labeled datasets for the four tools
  legacy/<tool>/                          Original causal-analysis notebooks and artifacts
  rq1_graph_assessment/
    configs/                              Tool-specific graph-workflow configurations
    graphs/                               Domain-specified causal graph
    results/                              Saved association checks and graph summaries
    rq1_analysis.ipynb                    Restart-executable cross-tool RQ1 workflow
  rq3_effect_estimation/
    <tool>_rq3.ipynb                     Overall reporting-policy analyses
    <tool>_rq3_library_types.ipynb       Library-type subgroup analyses
    results/<tool>/                       Saved estimates, diagnostics, and refuters
  shared/                                 Shared loading, graph, and estimation modules
codeql/                                   CodeQL execution, preprocessing, and outputs
cognicrypt-CryptoAnalysis/                CogniCrypt reports and preprocessing scripts
cryptoguard/                              CryptoGuard reports and preprocessing scripts
semgrep/                                  Semgrep execution, preprocessing, and outputs
input_files/                              APK sampling and metadata inputs
library_classification/                   LibScout profiles and classification support
rule_based_analysis_codeql/               Supporting CodeQL rule-based analysis artifacts
utils/                                    Shared preprocessing and analysis utilities
```

## SLR Search Query

We used the following search query for finding our initial list of papers in identified sources for our systematic literature review:
```text 
("static analysis" OR "SAST" OR "static application security testing") AND ("taint analysis" OR "taint tracking" OR "data leak detection" OR "crypto API misuse" OR "cryptographic API misuse" OR "API misuse" OR "vulnerability detection")
```


## Dataset Sampling

The Android apps are stratified by Google Play install-count buckets:

```text
<100
100-500
500-1k
1k-5k
5k-10k
10k-50k
50k-100k
100k-500k
500k-1M
1M-5M
>5M
```

The input metadata from AndroZoo is kept under `input_files/`. The original
workflow selected the latest version of each app, shuffled the resulting APK
list for randomness, and downloaded APKs that were still available in Google
Play at collection time.

To download APKs from AndroZoo, you need:

- an AndroZoo API key in `api_key.txt`;
- an input CSV containing APK SHA-256 hashes and metadata;
- local storage for downloaded APKs and decompiled source files.

The decompilation workflow expects `jadx` to be installed locally.

## Manually Validated Alert Datasets

The final causal-analysis CSVs are:

```text
causal_analysis/data/codeql/alerts_with_lib_category_and_apk_size_codeql.csv
causal_analysis/data/semgrep/alerts_with_lib_category_and_apk_size_semgrep.csv
causal_analysis/data/cognicrypt/alerts_with_lib_category_and_apk_size_cognicrypt.csv
causal_analysis/data/cryptoguard/alerts_with_lib_category_and_apk_size_cryptoguard.csv
```

Each CSV contains manually validated alerts with fields used by the causal
analysis, including:

- `verdict`: alert label, where `1` is true positive and `0` is false positive;
- `code_location`: developer-written code or library category;
- `apk_size`;
- `app_popularity` / encoded popularity bucket;
- `ruleId` or rule identifier, where available.

## Preprocessing Pipeline

Each tool has a preprocessing folder with two main scripts:

```text
<tool>/data_preprocessing_for_causal_analysis/
  extract_alerts_from_json_and_apk_size_from_input_file.py
  alert_classification_for_causal_analysis.py
```

The first script extracts manually validated alerts from the tool-specific JSON
reports and attaches APK metadata. The second script classifies alert provenance
and library category using the shared classifier in:

```text
utils/shared_classifier_alert_util.py
```

Example for CodeQL:

```bash
python3 codeql/data_preprocessing_for_causal_analysis/extract_alerts_from_json_and_apk_size_from_input_file.py
python3 codeql/data_preprocessing_for_causal_analysis/alert_classification_for_causal_analysis.py
```

The same pattern applies to `semgrep`, `cryptoguard`, and
`cognicrypt-CryptoAnalysis`.


## Alternative Estimator Checks

To check whether the main PSM results are estimator-sensitive, the repository
also includes logistic-regression adjustment notebooks:

```text
causal_analysis/legacy/<tool>/causal_analysis_binary_treatment_logistic_regression_adjustment.ipynb
causal_analysis/legacy/<tool>/causal_analysis_library_types_logistic_regression_adjustment.ipynb
```

These notebooks use the same treatment, outcome, and adjustment variables as the
main PSM analyses, but estimate the effect with a model-based adjustment
strategy.

## Utility Scripts

Useful utility scripts include:

```text
utils/raw_precision_calculator.py          Raw and balanced precision summaries
utils/power_analysis_binary_treatment.py   Power analysis for causal variables
utils/statistical_tests.py                 Statistical tests used in analysis
utils/shared_classifier_alert_util.py      Shared alert provenance/library classifier
```

For example, raw precision baselines can be regenerated with:

```bash
python3 utils/raw_precision_calculator.py
```

## RQ1 Graph Assessment

RQ1 uses one parameterized, restart-executable workflow for all four tools. It
runs tool-specific association checks and generates four causal graphs using a
common domain-specified structure:

```bash
source venv/bin/activate
jupyter notebook causal_analysis/rq1_graph_assessment/rq1_analysis.ipynb
```

See `causal_analysis/rq1_graph_assessment/README.md` for interpretation and
limitations.

## RQ3 Estimation and Assessment

RQ3 retains the legacy developer-only versus developer-plus-third-party
reporting-policy comparison and runs three estimators on the same alert-row ATE
risk-difference scale: propensity-score matching, standardized binomial
logistic regression, and doubly robust AIPW. It also reports propensity overlap,
post-adjustment balance, alert-row versus APK-cluster bootstrap intervals, and
the four legacy refuters plus an unobserved-common-cause sensitivity scenario.

There is one restart-executable notebook per tool:

```text
causal_analysis/rq3_effect_estimation/codeql_rq3.ipynb
causal_analysis/rq3_effect_estimation/cognicrypt_rq3.ipynb
causal_analysis/rq3_effect_estimation/cryptoguard_rq3.ipynb
causal_analysis/rq3_effect_estimation/semgrep_rq3.ipynb
```

See `causal_analysis/rq3_effect_estimation/README.md` for methods and
`NAVIGATION.md` in the same directory for the output map.

If the local environment is missing or stale, rebuild it from the pinned
dependencies before running analyses:

```bash
uv venv venv --python 3.12 --clear
uv pip install --python venv/bin/python -r requirements.txt
```


## Notes For Reproduction

- The notebooks assume that the final causal-analysis CSVs already exist.
- Some raw reports files may be large and are not always 
  available in a fresh clone. (will be available upon needed)
- If regenerating CSVs, run extraction before alert classification.
