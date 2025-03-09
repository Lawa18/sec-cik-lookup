from xbrl_parser import find_xbrl_url, extract_summary  # ✅ Fix import issue

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
