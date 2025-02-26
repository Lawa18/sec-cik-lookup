from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

# Load JSON datasets with error handling
def load_json(filename):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return {}

ticker_lookup = load_json("cik_tickers.json")
name_lookup = load_json("cik_names.json")

@app.route("/cik_lookup", methods=["GET"])
def get_cik():
    query = request.args.get("query", "").strip().lower()

    if not query:
        return jsonify({"error": "Query parameter is required."}), 400

    if query in {key.lower(): value for key, value in ticker_lookup.items()}:
        return jsonify({"cik": ticker_lookup[query.upper()]})

    if query in {key.lower(): value for key, value in name_lookup.items()}:
        return jsonify({"cik": name_lookup[query.title()]})

    return jsonify({"error": "CIK not found."}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
