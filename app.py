from flask import Flask, request, jsonify
from data_router import get_financial_data
from sec_api import get_company_sic_info, download_multiple_xbrl
from upload_processor import process_uploaded_financials
import os

app = Flask(__name__)

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

    print(f"🔍 DEBUG: Result sent to GPT: {result}")
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
        xbrl_files = download_multiple_xbrl(cik)
        result = []

        for file_path in xbrl_files:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            parts = os.path.basename(file_path).split("_")
            result.append({
                "company_cik": cik,
                "form_type": parts[1] if len(parts) > 1 else "N/A",
                "filing_date": parts[2].replace(".xml", "") if len(parts) > 2 else "N/A",
                "xbrl_text": content
            })

        return jsonify(result)

    except Exception as e:
        print(f"❌ Error in get_multiple_xbrl: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
