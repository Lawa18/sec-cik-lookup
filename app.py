import requests
from flask import Flask, request, jsonify
import json
from flask_cors import CORS
from lxml import etree

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins=["*"])  # Allow all origins (or restrict to OpenAI if needed)

# Ensure all requests contain the correct User-Agent
@app.before_request
def before_request():
    """Ensure all incoming requests contain the correct User-Agent, allowing GPT & SEC requests."""
    allowed_user_agents = [
        "Lars Wallin lars.e.wallin@gmail.com",  # Required for SEC API access
        "Go-http-client/1.1",  # GPT API requests
        "Go-http-client/2.0",  # Some GPT versions
        "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; ChatGPT-User/1.0; +https://openai.com/bot"
    ]
    
    user_agent = request.headers.get("User-Agent")
    print(f"DEBUG: Incoming request - Headers: {dict(request.headers)}")

    if not user_agent:
        print("DEBUG: 403 Forbidden - No User-Agent received.")
        return jsonify({"error": "Missing User-Agent."}), 403

    if user_agent in allowed_user_agents:
        print(f"DEBUG: ✅ Allowed request from User-Agent: {user_agent}")
    else:
        print(f"DEBUG: ⚠️ Unknown User-Agent: {user_agent}, but allowing request.")

# Function to load JSON safely
def load_json(filename):
    """Loads cik_names.json and creates lookup dictionaries for tickers and company names."""
    try:
        with open(filename, "r") as f:
            data = json.load(f)

            cik_by_ticker = {}
            cik_by_company = {}

            for key, item in data.items():
                if not isinstance(item, dict) or "cik_str" not in item or "ticker" not in item or "title" not in item:
                    continue  

                cik_str = str(item["cik_str"]).zfill(10)  
                cik_by_ticker[item["ticker"].lower()] = cik_str
                cik_by_company[item["title"].lower()] = cik_str

            return cik_by_ticker, cik_by_company

    except (FileNotFoundError, json.JSONDecodeError):
        return {}, {}

def find_xbrl_url(index_url):
    """Fetches SEC index.json and finds the correct XBRL file for financial data."""
    headers = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}
    response = requests.get(index_url, headers=headers)

    if response.status_code != 200:
        return None

    try:
        index_data = response.json()
        for file in index_data["directory"]["item"]:
            if file["name"].endswith("_htm.xml") or file["name"].endswith("_full.xml"):
                return f"{index_url.rsplit('/', 1)[0]}/{file['name']}"
    except Exception as e:
        print(f"ERROR: Could not parse SEC index.json: {e}")
        return None

def extract_summary(xbrl_url):
    """Extracts key financial data from the XBRL SEC filing."""
    if not xbrl_url:
        return {}

    headers = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}
    response = requests.get(xbrl_url, headers=headers)

    if response.status_code != 200:
        return {}

    try:
        parser = etree.XMLParser(recover=True)
        tree = etree.fromstring(response.content, parser=parser)

        financial_summary = {
            "Revenue": extract_xbrl_value(tree, "Revenues"),
            "NetIncome": extract_xbrl_value(tree, "NetIncomeLoss"),
            "TotalAssets": extract_xbrl_value(tree, "Assets"),
            "TotalLiabilities": extract_xbrl_value(tree, "Liabilities"),
            "OperatingCashFlow": extract_xbrl_value(tree, "NetCashProvidedByUsedInOperatingActivities"),
            "CurrentAssets": extract_xbrl_value(tree, "AssetsCurrent"),
            "CurrentLiabilities": extract_xbrl_value(tree, "LiabilitiesCurrent"),
            "Debt": extract_xbrl_value(tree, "LongTermDebtNoncurrent"),
        }

        return financial_summary

    except Exception as e:
        print(f"ERROR: Parsing error in extract_summary(): {e}")
        return {}

def extract_xbrl_value(tree, tag):
    """Extracts the value of a specific XBRL financial tag."""
    try:
        value = tree.xpath(f"//*[local-name()='{tag}']/text()")
        return value[0] if value else "N/A"
    except Exception as e:
        print(f"ERROR: Could not extract {tag}: {e}")
        return "N/A"

@app.route("/", methods=["GET"])
def home():
    """Handles root requests and directs users to the correct endpoint."""
    return jsonify({
        "message": "SEC Financial API is running. Use /financials?query=<ticker> for financial data.",
        "example": "https://sec-cik-lookup.onrender.com/financials?query=IBM"
    }), 200

@app.route("/financials", methods=["GET"])
def get_financials():
    query = request.args.get("query", "").strip().lower()

    if not query:
        return jsonify({"error": "Query parameter is required."}), 400

    cik_by_ticker, cik_by_company = load_json("cik_names.json")
    cik = cik_by_ticker.get(query) or cik_by_company.get(query)

    if not cik:
        return jsonify({"error": "CIK not found. This API provides only SEC financial data."}), 404

    sec_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    headers = {
        "User-Agent": "Lars Wallin lars.e.wallin@gmail.com",
        "Accept": "application/json"
    }

    sec_response = requests.get(sec_url, headers=headers)

    if sec_response.status_code != 200:
        return jsonify({"error": "Failed to fetch SEC data.", "status": sec_response.status_code}), sec_response.status_code

    data = sec_response.json()
    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    urls = filings.get("primaryDocument", [])
    accession_numbers = filings.get("accessionNumber", [])
    dates = filings.get("filingDate", [])

    latest_filing = None
    for i, form in enumerate(forms):
        if form in ["10-K", "10-Q"]:
            folder_name = accession_numbers[i].replace("-", "")
            base_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{folder_name}"
            filing_main_url = f"{base_url}/{urls[i]}"
            filing_index_url = f"{base_url}/index.json"

            xbrl_url = find_xbrl_url(filing_index_url)

            latest_filing = {
                "formType": form,
                "filingDate": dates[i],
                "filingUrl": filing_main_url,
                "xbrlUrl": xbrl_url,
                "summary": extract_summary(xbrl_url) if xbrl_url else {}
            }
            break

    if not latest_filing:
        return jsonify({"error": "No 10-K or 10-Q found for this company."}), 404

    return jsonify({
        "company": data.get("name", "Unknown"),
        "cik": cik,
        "latest_filing": latest_filing
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
