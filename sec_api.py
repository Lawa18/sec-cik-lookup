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

def get_sec_financials(cik, max_years=5):
    """Extracts historical SEC filings up to a specified number of years."""
    data = fetch_sec_data(cik)
    if not data:
        return None

    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    filing_dates = filings.get("filingDate", [])
    
    historical_filings = []
    seen_years = set()

    for i, form in enumerate(forms):
        if form in ["10-K", "10-Q"]:
            filing_year = filing_dates[i][:4]  # Extract year from YYYY-MM-DD format
            if filing_year in seen_years or len(seen_years) >= max_years:
                continue  # Skip if we already have max_years of data

            seen_years.add(filing_year)

            accession_number = filings.get("accessionNumber", [None])[i]
            if not accession_number:
                continue  # Skip if no accession number

            from xbrl_parser import find_xbrl_url, extract_summary
            index_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number.replace('-', '')}/index.json"
            xbrl_url = find_xbrl_url(index_url)
            financials = extract_summary(xbrl_url) if xbrl_url else {}

            filing_data = {
                "formType": form,
                "filingDate": filing_dates[i],
                "filingUrl": f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number.replace('-', '')}/{filings.get('primaryDocument', [''])[i]}",
                "xbrlUrl": xbrl_url if xbrl_url else "XBRL file not found.",
                "financials": financials
            }

            historical_filings.append(filing_data)

    return {
        "company": data.get("name", "Unknown"),
        "cik": cik,
        "historical_filings": historical_filings
    }
