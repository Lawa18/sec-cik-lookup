import requests
from flask import Flask, request, jsonify
import json
from flask_cors import CORS
from lxml import etree

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins=["*"])  # Allow all origins

# Function to load JSON safely
def load_json(filename):
    """Loads cik_names.json and creates lookup dictionaries for tickers and company names."""
    try:
        with open(filename, "r") as f:
            data = json.load(f)

            cik_by_ticker = {}
            cik_by_company = {}

            for key, item in data.items():
                if not isinstance(item, dict) or "cik_str" not in item:
                    continue  

                cik_str = str(item["cik_str"]).zfill(10)  
                cik_by_ticker[item["ticker"].lower()] = cik_str
                cik_by_company[item["title"].lower()] = cik_str

            return cik_by_ticker, cik_by_company

    except (FileNotFoundError, json.JSONDecodeError):
        return {}, {}

def fetch_sec_data(cik):
    """Fetch latest and historical financials from SEC API."""
    sec_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    headers = {
        "User-Agent": "Lars Wallin lars.e.wallin@gmail.com",
        "Accept": "application/json"
    }
    sec_response = requests.get(sec_url, headers=headers)

    if sec_response.status_code != 200:
        return None

    return sec_response.json()

def extract_summary(xbrl_url):
    """Extracts financial data & calculates key ratios with error handling."""
    if not xbrl_url:
        return "No XBRL file found."

    headers = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}
    response = requests.get(xbrl_url, headers=headers)

    if response.status_code != 200:
        return f"Error fetching XBRL report. Status: {response.status_code}"

    # 🛑 **Check if response content is empty**
    if not response.content.strip():
        return "Error: XBRL file is empty."

    try:
        parser = etree.XMLParser(recover=True)
        tree = etree.fromstring(response.content, parser=parser)

        # 🛑 **Check if tree is None**
        if tree is None:
            return "Error: Could not parse XBRL file."

        # Extract namespaces
        namespaces = {k: v for k, v in tree.nsmap.items() if k}
        print(f"DEBUG: Namespaces detected: {namespaces}")

        financials = {
            "Revenue": extract_xbrl_value(tree, "Revenues", namespaces),
            "NetIncome": extract_xbrl_value(tree, "NetIncomeLoss", namespaces),
            "TotalAssets": extract_xbrl_value(tree, "Assets", namespaces),
            "TotalLiabilities": extract_xbrl_value(tree, "Liabilities", namespaces),
            "OperatingCashFlow": extract_xbrl_value(tree, "NetCashProvidedByUsedInOperatingActivities", namespaces),
            "CurrentAssets": extract_xbrl_value(tree, "AssetsCurrent", namespaces),
            "CurrentLiabilities": extract_xbrl_value(tree, "LiabilitiesCurrent", namespaces),
            "Debt": extract_xbrl_value(tree, "LongTermDebtNoncurrent", namespaces)
        }

        return financials

    except Exception as e:
        print(f"ERROR: Parsing error in extract_summary(): {e}")
        return f"Error extracting financial data: {str(e)}"

def extract_xbrl_value(tree, tag, namespaces):
    """Extracts a specific financial value from XBRL."""
    try:
        value = tree.xpath(f"//*[local-name()='{tag}']/text()", namespaces=namespaces)
        return value[0] if value else "N/A"
    except Exception:
        return "N/A"

@app.route("/financials", methods=["GET"])
def get_financials():
    query = request.args.get("query", "").strip().lower()

    if not query:
        return jsonify({"error": "Query parameter is required."}), 400

    cik_by_ticker, cik_by_company = load_json("cik_names.json")
    cik = cik_by_ticker.get(query) or cik_by_company.get(query)

    if not cik:
        return jsonify({"error": "CIK not found."}), 404

    data = fetch_sec_data(cik)
    if not data:
        return jsonify({"error": "Failed to fetch SEC data."}), 500

    # Fetch latest filing
    filings = data.get("filings", {}).get("recent", {})
    latest_filing = None
    for i, form in enumerate(filings.get("form", [])):
        if form in ["10-K", "10-Q"]:
            latest_filing = {
                "formType": form,
                "filingDate": filings.get("filingDate", ["N/A"])[i],
                "filingUrl": f"https://www.sec.gov/Archives/edgar/data/{cik}/{filings.get('accessionNumber', [''])[i].replace('-', '')}/{filings.get('primaryDocument', [''])[i]}",
                "summary": extract_summary(f"https://www.sec.gov/Archives/edgar/data/{cik}/{filings.get('accessionNumber', [''])[i].replace('-', '')}/index.json")
            }
            break

    return jsonify({
        "company": data.get("name", "Unknown"),
        "cik": cik,
        "latest_filing": latest_filing
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
