#!/usr/bin/env python3
"""
Script to fill gaps in CSV file:
1. Fill gaps with dates
2. Fill gaps with reasons of deviation
3. Fill gaps with task names from Excel file
"""

import pandas as pd
import sys
import csv
from pathlib import Path
from datetime import datetime, timedelta

# List of deviation reasons
DEVIATION_REASONS = [
    "Нет РД",
    "Не передан фронт работ",
    "Недостаточно трудоресурсов",
    "Ошибки в ВД",
    "Нет оплаты подрядчику"
]

def read_excel_tasks(excel_path):
    """Read task names from Excel file"""
    try:
        # Read all sheets
        excel_file = pd.ExcelFile(excel_path)
        all_tasks = []
        
        print(f"Found sheets: {excel_file.sheet_names}")
        
        # Read each sheet and collect task names
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
            print(f"\nSheet '{sheet_name}' columns: {df.columns.tolist()}")
            
            # Try to find task name column (common variations)
            task_columns = [col for col in df.columns if any(keyword in str(col).lower() 
                          for keyword in ['task', 'задача', 'название', 'name', 'описание'])]
            
            if task_columns:
                tasks = df[task_columns[0]].dropna().unique().tolist()
                all_tasks.extend([str(t).strip() for t in tasks if str(t).strip()])
                print(f"Found {len(tasks)} tasks in column '{task_columns[0]}'")
            else:
                # If no obvious task column, show first few rows to help identify
                print(f"First few rows of sheet '{sheet_name}':")
                print(df.head())
        
        return list(set(all_tasks))  # Remove duplicates
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return []

def fill_dates(df):
    """Fill gaps in date columns using forward fill and backward fill"""
    date_columns = ['base start', 'base end', 'plan start', 'plan end']
    
    for col in date_columns:
        if col in df.columns:
            # Convert to datetime if not already
            df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
            
            # Forward fill within groups (by project/section)
            if 'project name' in df.columns:
                df[col] = df.groupby('project name')[col].ffill()
            else:
                df[col] = df[col].ffill()
            
            # Backward fill within groups
            if 'project name' in df.columns:
                df[col] = df.groupby('project name')[col].bfill()
            else:
                df[col] = df[col].bfill()
            
            # For remaining gaps, try to infer from other date columns
            if col == 'plan start' and 'plan end' in df.columns:
                # If plan start is missing but plan end exists, estimate start (e.g., 10 days before)
                plan_end_dt = pd.to_datetime(df['plan end'], errors='coerce', dayfirst=True)
                mask = df[col].isna() & plan_end_dt.notna()
                if mask.any():
                    df.loc[mask, col] = (plan_end_dt[mask] - pd.Timedelta(days=10))
            elif col == 'plan end' and 'plan start' in df.columns:
                # If plan end is missing but plan start exists, estimate end (e.g., 10 days after)
                plan_start_dt = pd.to_datetime(df['plan start'], errors='coerce', dayfirst=True)
                mask = df[col].isna() & plan_start_dt.notna()
                if mask.any():
                    df.loc[mask, col] = (plan_start_dt[mask] + pd.Timedelta(days=10))
            elif col == 'base start' and 'base end' in df.columns:
                # If base start is missing but base end exists, estimate start
                base_end_dt = pd.to_datetime(df['base end'], errors='coerce', dayfirst=True)
                mask = df[col].isna() & base_end_dt.notna()
                if mask.any():
                    df.loc[mask, col] = (base_end_dt[mask] - pd.Timedelta(days=10))
            elif col == 'base end' and 'base start' in df.columns:
                # If base end is missing but base start exists, estimate end
                base_start_dt = pd.to_datetime(df['base start'], errors='coerce', dayfirst=True)
                mask = df[col].isna() & base_start_dt.notna()
                if mask.any():
                    df.loc[mask, col] = (base_start_dt[mask] + pd.Timedelta(days=10))
            
            # Copy from plan to base if base is missing and plan exists
            if col.startswith('base') and col.replace('base', 'plan') in df.columns:
                plan_col = col.replace('base', 'plan')
                plan_dt = pd.to_datetime(df[plan_col], errors='coerce', dayfirst=True)
                mask = df[col].isna() & plan_dt.notna()
                if mask.any():
                    df.loc[mask, col] = plan_dt[mask]
            
            # Format back to string (DD.MM.YYYY format)
            # Convert datetime to string format
            df[col] = df[col].apply(lambda x: x.strftime('%d.%m.%Y') if pd.notna(x) and isinstance(x, pd.Timestamp) else (x if pd.notna(x) else ''))
    
    return df

