# CauSec: Causal Analysis of SAST Assumptions

This repository contains the data-processing scripts, manually validated alert
datasets, and causal-analysis notebooks used for the paper:

**CauSec: Unboxing the Causal Drivers of Static Vulnerability Analysis Performance**

The project studies whether assumptions made by static application security testing (SAST) tools hold under causal analysis.

## Repository Layout

```text
Assumptions/                         Extracted security assumptions from SAST papers
causal_analysis_codeql/              CodeQL causal-analysis datasets and notebooks
causal_analysis_semgrep/             Semgrep causal-analysis datasets and notebooks
causal_analysis_cognicrypt/          CogniCrypt causal-analysis datasets and notebooks
causal_analysis_cryptoguard/         CryptoGuard causal-analysis datasets and notebooks
codeql/                              CodeQL execution, preprocessing, and labeled outputs
semgrep/                             Semgrep execution, preprocessing, and labeled outputs
cognicrypt-CryptoAnalysis/           CogniCrypt reports and preprocessing scripts
cryptoguard/                         CryptoGuard reports and preprocessing scripts
library_classification/              LibScout profiles and library-classification support
utils/                               Shared utilities for classification, precision, and tests
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
causal_analysis_codeql/alerts_with_lib_category_and_apk_size_codeql.csv
causal_analysis_semgrep/alerts_with_lib_category_and_apk_size_semgrep.csv
causal_analysis_cognicrypt/alerts_with_lib_category_and_apk_size_cognicrypt.csv
causal_analysis_cryptoguard/alerts_with_lib_category_and_apk_size_cryptoguard.csv
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

## Causal Analysis

Each tool has two main causal-analysis notebooks:

```text
causal_analysis_<tool>/causal_analysis_binary_treatment.ipynb
causal_analysis_<tool>/causal_analysis_library_types.ipynb
```

The binary-treatment notebooks answer:

> Does reporting alerts from third-party libraries along with developer-written
> alerts have a causal effect on precision?

The library-type notebooks answer:

> Do different types of third-party libraries have different causal impacts on
> precision?

The main causal graph adjusts for:

- APK size;
- app popularity.

The notebooks estimate effects with propensity score matching (PSM) and run
refutation tests, including random common cause, placebo treatment, data subset,
and dummy outcome refuters.

## Alternative Estimator Checks

To check whether the main PSM results are estimator-sensitive, the repository
also includes logistic-regression adjustment notebooks:

```text
causal_analysis_<tool>/causal_analysis_binary_treatment_logistic_regression_adjustment.ipynb
causal_analysis_<tool>/causal_analysis_library_types_logistic_regression_adjustment.ipynb
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


## Notes For Reproduction

- The notebooks assume that the final causal-analysis CSVs already exist.
- Some raw reports files may be large and are not always 
  available in a fresh clone. (will be available upon needed)
- If regenerating CSVs, run extraction before alert classification.
