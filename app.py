
from flask import Flask, request, jsonify
from data_router import get_financial_data
from sec_api import get_company_sic_info
from upload_processor import process_uploaded_financials
import os

app = Flask(__name__)

@app.route("/financials", methods=["GET"])
def financials():
    query = request.args.get("query", "").strip().lower()
    print(f"🔍 DEBUG: Received query from GPT: {query}")  # ✅ Log incoming query

    if not query:
        return jsonify({"error": "Query parameter is required."}), 400

    from data_router import get_financial_data
from sec_api import get_company_sic_info
    result = get_financial_data(query)

    cik = result.get("cik")
    if cik:
        sic_code, sic_description = get_company_sic_info(cik)
        result["sic_code"] = str(sic_code) if sic_code else "N/A"
        result["sic_description"] = sic_description if sic_description else "N/A"
    else:
        result["sic_code"] = "N/A"
        result["sic_description"] = "N/A"

    print(f"🔍 DEBUG: Result sent to GPT: {result}")  # ✅ Log response sent to GPT

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