def fill_reasons(df):
    """Fill gaps in reason of deviation column"""
    if 'reason of deviation' not in df.columns:
        return df
    
    # Fill empty reasons with the first reason from the list
    # You can modify this logic to distribute reasons differently
    empty_mask = df['reason of deviation'].isna() | (df['reason of deviation'] == '')
    
    if empty_mask.sum() > 0:
        # Distribute reasons cyclically
        reason_idx = 0
        for idx in df[empty_mask].index:
            df.at[idx, 'reason of deviation'] = DEVIATION_REASONS[reason_idx % len(DEVIATION_REASONS)]
            reason_idx += 1
    
    return df

def fill_task_names(df, task_list):
    """Fill gaps in task name column using task list from Excel"""
    if 'task name' not in df.columns or not task_list:
        return df
    
    empty_mask = df['task name'].isna() | (df['task name'] == '')
    
    if empty_mask.sum() > 0:
        # Try to match by section or use task list cyclically
        task_idx = 0
        for idx in df[empty_mask].index:
            # If we have section info, try to find matching task
            if 'section' in df.columns and pd.notna(df.at[idx, 'section']):
                section = str(df.at[idx, 'section']).lower()
                # Try to find task that might match section
                matching_tasks = [t for t in task_list if section in str(t).lower() or str(t).lower() in section]
                if matching_tasks:
                    df.at[idx, 'task name'] = matching_tasks[0]
                else:
                    df.at[idx, 'task name'] = task_list[task_idx % len(task_list)]
                    task_idx += 1
            else:
                df.at[idx, 'task name'] = task_list[task_idx % len(task_list)]
                task_idx += 1
    
    return df

