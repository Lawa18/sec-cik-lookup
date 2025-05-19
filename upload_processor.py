import pandas as pd

def process_uploaded_financials(file_path):
    df = pd.read_csv(file_path) if file_path.endswith('.csv') else pd.read_excel(file_path)

    def safe_get(metric):
        matches = df.loc[df['Metric'] == metric, 'Value'].values
        return matches[0] if len(matches) > 0 else "Missing"

    structured_data = {
        "company": "Uploaded Corp",
        "financials": {
            "Revenue": safe_get('Revenue'),
            "NetIncome": safe_get('Net Income'),
            "TotalAssets": safe_get('Total Assets')
        }
    }
    return structured_data
