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
    """Extract financials from SEC filings."""
    data = fetch_sec_data(cik)
    if not data:
        return None
    
    filings = data.get("filings", {}).get("recent", {})
    
    for i, form in enumerate(filings.get("form", [])):
        if form in ["10-K", "10-Q"]:
            return {
                "company": data.get("name", "Unknown"),
                "cik": cik,
                "financials": {
                    "Revenue": filings.get("totalRevenue", [None])[i],
                    "NetIncome": filings.get("netIncome", [None])[i],
                    "TotalAssets": filings.get("totalAssets", [None])[i]
                }
            }
    return None
