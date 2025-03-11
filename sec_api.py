import requests
from xbrl_parser import find_xbrl_url, extract_summary  # ✅ Import once at the top

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
    """Extracts the last 5 years of annual and last 4 quarters of financials from SEC filings."""
    data = fetch_sec_data(cik)
    if not data:
        return None

    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    filing_dates = filings.get("filingDate", [])  # ✅ Store this separately for safe access
    accession_numbers = filings.get("accessionNumber", [])

    historical_annuals = []
    historical_quarters = []
    
    seen_years = set()
    seen_quarters = 0

    for i, form in enumerate(forms):
        if i >= len(filing_dates) or i >= len(accession_numbers):  # ✅ Prevent index errors
            continue

        filing_year = filing_dates[i][:4] if filing_dates[i] else "N/A"

        if form in ["10-K", "20-F"] and filing_year not in seen_years and len(seen_years) < 5:
            seen_years.add(filing_year)
        elif form in ["10-Q", "6-K"] and seen_quarters < 4:
            seen_quarters += 1
        else:
            continue  # Skip if we already have enough filings

        accession_number = accession_numbers[i]
        if not accession_number:
            continue

        index_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number.replace('-', '')}/index.json"
        xbrl_url = find_xbrl_url(index_url)
        financials = extract_summary(xbrl_url) if xbrl_url else {}

        filing_data = {
            "formType": form,
            "filingDate": filing_dates[i] if i < len(filing_dates) else "N/A",
            "filingUrl": f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number.replace('-', '')}/{filings.get('primaryDocument', [''])[i]}",
            "xbrlUrl": xbrl_url if xbrl_url else "XBRL file not found.",
            "financials": financials
        }

        if form in ["10-K", "20-F"]:
            historical_annuals.append(filing_data)
        elif form in ["10-Q", "6-K"]:
            historical_quarters.append(filing_data)

    # ✅ Filter out 6-Ks with no financial data
    historical_quarters = [filing for filing in historical_quarters if any(value != "N/A" for value in filing["financials"].values())]

    return {
        "company": data.get("name", "Unknown"),
        "cik": cik,
        "historical_annuals": historical_annuals,
        "historical_quarters": historical_quarters
    }