def fill_base_dates(df):
    """Fill base start and base end (fact dates) from plan dates if missing"""
    # Convert to datetime for comparison
    if 'plan start' in df.columns:
        df['plan start'] = pd.to_datetime(df['plan start'], errors='coerce', dayfirst=True)
    if 'plan end' in df.columns:
        df['plan end'] = pd.to_datetime(df['plan end'], errors='coerce', dayfirst=True)
    if 'base start' in df.columns:
        df['base start'] = pd.to_datetime(df['base start'], errors='coerce', dayfirst=True)
    if 'base end' in df.columns:
        df['base end'] = pd.to_datetime(df['base end'], errors='coerce', dayfirst=True)
    
    # Copy plan dates to base if base is missing (this is the main logic)
    if 'base start' in df.columns and 'plan start' in df.columns:
        mask = df['base start'].isna() & df['plan start'].notna()
        if mask.any():
            df.loc[mask, 'base start'] = df.loc[mask, 'plan start']
    
    if 'base end' in df.columns and 'plan end' in df.columns:
        mask = df['base end'].isna() & df['plan end'].notna()
        if mask.any():
            df.loc[mask, 'base end'] = df.loc[mask, 'plan end']
    
    # If base start exists but base end is missing, estimate end
    if 'base start' in df.columns and 'base end' in df.columns:
        mask = df['base end'].isna() & df['base start'].notna()
        if mask.any():
            # Use plan end if available, otherwise estimate 10 days after start
            if 'plan end' in df.columns:
                plan_end = pd.to_datetime(df['plan end'], errors='coerce', dayfirst=True)
                mask_with_plan = mask & plan_end.notna()
                if mask_with_plan.any():
                    df.loc[mask_with_plan, 'base end'] = plan_end[mask_with_plan]
                mask_without_plan = mask & plan_end.isna()
                if mask_without_plan.any():
                    df.loc[mask_without_plan, 'base end'] = df.loc[mask_without_plan, 'base start'] + pd.Timedelta(days=10)
            else:
                df.loc[mask, 'base end'] = df.loc[mask, 'base start'] + pd.Timedelta(days=10)
    
    # If base end exists but base start is missing, estimate start
    if 'base start' in df.columns and 'base end' in df.columns:
        mask = df['base start'].isna() & df['base end'].notna()
        if mask.any():
            # Use plan start if available, otherwise estimate 10 days before end
            if 'plan start' in df.columns:
                plan_start = pd.to_datetime(df['plan start'], errors='coerce', dayfirst=True)
                mask_with_plan = mask & plan_start.notna()
                if mask_with_plan.any():
                    df.loc[mask_with_plan, 'base start'] = plan_start[mask_with_plan]
                mask_without_plan = mask & plan_start.isna()
                if mask_without_plan.any():
                    df.loc[mask_without_plan, 'base start'] = df.loc[mask_without_plan, 'base end'] - pd.Timedelta(days=10)
            else:
                df.loc[mask, 'base start'] = df.loc[mask, 'base end'] - pd.Timedelta(days=10)
    
    # For rows with no dates at all, try to use dates from similar rows (same project/section)
    if 'project name' in df.columns:
        for col in ['base start', 'base end', 'plan start', 'plan end']:
            if col in df.columns:
                mask = df[col].isna()
                if mask.any():
                    # Group by project and forward fill/backward fill
                    df[col] = df.groupby('project name')[col].ffill()
                    df[col] = df.groupby('project name')[col].bfill()
    
    # For rows that still have no dates, use default dates (start of 2024, or copy from previous row)
    # First, try to get dates from the most recent row with dates in the same project
    if 'project name' in df.columns:
        for col in ['plan start', 'plan end', 'base start', 'base end']:
            if col in df.columns:
                mask = df[col].isna()
                if mask.any():
                    # For each empty row, find the last non-empty value in the same project
                    for idx in df[mask].index:
                        project = df.at[idx, 'project name']
                        # Get all rows with same project that have this date filled
                        project_rows = df[(df['project name'] == project) & df[col].notna()]
                        if len(project_rows) > 0:
                            # Use the last date from the same project, add some days
                            last_date = project_rows[col].iloc[-1]
                            if pd.notna(last_date):
                                if 'end' in col:
                                    # For end dates, add 15 days
                                    df.at[idx, col] = last_date + pd.Timedelta(days=15)
                                else:
                                    # For start dates, use the same or add 1 day
                                    df.at[idx, col] = last_date + pd.Timedelta(days=1)
    
    # Final fallback: use default dates (01.01.2024 for start, 31.12.2024 for end)
    default_start = pd.Timestamp('2024-01-01')
    default_end = pd.Timestamp('2024-12-31')
    
    for col in ['plan start', 'base start']:
        if col in df.columns:
            mask = df[col].isna()
            if mask.any():
                df.loc[mask, col] = default_start
    
    for col in ['plan end', 'base end']:
        if col in df.columns:
            mask = df[col].isna()
            if mask.any():
                df.loc[mask, col] = default_end
    
    # Format dates back to string
    for col in ['base start', 'base end', 'plan start', 'plan end']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: x.strftime('%d.%m.%Y') if pd.notna(x) and isinstance(x, pd.Timestamp) else (x if pd.notna(x) else ''))
    
    return df

def calculate_deviation(df):
    """Calculate deviation (True/False) and deviation in days"""
    # Convert dates to datetime
    if 'plan end' in df.columns:
        plan_end = pd.to_datetime(df['plan end'], errors='coerce', dayfirst=True)
    else:
        plan_end = pd.Series([pd.NaT] * len(df))
    
    if 'base end' in df.columns:
        base_end = pd.to_datetime(df['base end'], errors='coerce', dayfirst=True)
    else:
        base_end = pd.Series([pd.NaT] * len(df))
    
    # Calculate deviation: True if base end > plan end (delayed)
    if 'deviation' in df.columns:
        mask = plan_end.notna() & base_end.notna()
        df.loc[mask, 'deviation'] = (base_end[mask] > plan_end[mask])
        
        # If base end equals plan end, no deviation
        mask_equal = mask & (base_end == plan_end)
        df.loc[mask_equal, 'deviation'] = False
        
        # If only plan end exists, assume no deviation yet
        mask_plan_only = plan_end.notna() & base_end.isna()
        df.loc[mask_plan_only, 'deviation'] = False
    
    # Calculate deviation in days
    if 'deviation in days' in df.columns:
        mask = plan_end.notna() & base_end.notna()
        deviation_days = (base_end[mask] - plan_end[mask]).dt.days
        df.loc[mask, 'deviation in days'] = deviation_days
        
        # Set to 0 if no deviation or negative (ahead of schedule)
        mask_no_deviation = mask & (deviation_days <= 0)
        df.loc[mask_no_deviation, 'deviation in days'] = 0
        
        # If only plan end exists, set to 0
        mask_plan_only = plan_end.notna() & base_end.isna()
        df.loc[mask_plan_only, 'deviation in days'] = 0
    
    return df

