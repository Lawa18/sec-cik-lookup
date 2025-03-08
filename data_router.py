from sec_api import get_sec_financials

def get_financial_data(query):
    """Route requests to the correct data source based on query input."""
    cik_by_ticker = {"ibm": "0000051143"}  # Example mapping
    cik = cik_by_ticker.get(query.lower())
    
    if cik:
        return get_sec_financials(cik)
    
    return {"error": "Company not found"}
