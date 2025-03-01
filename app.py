import requests
from flask import Flask, request, jsonify
import json
from flask_cors import CORS  # Enable CORS for OpenAI API access

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# Function to load JSON safely
def load_json(filename):
    """Loads cik_names.json and creates lookup dictionaries for tickers and company names."""
    try:
        with open(filename, "r") as f:
            data = json.load(f)

            print(f"DEBUG: Loaded {filename}, total entries: {len(data)}")

            # Check if data is a dictionary
            if not isinstance(data, dict):
                print(f"ERROR: {filename} is not a dictionary! It is a {type(data)}.")
                return {}, {}

            cik_by_ticker = {}
            cik_by_company = {}

            for key, item in data.items():  # Loop through indexed dictionary
                if not isinstance(item, dict) or "cik_str" not in item or "ticker" not in item or "title" not in item:
                    print(f"ERROR: Invalid format at key {key}: {item}")
                    continue  # Skip invalid entries

                cik_str = str(item["cik_str"]).zfill(10)  # Convert CIK to string with leading zeros
                cik_by_ticker[item["ticker"].lower()] = cik_str
                cik_by_company[item["title"].lower()] = cik_str

            print(f"SUCCESS: Processed {len(cik_by_company)} companies and {len(cik_by_ticker)} tickers.")

            return cik_by_ticker, cik_by_company

    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"ERROR: Could not load {filename}. Exception: {e}")
        return {}, {}
        
@app.route("/financials", methods=["GET"])
def get_financials():
    query = request.args.get("query", "").strip().lower()

    if not query:
        return jsonify({"error": "Query parameter is required."}), 400

    # Load the CIK database (single file)
    cik_by_ticker, cik_by_company = load_json("cik_names.json")

    # If files failed to load, return error
    if not cik_by_ticker or not cik_by_company:
        return jsonify({"error": "Failed to load CIK database. Check JSON format."}), 500

    # Exact match lookup (first try ticker, then company name)
    cik = cik_by_ticker.get(query) or cik_by_company.get(query)

    # Partial match (if no exact match)
    if not cik:
        for name, cik_value in cik_by_company.items():
            if query in name:
                cik = cik_value
                break

    if not cik:
        return jsonify({"error": "CIK not found."}), 404

    return jsonify({"cik": cik})

    # Fetch financial data from SEC
    sec_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    headers = {
        "User-Agent": "Lars Wallin lars.e.wallin@gmail.com",  # REQUIRED by SEC API
        "Accept": "application/json"
    }

    sec_response = requests.get(sec_url, headers=headers)

    # Handle SEC API errors
    if sec_response.status_code == 403:
        return jsonify({"error": "SEC API blocked request (403 Forbidden). Check User-Agent header."}), 403
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
