import csv
from collections import defaultdict

csv_file = 'download_log.csv'

pkg_name_dict = defaultdict(list)

with open(csv_file, 'r', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        pkg_name_dict[row['pkg_name']].append(row)

for pkg_name, rows in pkg_name_dict.items():
    if len(rows) > 1:
        print(f"\nDuplicate pkg_name: {pkg_name}")
        for row in rows:
            print(row)
