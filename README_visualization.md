# Project Plan vs Fact Visualization Dashboard

A comprehensive Streamlit dashboard for visualizing and analyzing project data, comparing planned vs actual dates and budgets.

## Features

- 📅 **Date Analysis**
  - Timeline comparison (Plan vs Actual durations)
  - Gantt chart visualization
  - Deviation distribution analysis

- 💰 **Budget Analysis**
  - Budget Plan vs Fact comparison charts
  - Budget variance scatter analysis
  - Budget summary by project/section

- 🔍 **Interactive Filters**
  - Filter by project
  - Filter by section
  - Filter by deviation status

- 📊 **Summary Statistics**
  - Total tasks count
  - Average deviation in days
  - Total budget plan vs fact
  - Budget variance percentage

## Installation

1. Install required dependencies:
```bash
pip install -r requirements_visualization.txt
```

Or install individually:
```bash
pip install streamlit pandas plotly openpyxl
```

## Usage

### Quick Start

1. **Run the Streamlit app:**
```bash
streamlit run project_visualization_app.py
```

Or use the batch file (Windows):
```bash
start_visualization_app.bat
```

2. **Upload your data file:**
   - Click "Browse files" in the sidebar
   - Select your CSV or Excel file
   - The app will automatically load and validate your data

3. **Use filters:**
   - Select specific projects or sections from the sidebar
   - Filter by deviation status
   - Visualizations will update automatically

### Data Format

Your data file should contain the following columns:

| Column Name | Type | Description |
|------------|------|-------------|
| project name | string | Name of the project |
| abbreviation | string | Project abbreviation |
| section | string | Section/category |
| task name | string | Name of the task |
| base start | date | Actual start date |
| base end | date | Actual end date |
| plan start | date | Planned start date |
| plan end | date | Planned end date |
| deviation | boolean | Whether there is a deviation |
| deviation in days | integer | Number of days of deviation |
| reason of deviation | string | Explanation for the deviation |
| budget plan | integer | Planned budget amount |
| budget fact | integer | Actual budget amount |

### Sample Data

A sample CSV file (`sample_project_data.csv`) is included for testing. You can use it to explore the dashboard features.

## Visualizations

### 1. Timeline Comparison
Scatter plot comparing planned duration vs actual duration for each task. Points above the diagonal line indicate delays.

### 2. Gantt Chart
Visual timeline showing both planned and actual task durations overlaid on a calendar.

### 3. Budget Comparison
Grouped bar chart comparing planned vs actual budgets for the top 20 tasks.

### 4. Budget Variance Analysis
Scatter plot showing budget plan vs fact with color-coded variance percentages.

### 5. Budget Summary
Aggregated budget comparison grouped by project or section.

## Tips

- **Large datasets**: The app automatically limits some visualizations (e.g., top 20 tasks) for better readability
- **Date formats**: The app supports various date formats and will attempt to parse them automatically
- **Missing data**: Tasks with missing dates or budgets will be excluded from relevant visualizations
- **Export**: Use the "View Raw Data" expander to see and copy the filtered dataset

## Troubleshooting

**Issue**: "No valid date data available"
- **Solution**: Check that your date columns are properly formatted and contain valid dates

**Issue**: "No valid budget data available"
- **Solution**: Ensure budget columns contain numeric values (not text or empty cells)

**Issue**: Charts not displaying
- **Solution**: Make sure you have valid data in the required columns and that filters haven't excluded all rows

## Requirements

- Python 3.8+
- streamlit >= 1.52.1
- pandas >= 2.0.0
- plotly >= 5.17.0
- openpyxl >= 3.1.0 (for Excel file support)

