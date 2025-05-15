# data_router.py
import json

def load_cik_mappings():
    """Loads CIK mappings from cik_names.json."""
    try:
        with open("cik_names.json", "r") as f:
            data = json.load(f)

        cik_by_ticker = {item["ticker"].lower(): str(item["cik_str"]).zfill(10) for item in data.values() if "ticker" in item}
        cik_by_company = {item["title"].lower(): str(item["cik_str"]).zfill(10) for item in data.values() if "title" in item}

        return cik_by_ticker, cik_by_company

    except Exception as e:
        print(f"⚠️ ERROR: Could not load cik_names.json: {e}")
        return {}, {}

def get_financial_data(query):
    """Fetches financial data using the correct CIK mapping."""
    cik_by_ticker, cik_by_company = load_cik_mappings()
    query_lc = query.lower().strip()

    # Exact match by ticker or company name
    cik = cik_by_ticker.get(query_lc) or cik_by_company.get(query_lc)

    # Fuzzy fallback: partial match against known company names
    if not cik:
        for name, value in cik_by_company.items():
            if query_lc in name:
                cik = value
                break

    if not cik:
        return {
            "error": "SEC data is only available for publicly listed US companies. "
                     "This company may not have direct SEC filings. Try another company or check alternative sources."
        }

    from sec_api import get_sec_financials
    return get_sec_financials(cik)
