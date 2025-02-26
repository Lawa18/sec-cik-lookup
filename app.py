from flask import Flask, request, jsonify
import json

app = Flask(__name__)

# Function to safely load JSON files
def load_json(filename):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
        return {}  
    except json.JSONDecodeError:
        print(f"Error: {filename} is not a valid JSON file.")
        return {}

# Load datasets
ticker_lookup = load_json("cik_tickers.json")  # Ticker lookup should be lowercase
name_lookup = load_json("cik_names.json")  # Company name lookup should be lowercase

@app.route("/cik_lookup", methods=["GET"])
def get_cik():
    query = request.args.get("query", "").strip().lower()  # Normalize input to lowercase

    if not query:
        return jsonify({"error": "Query parameter is required."}), 400

    # Convert dictionary keys to lowercase for case-insensitive lookup
    ticker_dict = {key.lower(): value for key, value in ticker_lookup.items()}
    name_dict = {key.lower(): value for key, value in name_lookup.items()}

    # Try ticker lookup first
    if query in ticker_dict:
        return jsonify({"cik": ticker_dict[query]})

    # Try company name lookup
    if query in name_dict:
        return jsonify({"cik": name_dict[query]})

    return jsonify({"error": "CIK not found."}), 404  # Proper 404 instead of crashing

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
