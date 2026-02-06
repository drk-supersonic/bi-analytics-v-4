#!/usr/bin/env python3
"""Fix CSV formatting to properly quote fields with commas and special characters"""

import pandas as pd
import csv
from pathlib import Path

def fix_csv_formatting(input_file, output_file):
    """Read CSV and save with proper formatting"""
    # Read the CSV file
    encodings = ['utf-8-sig', 'windows-1251', 'utf-8', 'cp1251']
    df = None
    
    for encoding in encodings:
        try:
            df = pd.read_csv(input_file, sep=';', encoding=encoding)
            print(f"Read file with encoding: {encoding}")
            break
        except Exception as e:
            continue
    
    if df is None:
        print("Error: Could not read file")
        return
    
    print(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    
    # Save with proper CSV formatting
    # Quote fields that contain commas to avoid parsing issues when opened in Excel or other tools
    # that might auto-detect comma as delimiter
    def should_quote_field(val):
        if pd.isna(val):
            return False
        val_str = str(val)
        return ',' in val_str or '"' in val_str or '\n' in val_str or '\r' in val_str
    
    # Custom quoting function
    class CustomQuoting:
        def __init__(self):
            pass
    
    # Use QUOTE_NONNUMERIC to quote all non-numeric fields, or QUOTE_MINIMAL with custom logic
    # Actually, let's use QUOTE_NONNUMERIC which will quote all text fields
    df.to_csv(output_file, sep=';', index=False, encoding='utf-8-sig', 
              quoting=csv.QUOTE_NONNUMERIC, quotechar='"', doublequote=True)
    
    print(f"Saved fixed CSV to: {output_file}")
    
    # Verify the file can be read back correctly
    try:
        df_check = pd.read_csv(output_file, sep=';', encoding='utf-8-sig')
        print(f"Verification: Successfully read back {len(df_check)} rows")
        
        # Check for any lines with wrong field count
        with open(output_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f, delimiter=';')
            rows = list(reader)
            header_count = len(rows[0])
            problematic = [i+1 for i, row in enumerate(rows[1:], 1) if len(row) != header_count]
            if problematic:
                print(f"Warning: Lines with incorrect field count: {problematic}")
            else:
                print("All lines have correct field count")
    except Exception as e:
        print(f"Warning: Could not verify file: {e}")

if __name__ == "__main__":
    input_file = Path("sample_project_data_filled.csv")
    output_file = Path("sample_project_data_fixed.csv")
    
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
    else:
        fix_csv_formatting(input_file, output_file)

