import requests
from flask import Flask, request, jsonify
import json

# Initialize Flask app
app = Flask(__name__)

# Function to load JSON safely
def load_json(filename):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

@app.route("/financials", methods=["GET"])
def get_financials():
    query = request.args.get("query", "").strip().lower()

    if not query:
        return jsonify({"error": "Query parameter is required."}), 400

    # Load datasets
    ticker_dict = load_json("cik_tickers.json")
    company_dict = load_json("cik_names.json")  

    # Convert keys to lowercase for case-insensitive search
    ticker_dict = {key.lower(): value for key, value in ticker_dict.items()}
    company_dict = {key.lower(): value for key, value in company_dict.items()}

    # Lookup by exact ticker or company name
    cik = ticker_dict.get(query) or company_dict.get(query)

    # Partial match (if no exact match)
    if not cik:
        for name, cik_value in company_dict.items():
            if query in name:
                cik = cik_value
                break

    if not cik:
        return jsonify({"error": "CIK not found."}), 404

    # Fetch financial data from SEC
    sec_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    headers = {
        "User-Agent": "Lars Wallin lars.e.wallin@gmail.com",
        "Accept": "application/json"
    }
    
    sec_response = requests.get(sec_url, headers=headers)

    if sec_response.status_code != 200:
        return jsonify({"error": "Failed to fetch SEC data.", "status": sec_response.status_code}), sec_response.status_code

    data = sec_response.json()

    # Extract the latest 10-K or 10-Q filing
    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    urls = filings.get("primaryDocument", [])
    dates = filings.get("filingDate", [])

    # Find the latest 10-K or 10-Q
    latest_filing = None
    for i, form in enumerate(forms):
        if form in ["10-K", "10-Q"]:
            filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{urls[i]}"
            latest_filing = {
                "formType": form,
                "filingDate": dates[i],
                "filingUrl": filing_url
            }
            break

    if not latest_filing:
        return jsonify({"error": "No 10-K or 10-Q found."}), 404

    return jsonify({
        "company": data.get("name", "Unknown"),
        "cik": cik,
        "latest_filing": latest_filing
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
