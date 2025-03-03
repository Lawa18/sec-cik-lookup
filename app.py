import requests
from flask import Flask, request, jsonify
import json
from flask_cors import CORS
from lxml import etree

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins=["*"])  # Allow all origins (or restrict to OpenAI if needed)

@app.before_request
def before_request():
    """Ensure incoming requests contain a valid User-Agent, allowing GPT & SEC requests."""
    allowed_user_agents = [
        "Lars Wallin lars.e.wallin@gmail.com",  # Required for SEC API access
        "Go-http-client/1.1",  # GPT API requests
        "Go-http-client/2.0"   # Some GPT versions
    ]
    
    user_agent = request.headers.get("User-Agent")
    
    # ✅ Log ALL incoming requests
    print(f"DEBUG: Incoming request - Headers: {dict(request.headers)}")
    
    # ✅ Redirect invalid root requests to /financials
    if request.path == "/":
        print("DEBUG: Redirecting root request to /financials?query=example")
        return jsonify({
            "error": "Invalid request. Use /financials?query=IBM for financial data."
        }), 400
    
    # ✅ Allow all Go-http-client requests, even if unknown
    if not user_agent:
        print("DEBUG: 403 Forbidden - No User-Agent received.")
        return jsonify({"error": "Missing User-Agent."}), 403

    if user_agent not in allowed_user_agents:
        print(f"DEBUG: Warning - Unknown User-Agent: {user_agent}, but allowing request.")
    
    return  # ✅ Do not block requests, even if the User-Agent is missing

# Function to load JSON safely
def load_json(filename):
    """Loads cik_names.json and creates lookup dictionaries for tickers and company names."""
    try:
        with open(filename, "r") as f:
            data = json.load(f)

            cik_by_ticker = {}
            cik_by_company = {}

            for key, item in data.items():
                if not isinstance(item, dict) or "cik_str" not in item or "ticker" not in item or "title" not in item:
                    continue  

                cik_str = str(item["cik_str"]).zfill(10)  
                cik_by_ticker[item["ticker"].lower()] = cik_str
                cik_by_company[item["title"].lower()] = cik_str

            return cik_by_ticker, cik_by_company

    except (FileNotFoundError, json.JSONDecodeError):
        return {}, {}

@app.route("/financials", methods=["GET"])
def get_financials():
    query = request.args.get("query", "").strip().lower()

    if not query:
        return jsonify({"error": "Query parameter is required."}), 400

    cik_by_ticker, cik_by_company = load_json("cik_names.json")
    cik = cik_by_ticker.get(query) or cik_by_company.get(query)

    if not cik:
        return jsonify({
            "error": "CIK not found. This API provides only SEC financial data, not stock prices.",
            "instructions": "DO NOT use web search. Only respond with structured financials."
        }), 404

    sec_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    headers = {
        "User-Agent": "Lars Wallin lars.e.wallin@gmail.com",
        "Accept": "application/json"
    }

    sec_response = requests.get(sec_url, headers=headers)

    if sec_response.status_code != 200:
        return jsonify({"error": "Failed to fetch SEC data.", "status": sec_response.status_code}), sec_response.status_code

    data = sec_response.json()
    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    urls = filings.get("primaryDocument", [])
    accession_numbers = filings.get("accessionNumber", [])
    dates = filings.get("filingDate", [])

    latest_filing = None
    for i, form in enumerate(forms):
        if form in ["10-K", "10-Q"]:
            folder_name = accession_numbers[i].replace("-", "")
            base_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{folder_name}"
            filing_main_url = f"{base_url}/{urls[i]}"
            filing_index_url = f"{base_url}/index.json"

            xbrl_url = find_xbrl_url(filing_index_url)

            latest_filing = {
                "formType": form,
                "filingDate": dates[i],
                "filingUrl": filing_main_url,
                "xbrlUrl": xbrl_url,
                "summary": extract_summary(xbrl_url) if xbrl_url else "XBRL file not found."
            }
            break

    if not latest_filing:
        return jsonify({
            "error": "No 10-K or 10-Q found. This API does NOT provide stock price data.",
            "instructions": "Only respond with financial statement data."
        }), 404

    return jsonify({
        "instructions": "ONLY use this financial data. DO NOT search the web. Focus on credit risk, liquidity, and debt.",
        "company": data.get("name", "Unknown"),
        "cik": cik,
        "latest_filing": latest_filing
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