def fill_budget(df, excel_path=None):
    """Fill budget plan and budget fact columns"""
    # Try to read budget from Excel if provided
    budget_data = {}
    if excel_path and Path(excel_path).exists():
        try:
            excel_file = pd.ExcelFile(excel_path)
            for sheet_name in excel_file.sheet_names:
                df_excel = pd.read_excel(excel_path, sheet_name=sheet_name)
                # Look for budget columns
                budget_cols = [col for col in df_excel.columns if any(keyword in str(col).lower() 
                            for keyword in ['budget', 'бюджет', 'стоимость', 'cost', 'price', 'цена'])]
                if budget_cols and 'task name' in df_excel.columns or 'task' in df_excel.columns:
                    # Try to match tasks and extract budget
                    task_col = 'task name' if 'task name' in df_excel.columns else 'task'
                    for idx, row in df_excel.iterrows():
                        task = str(row.get(task_col, '')).strip()
                        if task and budget_cols:
                            budget_val = row.get(budget_cols[0], None)
                            if pd.notna(budget_val):
                                budget_data[task] = float(budget_val)
        except Exception as e:
            print(f"   Warning: Could not read budget from Excel: {e}")
    
    # Fill budget plan
    if 'budget plan' in df.columns:
        empty_mask = (df['budget plan'].isna() | (df['budget plan'] == ''))
        
        if empty_mask.sum() > 0:
            # Try to get from Excel data if task name matches
            if budget_data and 'task name' in df.columns:
                for idx in df[empty_mask].index:
                    task = str(df.at[idx, 'task name']).strip()
                    if task in budget_data:
                        df.at[idx, 'budget plan'] = budget_data[task]
                        continue
            
            # If still empty, try to use average from same project/section
            if 'project name' in df.columns:
                for idx in df[empty_mask].index:
                    project = df.at[idx, 'project name']
                    project_budgets = df[(df['project name'] == project) & 
                                        df['budget plan'].notna() & 
                                        (df['budget plan'] != '')]['budget plan']
                    if len(project_budgets) > 0:
                        # Convert to numeric and get mean
                        numeric_budgets = pd.to_numeric(project_budgets, errors='coerce')
                        if numeric_budgets.notna().any():
                            df.at[idx, 'budget plan'] = numeric_budgets.mean()
                            continue
            
            # If still empty, use a default value (e.g., 50000)
            remaining_empty = df['budget plan'].isna() | (df['budget plan'] == '')
            if remaining_empty.any():
                df.loc[remaining_empty, 'budget plan'] = 50000
    
    # Fill budget fact (copy from budget plan if missing, or use plan * 1.1 as estimate)
    if 'budget fact' in df.columns:
        empty_mask = (df['budget fact'].isna() | (df['budget fact'] == ''))
        
        if empty_mask.sum() > 0:
            # If budget plan exists, use it as fact (or plan * 1.05 as estimate)
            if 'budget plan' in df.columns:
                for idx in df[empty_mask].index:
                    plan_val = df.at[idx, 'budget plan']
                    if pd.notna(plan_val) and plan_val != '':
                        plan_num = pd.to_numeric(plan_val, errors='coerce')
                        if pd.notna(plan_num):
                            # Use plan * 1.05 as estimate for fact
                            df.at[idx, 'budget fact'] = plan_num * 1.05
                            continue
            
            # If still empty, use default
            remaining_empty = df['budget fact'].isna() | (df['budget fact'] == '')
            if remaining_empty.any():
                df.loc[remaining_empty, 'budget fact'] = 52500
    
    return df

