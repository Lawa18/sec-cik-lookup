import requests
from flask import Flask, request, jsonify
import json

app = Flask(__name__)

# Load JSON datasets
with open("cik_tickers.json", "r") as f:
    ticker_lookup = json.load(f)

@app.route("/cik_lookup", methods=["GET"])
def get_cik():
    query = request.args.get("query", "").strip().lower()
    
    if not query:
        return jsonify({"error": "Query parameter is required."}), 400

    if query in ticker_lookup:
        cik = ticker_lookup[query]

        # SEC API request (ensures User-Agent is included)
        sec_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        headers = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}
        
        sec_response = requests.get(sec_url, headers=headers)

        if sec_response.status_code == 200:
            data = sec_response.json()

            # Extract latest 10-K or 10-Q filing
            recent_filings = data.get("filings", {}).get("recent", {})
            forms = recent_filings.get("form", [])
            urls = recent_filings.get("primaryDocument", [])
            dates = recent_filings.get("filingDate", [])

            # Find the latest 10-K or 10-Q
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
        
        else:
            return jsonify({"error": "SEC API request failed.", "status": sec_response.status_code}), sec_response.status_code

    return jsonify({"error": "CIK not found."}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
