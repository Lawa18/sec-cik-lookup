from flask import Flask, request, jsonify
import json
from flask_cors import CORS  # Add CORS

app = Flask(__name__)
CORS(app)  # Allow all origins

# Load JSON files
with open("cik_tickers.json", "r") as f:
    ticker_lookup = json.load(f)

with open("cik_names.json", "r") as f:
    name_lookup = json.load(f)

@app.route("/cik_lookup", methods=["GET"])
def get_cik():
    query = request.args.get("query", "").strip().lower()

    if not query:
        return jsonify({"error": "Query parameter is required."}), 400

    if query in ticker_lookup:
        return jsonify({"cik": ticker_lookup[query]})

    if query in name_lookup:
        return jsonify({"cik": name_lookup[query]})

    return jsonify({"error": "CIK not found."}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