def main():
    # File paths - allow CSV file to be specified as argument
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
    else:
        csv_path = Path("sample_project_data.csv")
    
    excel_path = Path("график  -Ленинский_25.11.25_01.xlsx")
    
    # Output file name based on input file
    if len(sys.argv) > 2:
        output_path = Path(sys.argv[2])
    else:
        output_path = csv_path.parent / f"{csv_path.stem}_filled{csv_path.suffix}"
    
    # Check if files exist
    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)
    
    if not excel_path.exists():
        print(f"Error: Excel file not found: {excel_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("Filling gaps in CSV file")
    print("=" * 60)
    
    # Read CSV - try different encodings
    print(f"\n1. Reading CSV file: {csv_path}")
    encodings = ['utf-8', 'windows-1251', 'cp1251', 'latin-1', 'iso-8859-1']
    df = None
    for encoding in encodings:
        try:
            df = pd.read_csv(csv_path, sep=';', encoding=encoding)
            print(f"   Loaded {len(df)} rows, {len(df.columns)} columns (encoding: {encoding})")
            break
        except UnicodeDecodeError:
            continue
    if df is None:
        print("   Error: Could not read CSV with any encoding")
        sys.exit(1)
    
    # Count gaps before
    print("\n2. Analyzing gaps:")
    date_cols = ['base start', 'base end', 'plan start', 'plan end']
    all_cols_to_check = date_cols + ['reason of deviation', 'task name', 'deviation', 'deviation in days', 'budget plan', 'budget fact']
    gaps_before = {}
    for col in all_cols_to_check:
        if col in df.columns:
            empty_count = (df[col].isna() | (df[col] == '')).sum()
            gaps_before[col] = empty_count
            print(f"   {col}: {empty_count} gaps")
    
    # Read task names from Excel
    print(f"\n3. Reading task names from Excel: {excel_path}")
    task_list = read_excel_tasks(excel_path)
    print(f"   Found {len(task_list)} unique task names")
    if task_list:
        print(f"   Sample tasks: {task_list[:5]}")
    
    # Fill gaps
    print("\n4. Filling gaps...")
    
    # Fill dates (plan dates first)
    print("   - Filling plan date gaps...")
    df = fill_dates(df)
    
    # Fill base dates (fact dates)
    print("   - Filling base (fact) date gaps...")
    df = fill_base_dates(df)
    
    # Calculate deviation
    print("   - Calculating deviation...")
    df = calculate_deviation(df)
    
    # Fill reasons
    print("   - Filling reason of deviation gaps...")
    df = fill_reasons(df)
    
    # Fill task names
    print("   - Filling task name gaps...")
    df = fill_task_names(df, task_list)
    
    # Fill budget
    print("   - Filling budget gaps...")
    df = fill_budget(df, excel_path)
    
    # Count gaps after
    print("\n5. Gaps after filling:")
    for col in all_cols_to_check:
        if col in df.columns:
            empty_count = (df[col].isna() | (df[col] == '')).sum()
            filled = gaps_before.get(col, 0) - empty_count
            print(f"   {col}: {empty_count} remaining ({filled} filled)")
    
    # Save result
    print(f"\n6. Saving filled CSV: {output_path}")
    # Try to save with the same encoding that was used for reading
    try:
        # Use QUOTE_NONNUMERIC to quote all text fields - this prevents parsing issues
        # when fields contain commas and the file is opened in Excel or other tools
        df.to_csv(output_path, sep=';', index=False, encoding='utf-8-sig', 
                  quoting=csv.QUOTE_NONNUMERIC, quotechar='"', doublequote=True)
        print(f"   [OK] Saved successfully!")
    except Exception as e:
        print(f"   Error saving: {e}")
        # Try alternative encoding
        try:
            df.to_csv(output_path, sep=';', index=False, encoding='utf-8-sig')
            print(f"   [OK] Saved with utf-8-sig encoding!")
        except Exception as e2:
            # Try windows-1251 as last resort
            df.to_csv(output_path, sep=';', index=False, encoding='windows-1251')
            print(f"   [OK] Saved with windows-1251 encoding!")
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)

if __name__ == "__main__":
    main()

