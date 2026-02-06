#!/usr/bin/env python3
"""Test CSV loading with proper parameters"""

import pandas as pd
import csv

# Test loading the filled CSV file
try:
    df = pd.read_csv('sample_project_data_filled.csv', sep=';', encoding='utf-8-sig', 
                     quoting=csv.QUOTE_MINIMAL, quotechar='"', doublequote=True)
    print(f"[OK] Successfully loaded {len(df)} rows, {len(df.columns)} columns")
    print(f"  Columns: {list(df.columns)}")
except Exception as e:
    print(f"[ERROR] Error loading: {e}")
    # Try with windows-1251 encoding
    try:
        df = pd.read_csv('sample_project_data_filled.csv', sep=';', encoding='windows-1251',
                        quoting=csv.QUOTE_MINIMAL, quotechar='"', doublequote=True)
        print(f"[OK] Successfully loaded with windows-1251: {len(df)} rows, {len(df.columns)} columns")
    except Exception as e2:
        print(f"[ERROR] Error with windows-1251: {e2}")

