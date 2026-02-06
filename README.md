## Paper Title: CauSec: Unboxing the Causal Drivers of Static Vulnerability Analysis Performance

### Ranges for the Stratified Sampling
We extracted APK based on the popularity (download count) and got a stratified sampling.<br>
below are the APK groups based on the download count.<br>
\<100
100 - 500
500 - 1k
1k - 5k
5k - 10k
10k - 50k
50k - 100k
100k - 500k
500k - 1M
1M - 5M
\> 5M

### How to Extract APKs from the AndroZoo
To download the APK from the AndroZoo, you must have both the API key and the SHA256 of the APK
- Get the API key from the authors.
- Write the plain API key in the file named `api_key.txt`
- To get the SHA256 of APKs, you have to download the [input file](https://androzoo.uni.lu/api_doc#:~:text=Obtaining%20SHA256%20Hashes). Consider downloading the input file with the `added` field. This input file also contains some other important fields like version code, markets from where the APK was detected.
<br>

These input files are containing multiple version of the same app. That is why, first we have selected and extracted the latest version of each app. We kept only unique APKs in the `input_file/filtered_unique_latest_with-added-date.csv`.
Then we shuffled this file for randomness and used that file (`input_file/shuffled_filtered_unique_latest_with-added-date.csv`) as an input in the `Extract_apk.py`. We only collected the APKs, which are also available in the Google Play Store on June 26th, 2025. After completing the download (output folder name: `downloaded_apk/` ).
<br>
Then to decompile the APK files, first you need to install the Jadx in the machine. Then run the `decompile_apk.py` file.
<br>
**Next step:** If we want to downlod more APKs, then we have make sure that we are downloading those APK, which are not already available.

### Dataset Creation
For example, to create alert dataset from the validated alerts of `CogniCrypt`:
Step 1 -  First run the `extract_final_dataset_from_json/extract_alert_data_cognicrypt.py` file to get the alert dataset
Step 2 - To identify the alert provenance, we used LibScout 3rd-party library dataset, as it is popular and widely used. Run the `library_classification/alert_classification.py` to get the alert provenance from the Libscout library dataset. use the outfile file of Step 1 as an input here.
Step 3 -  Then,  get the apk_size and metadata about the APK from the `input_files/dataset_apk_metadata.json`, run the script `extract_final_dataset_from_json/get_apk_size_for_alerts.py`. Use the output file of Step 2 as an input here. The output of this step is the final dataset for the CogniCrypt.

That means, keep all the metadata from AndroZoo in the `input_files/` folder.
<br>

We have the following files containing our manually labelled alert data:
- CryptoGuard Dataset: `causal_analysis_cryptoguard/alerts_with_category_and_apk_size_updated_cryptoguard.csv`
- CogniCrypt Dataset: `causal_analysis_cognicrypt/alerts_with_category_with_apk_size_updated.csv`

These datasets can then be used as an input in our causal analysis in `causal_analysis_cryptoguard` and `causal_analysis_cognicrypt` folders respectively.

Then we can run the following files for causal analysis of CryptoGuard:
- Run `causal_analysis_cryptoguard/causal_analysis_binary_treatment.ipynb` for EQ1 of CryptoGuard
- Then run the `causal_analysis_cryptoguard/causal_analysis_libraries.ipynb` for EQ2 of CryptoGuard.

In the same way, we can run the following files for causal analysis of CogniCrypt:
- Run `causal_analysis_cognicrypt/causal_analysis_binary_treatment.ipynb` for EQ1 of CogniCrypt
-  Then run the `causal_analysis_cognicrypt/causal_analysis_libraries.ipynb` for EQ2 of CogniCrypt



