from flask import Flask, request, jsonify
from data_router import get_financial_data
from sec_api import get_company_sic_info, download_multiple_xbrl, get_sec_financials
from upload_processor import process_uploaded_financials
import os

app = Flask(__name__)

@app.route("/", methods=["GET"])
def health_check():
    return "✅ SEC API backend is running!", 200

@app.route("/financials", methods=["GET"])
def financials():
    query = request.args.get("query", "").strip().lower()
    print(f"🔍 DEBUG: Received query from GPT: {query}")

    if not query:
        return jsonify({"error": "Query parameter is required."}), 400

    result = get_financial_data(query)

    cik = result.get("cik")
    if cik:
        sic_code, sic_description = get_company_sic_info(cik)
        result["sic_code"] = str(sic_code) if sic_code else "N/A"
        result["sic_description"] = sic_description if sic_description else "N/A"
    else:
        result["sic_code"] = "N/A"
        result["sic_description"] = "N/A"

    print(f"📦 Returning result: {result}")
    return jsonify(result)

@app.route("/upload", methods=["POST"])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files['file']
    file_path = os.path.join("uploads", file.filename)
    file.save(file_path)
    structured_data = process_uploaded_financials(file_path)
    return jsonify(structured_data)

@app.route("/get_multiple_xbrl", methods=["GET"])
def get_multiple_xbrl():
    cik = request.args.get("cik", "").strip()
    if not cik:
        return jsonify({"error": "CIK parameter is required"}), 400

    try:
        financials = get_sec_financials(cik)
        combined = financials.get("historical_annuals", []) + financials.get("historical_quarters", [])
        return jsonify(combined)

    except Exception as e:
        print(f"❌ Error in get_multiple_xbrl: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
