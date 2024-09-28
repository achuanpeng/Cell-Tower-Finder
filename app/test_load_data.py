# test_load_data.py

import pandas as pd

file_path = r'c:\Users\alpen\Downloads\Cell Tower Finder\New New\GPS_Cell_Coverage_Small\databases\towers\UZB.csv.gz'

try:
    df = pd.read_csv(file_path, compression='gzip')
    print(f"Successfully loaded {len(df)} rows.")
    print(df.head())
except Exception as e:
    print(f"Error loading file: {e}")
