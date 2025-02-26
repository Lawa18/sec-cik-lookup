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
            return sec_response.json()
        else:
            return jsonify({"error": "SEC API request failed.", "status": sec_response.status_code}), sec_response.status_code

    return jsonify({"error": "CIK not found."}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
