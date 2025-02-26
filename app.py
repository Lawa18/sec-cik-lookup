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

@app.route("/cik_lookup", methods=["GET"])
def get_cik():
    query = request.args.get("query", "").strip().lower()

    if not query:
        return jsonify({"error": "Query parameter is required."}), 400

    # Convert dictionary keys to lowercase for case-insensitive search
    ticker_dict = {key.lower(): value for key, value in ticker_lookup.items()}

    # Exact match lookup
    if query in ticker_dict:
        return jsonify({"cik": ticker_dict[query]})

    # Partial match search (supports "Tesla" matching "Tesla Inc.")
    for name, cik in ticker_dict.items():
        if query in name.lower():
            return jsonify({"cik": cik})

    return jsonify({"error": "CIK not found."}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
