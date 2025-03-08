import requests

def fetch_sec_data(cik):
    """Fetch latest and historical financials from SEC API."""
    sec_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    headers = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com", "Accept": "application/json"}
    sec_response = requests.get(sec_url, headers=headers)
    
    if sec_response.status_code != 200:
        return None
    
    return sec_response.json()

def get_sec_financials(cik):
    """Extract financials from SEC filings safely."""
    data = fetch_sec_data(cik)
    if not data:
        return None

    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])

    for i, form in enumerate(forms):
        if form in ["10-K", "10-Q"]:
            # Ensure lists have the expected data
            revenue = filings.get("totalRevenue", [None])
            net_income = filings.get("netIncome", [None])
            total_assets = filings.get("totalAssets", [None])

            return {
                "company": data.get("name", "Unknown"),
                "cik": cik,
                "financials": {
                    "Revenue": revenue[i] if i < len(revenue) else "N/A",
                    "NetIncome": net_income[i] if i < len(net_income) else "N/A",
                    "TotalAssets": total_assets[i] if i < len(total_assets) else "N/A"
                }
            }
    return None  # If no valid filing is found
