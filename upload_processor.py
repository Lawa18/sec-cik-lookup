import pandas as pd

def process_uploaded_financials(file_path):
    """Parses user-uploaded financial statements and structures data."""
    df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)
    structured_data = {
        "company": "Uploaded Corp",
        "financials": {
            "Revenue": df.loc[df['Metric'] == 'Revenue', 'Value'].values[0],
            "NetIncome": df.loc[df['Metric'] == 'Net Income', 'Value'].values[0],
            "TotalAssets": df.loc[df['Metric'] == 'Total Assets', 'Value'].values[0]
        }
    }
    return structured_data
