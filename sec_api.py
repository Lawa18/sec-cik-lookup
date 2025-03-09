import requests

def fetch_sec_data(cik):
    """Fetch latest and historical financials from SEC API."""
    sec_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    headers = {
        "User-Agent": "Lars Wallin lars.e.wallin@gmail.com",
        "Accept": "application/json"
    }
    sec_response = requests.get(sec_url, headers=headers)

    if sec_response.status_code != 200:
        return None

    return sec_response.json()

def get_sec_financials(cik):
    """Extract financials from SEC filings using XBRL if necessary."""
    data = fetch_sec_data(cik)
    if not data:
        return None

    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])

    for i, form in enumerate(forms):
        if form in ["10-K", "10-Q"]:
            accession_number = filings.get("accessionNumber", [None])[i]
            if not accession_number:
                return {"error": "Accession number not found."}

            from xbrl_parser import find_xbrl_url, extract_summary  # Import here to avoid circular issues
            index_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number.replace('-', '')}/index.json"
            xbrl_url = find_xbrl_url(index_url)
            financials = extract_summary(xbrl_url) if xbrl_url else "XBRL file not found."

            return {
                "company": data.get("name", "Unknown"),
                "cik": cik,
                "latest_filing": {
                    "formType": form,
                    "filingDate": filings.get("filingDate", ["N/A"])[i],
                    "filingUrl": f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number.replace('-', '')}/{filings.get('primaryDocument', [''])[i]}",
                    "xbrlUrl": xbrl_url if xbrl_url else "XBRL file not found.",
                    "financials": financials
                }
            }
    return None
