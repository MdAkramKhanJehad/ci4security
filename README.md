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
For example, to create alert dataset from the validated alerts:
- After validating te alerts manually
- First run the `extract_final_dataset_from_json/extract_alert_data_cognicrypt.py` file to get the alert related data
- then get the apk_size etc. metadata about the apk from the `input_files/dataset_apk_metadata.json`
- then run the **** file to match and classify the alerts based on their code location

