import requests
from flask import Flask, request, jsonify
import json
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Allow cross-origin requests (for OpenAI integration)

# Function to load JSON safely
def load_json(filename):
    """Loads cik_names.json and creates lookup dictionaries for tickers and company names."""
    try:
        with open(filename, "r") as f:
            data = json.load(f)

            cik_by_ticker = {}
            cik_by_company = {}

            for key, item in data.items():  # Loop through indexed dictionary
                if not isinstance(item, dict) or "cik_str" not in item or "ticker" not in item or "title" not in item:
                    continue  # Skip invalid entries

                cik_str = str(item["cik_str"]).zfill(10)  # Convert CIK to string with leading zeros
                cik_by_ticker[item["ticker"].lower()] = cik_str
                cik_by_company[item["title"].lower()] = cik_str

            return cik_by_ticker, cik_by_company

    except (FileNotFoundError, json.JSONDecodeError):
        return {}, {}

@app.route("/financials", methods=["GET"])
def get_financials():
    query = request.args.get("query", "").strip().lower()

    if not query:
        return jsonify({"error": "Query parameter is required."}), 400

    # Load the CIK database
    cik_by_ticker, cik_by_company = load_json("cik_names.json")

    # Exact match lookup
    cik = cik_by_ticker.get(query) or cik_by_company.get(query)

    # Partial match (if no exact match)
    if not cik:
        for name, cik_value in cik_by_company.items():
            if query in name:
                cik = cik_value
                break

    if not cik:
        return jsonify({"error": "CIK not found."}), 404

    # Fetch latest SEC filings
    sec_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    headers = {
        "User-Agent": "Lars Wallin lars.e.wallin@gmail.com",
        "Accept": "application/json"
    }
    
    sec_response = requests.get(sec_url, headers=headers)

    if sec_response.status_code != 200:
        return jsonify({"error": "Failed to fetch SEC data.", "status": sec_response.status_code}), sec_response.status_code

    data = sec_response.json()

    # Extract the latest 10-K or 10-Q filing
    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    urls = filings.get("primaryDocument", [])
    accession_numbers = filings.get("accessionNumber", [])
    dates = filings.get("filingDate", [])

    # Find the latest 10-K or 10-Q
    latest_filing = None
    for i, form in enumerate(forms):
        if form in ["10-K", "10-Q"]:
            folder_name = accession_numbers[i].replace("-", "")
            base_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{folder_name}"
            filing_main_url = f"{base_url}/{urls[i]}"  # Main filing document
            filing_index_url = f"{base_url}/index.json"  # JSON index of all documents in the filing

            # Fetch filing index to find the XBRL file
            xbrl_url = find_xbrl_url(filing_index_url)

            latest_filing = {
                "formType": form,
                "filingDate": dates[i],
                "filingUrl": filing_main_url,
                "xbrlUrl": xbrl_url,
                "summary": extract_summary(xbrl_url) if xbrl_url else "XBRL file not found."
            }
            break

    if not latest_filing:
        return jsonify({"error": "No 10-K or 10-Q found."}), 404

    return jsonify({
        "company": data.get("name", "Unknown"),
        "cik": cik,
        "latest_filing": latest_filing
    })

from lxml import etree

def find_xbrl_url(index_url):
    """Fetches SEC index.json and finds the correct XBRL financial file."""
    headers = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}
    response = requests.get(index_url, headers=headers)

    if response.status_code != 200:
        return None

    try:
        index_data = response.json()
        for file in index_data["directory"]["item"]:
            # Ignore FilingSummary.xml and instead get financial statements
            if file["name"].endswith(".xml") or file["name"].endswith(".xbrl"):
                if "cal" in file["name"].lower() or "def" in file["name"].lower() or "pre" in file["name"].lower():
                    return f"{index_url.rsplit('/', 1)[0]}/{file['name']}"  # Construct full XBRL file URL
    except Exception as e:
        print(f"Error parsing index.json: {e}")

    return None

from lxml import etree

def extract_summary(xbrl_url):
    """Extracts key financial data from XBRL SEC filings."""
    if not xbrl_url:
        return "No XBRL file found."

    headers = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}
    response = requests.get(xbrl_url, headers=headers)

    if response.status_code != 200:
        return f"Error fetching XBRL report. Status: {response.status_code}"

    try:
        # Parse XBRL using lxml
        parser = etree.XMLParser(recover=True)
        tree = etree.fromstring(response.content, parser=parser)

        # Extract all namespace mappings dynamically
        namespaces = {k: v for k, v in tree.nsmap.items() if k}

        # Print namespace mappings for debugging
        print(f"DEBUG: Namespaces detected: {namespaces}")

        # Extract key financial metrics using namespaces
        financial_summary = {
            "Revenue": extract_xbrl_value(tree, "Revenues", namespaces),
            "NetIncome": extract_xbrl_value(tree, "NetIncomeLoss", namespaces),
            "TotalAssets": extract_xbrl_value(tree, "Assets", namespaces),
            "TotalLiabilities": extract_xbrl_value(tree, "Liabilities", namespaces),
            "OperatingCashFlow": extract_xbrl_value(tree, "NetCashProvidedByUsedInOperatingActivities", namespaces),
            "CurrentAssets": extract_xbrl_value(tree, "AssetsCurrent", namespaces),
            "CurrentLiabilities": extract_xbrl_value(tree, "LiabilitiesCurrent", namespaces),
            "Debt": extract_xbrl_value(tree, "LongTermDebtNoncurrent", namespaces)
        }

        print(f"DEBUG: Extracted financials: {financial_summary}")

        return financial_summary

    except Exception as e:
        print(f"ERROR: Parsing error in extract_summary(): {e}")
        return "Error extracting financial data."

def extract_xbrl_value(tree, tag, namespaces):
    """Extracts the value of a specific XBRL financial tag, handling namespaces dynamically."""
    try:
        value = tree.xpath(f"//*[local-name()='{tag}']/text()", namespaces=namespaces)
        return value[0] if value else "N/A"
    except Exception as e:
        print(f"ERROR: Could not extract {tag}: {e}")
        return "N/A"

    # Limit response size to avoid performance issues
    return response.text[:5000]  

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
