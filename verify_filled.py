#!/usr/bin/env python3
"""Quick verification script for filled CSV"""

import pandas as pd
import sys

file_path = sys.argv[1] if len(sys.argv) > 1 else "sample_project_data_filled.csv"

df = pd.read_csv(file_path, sep=';', encoding='windows-1251')

print(f"Total rows: {len(df)}")
print("\nGaps remaining:")
date_cols = ['base start', 'base end', 'plan start', 'plan end']
for col in date_cols + ['reason of deviation', 'task name']:
    if col in df.columns:
        empty_count = (df[col].isna() | (df[col] == '')).sum()
        print(f"  {col}: {empty_count}")

print("\nSample of filled data (first 10 rows):")
print(df[['task name', 'reason of deviation', 'plan start', 'plan end']].head(10).to_string())

