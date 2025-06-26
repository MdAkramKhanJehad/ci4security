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

These input files are containing multiple version of the same app. That is why, first we have selected and extracted the latest version of each app 

