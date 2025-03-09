def get_financial_data(query):
    """Fetches financial data using the correct CIK mapping."""
    cik_by_ticker, cik_by_company = load_cik_mappings()
    
    cik = cik_by_ticker.get(query.lower()) or cik_by_company.get(query.lower())

    if not cik:
        return {
            "error": "SEC data is only available for publicly listed US companies. "
                     "UBER may not have direct SEC filings. Try another company or check alternative sources."
        }

    from sec_api import get_sec_financials
    return get_sec_financials(cik)
