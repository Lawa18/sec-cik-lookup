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

def find_xbrl_url(index_url):
    """Fetches SEC index.json and finds the correct XBRL file for financial data."""
    headers = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}
    response = requests.get(index_url, headers=headers)

    if response.status_code != 200:
        print(f"ERROR: Failed to fetch index.json. Status: {response.status_code}")
        return None

    try:
        index_data = response.json()
        xbrl_file = None

        # ✅ Prioritize MAIN financial statement XBRL files
        for file in index_data["directory"]["item"]:
            name = file["name"].lower()

            # ✅ Prefer _htm.xml or _full.xml (Contains actual data)
            if name.endswith(("_htm.xml", "_full.xml")):
                xbrl_file = f"{index_url.rsplit('/', 1)[0]}/{file['name']}"
                break  

        if not xbrl_file:
            print("⚠️ WARNING: No valid XBRL file found in index.json.")
        else:
            print(f"DEBUG: ✅ Selected XBRL file: {xbrl_file}")

        return xbrl_file

    except Exception as e:
        print(f"ERROR: Could not parse SEC index.json: {e}")
        return None

def extract_summary(xbrl_url):
    """Extracts financial data from the XBRL SEC filing with improved error handling."""
    if not xbrl_url:
        return "No XBRL file found."

    headers = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}
    response = requests.get(xbrl_url, headers=headers)

    if response.status_code != 200:
        return f"Error fetching XBRL report. Status: {response.status_code}"

    # 🛑 Debugging: Print XBRL File URL & First 1000 Characters
    print(f"DEBUG: Fetching XBRL File from: {xbrl_url}")
    print(f"DEBUG: First 1000 characters of XBRL file:\n{response.text[:1000]}")

    try:
        parser = etree.XMLParser(recover=True)
        tree = etree.fromstring(response.content, parser=parser)

        # 🛑 Ensure XBRL File is Parsed Correctly
        if tree is None or not hasattr(tree, "nsmap"):
            print("ERROR: XBRL parsing failed. Tree is None or missing namespaces.")
            return "Error: Could not parse XBRL file."

        # ✅ Extract **all** namespaces dynamically
        namespaces = tree.nsmap
        print("DEBUG: Extracted Namespaces:", namespaces)

        # ✅ Print Full XML Structure for Analysis
        print("DEBUG: Full XBRL Tree Structure:")
        print(etree.tostring(tree, pretty_print=True).decode()[:2000])  # Print first 2000 characters

        # ✅ Extract Key Financial Data
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

        # 🛑 Print Extracted Values for Debugging
        print("DEBUG: Extracted Financial Data:", financials)

        return financials

    except etree.XMLSyntaxError:
        return "Error: XML Syntax Error - File may be corrupted."

    except Exception as e:
        return f"Error extracting financial data: {str(e)}"

def extract_xbrl_value(tree, tag, namespaces):
    """Extracts a specific financial value from XBRL with correct namespace handling."""
    try:
        # ✅ Find the correct prefix for 'us-gaap'
        us_gaap_prefix = None
        for key, value in namespaces.items():
            if "us-gaap" in value:  # Find the correct namespace prefix
                us_gaap_prefix = key
                break

        if not us_gaap_prefix:
            print("❌ ERROR: 'us-gaap' namespace not found in XBRL file!")
            return "N/A"

        # ✅ Construct correct XPath query using `us-gaap` prefix
        xpath_query = f"//{us_gaap_prefix}:{tag}"
        value_elements = tree.xpath(xpath_query, namespaces=namespaces)

        # ✅ Debugging: Print extracted values
        if value_elements:
            extracted_value = value_elements[0].text
            print(f"✅ DEBUG: Found {tag}: {extracted_value}")
            return extracted_value
        else:
            print(f"⚠️ WARNING: {tag} not found in XBRL document.")
            return "N/A"

    except Exception as e:
        print(f"❌ ERROR: Could not extract {tag}: {str(e)}")
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
            accession_number = filings.get("accessionNumber", [None])[i]
            if not accession_number:
                return jsonify({"error": "Accession number not found."}), 500

            index_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number.replace('-', '')}/index.json"
            xbrl_url = find_xbrl_url(index_url)

            latest_filing = {
                "formType": form,
                "filingDate": filings.get("filingDate", ["N/A"])[i],
                "filingUrl": f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number.replace('-', '')}/{filings.get('primaryDocument', [''])[i]}",
                "xbrlUrl": xbrl_url if xbrl_url else "XBRL file not found.",
                "summary": extract_summary(xbrl_url) if xbrl_url else "XBRL file not found."
            }
            break

    return jsonify({
        "company": data.get("name", "Unknown"),
        "cik": cik,
        "latest_filing": latest_filing
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
