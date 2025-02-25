from flask import Flask, request, jsonify
import json

app = Flask(__name__)

# Load JSON datasets (adjust file paths if necessary)
with open("cik_tickers.json", "r") as f:
    ticker_lookup = json.load(f)

with open("cik_names.json", "r") as f:
    name_lookup = json.load(f)

@app.route("/cik_lookup", methods=["GET"])
def get_cik():
    query = request.args.get("query", "").strip().lower()  # Convert input to lowercase

    # Try exact match first (case-insensitive)
    if query in {key.lower(): value for key, value in ticker_lookup.items()}:
        return jsonify({"cik": ticker_lookup[query.upper()]})  # Return CIK for ticker match

    if query in {key.lower(): value for key, value in name_lookup.items()}:
        return jsonify({"cik": name_lookup[query.title()]})  # Return CIK for exact company name match

    # Try partial name match (e.g., "Tesla" should match "Tesla Inc.")
    for name, cik in name_lookup.items():
        if query in name.lower():
            return jsonify({"cik": cik})

    return jsonify({"error": "CIK not found."}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
