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

# Load CIK dataset
ticker_lookup = load_json("cik_tickers.json")

@app.route("/financials", methods=["GET"])
def get_financials():
    query = request.args.get("query", "").strip().lower()

    if not query:
        return jsonify({"error": "Query parameter is required."}), 400

    # Convert dictionary keys to lowercase for case-insensitive search
    ticker_dict = {key.lower(): value for key, value in ticker_lookup.items()}

    # Lookup by exact ticker or company name
    cik = ticker_dict.get(query)

    # Try partial match if no exact match (e.g., "Tesla" should match "Tesla Inc.")
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

    # Extract recent financial filings
    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    urls = filings.get("primaryDocument", [])
    dates = filings.get("filingDate", [])

    # Find latest 10-K or 10-Q
    filing_url = None
    full_text = "No report found."
    for i, form in enumerate(forms):
        if form in ["10-K", "10-Q"]:
            filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{urls[i]}"
            full_text = fetch_filing_text(filing_url)  # Fetch the full document
            break

    if not filing_url:
        return jsonify({"error": "No 10-K or 10-Q found."}), 404

    # Structured financial data
    structured_data = {
        "company": data.get("name", "Unknown"),
        "cik": cik,
        "latest_filing": {
            "formType": form,
            "filingDate": dates[i],
            "filingUrl": filing_url,
            "fullText": full_text[:5000]  # Limit response to 5000 characters for performance
        }
    }

    return jsonify(structured_data)

def fetch_filing_text(url):
    """Fetches first 5000 characters of SEC 10-K/10-Q filing from a given URL."""
    headers = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.text[:5000]  # Limit response to avoid timeout
    return "Error fetching report."

