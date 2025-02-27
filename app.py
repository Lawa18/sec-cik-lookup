import requests
from flask import Flask, request, jsonify
import json

app = Flask(__name__)

# Function to load JSON safely
def load_json(filename):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Load datasets
ticker_lookup = load_json("cik_tickers.json")

@app.route("/financials", methods=["GET"])
def get_financials():
    query = request.args.get("query", "").strip().lower()

    if not query:
        return jsonify({"error": "Query parameter is required."}), 400

    # Convert dictionary keys to lowercase for case-insensitive search
    ticker_dict = {key.lower(): value for key, value in ticker_lookup.items()}

    # Exact match lookup
    cik = ticker_dict.get(query)

    # Partial match (e.g., "Tesla" should match "Tesla Inc.")
    if not cik:
        for name, cik_value in ticker_dict.items():
            if query in name.lower():
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
    recent_filings = data.get("filings", {}).get("recent", {})
    forms = recent_filings.get("form", [])
    urls = recent_filings.get("primaryDocument", [])
    dates = recent_filings.get("filingDate", [])

    for i, form in enumerate(forms):
        if form in ["10-K", "10-Q"]:
            filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{urls[i]}"
            return jsonify({
                "cik": cik,
                "company": data.get("name", "Unknown"),
                "latest_filing": {
                    "formType": form,
                    "filingDate": dates[i],
                    "filingUrl": filing_url
                }
            })

    return jsonify({"error": "No 10-K or 10-Q found."}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
