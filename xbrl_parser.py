import requests
import time
import json
from lxml import etree

# ✅ SEC API Rate Limit (~8-10 requests/sec)
REQUEST_DELAY = 0.5  # 500ms delay per request
MAX_RETRIES = 3  # Retry up to 3 times if request fails
RETRY_DELAY = 3  # Wait 3 sec before retrying failed requests

# ✅ Standard Headers
HEADERS = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}

# 🔹 STEP 1: FIND XBRL URL
def find_xbrl_url(index_url):
    """Finds the XBRL file URL from an SEC index.json."""
    time.sleep(REQUEST_DELAY)  # ✅ Prevent SEC rate limit issues

    response = requests.get(index_url, headers=HEADERS, timeout=5)
    if response.status_code != 200:
        return None

    try:
        data = response.json()
        if "directory" in data and "item" in data["directory"]:
            for file in data["directory"]["item"]:
                if file["name"].endswith(".xml") and "htm.xml" in file["name"]:
                    return index_url.replace("index.json", file["name"])
    except json.JSONDecodeError:
        return None

    return None  # No XBRL file found

# 🔹 STEP 2: FETCH DATA WITH RETRIES
def fetch_with_retries(url):
    """Fetches data from the SEC API with retries."""
    for attempt in range(MAX_RETRIES):
        response = requests.get(url, headers=HEADERS, timeout=5)

        if response.status_code == 200:
            return response.json()  # ✅ Success
        elif response.status_code == 403:
            print(f"⚠️ WARNING: SEC API rate limit hit. Retrying in {RETRY_DELAY} sec...")
        elif response.status_code == 500:
            print(f"❌ ERROR: SEC API is down. Retrying in {RETRY_DELAY} sec...")

        time.sleep(RETRY_DELAY)  # ✅ Wait before retrying

    print("❌ ERROR: SEC API failed after multiple attempts.")
    return None  # Return None if all attempts fail

# 🔹 STEP 3: EXTRACT FINANCIAL DATA FROM XBRL
def extract_summary(xbrl_url):
    """Parses XBRL data to extract key financial metrics."""
    if not xbrl_url:
        print(f"❌ ERROR: Invalid XBRL URL: {xbrl_url}")
        return {}

    time.sleep(REQUEST_DELAY)  # ✅ Prevent SEC rate limit issues
    response = requests.get(xbrl_url, headers=HEADERS, timeout=5)

    if response.status_code != 200:
        print(f"❌ ERROR: Failed to fetch XBRL file: {xbrl_url}")
        return {}

    try:
        root = etree.fromstring(response.content)  # ✅ Proper XML Parsing
    except etree.XMLSyntaxError as e:
        print(f"❌ ERROR: XML parsing failed: {e}")
        return {}

    namespaces = {k if k else "default": v for k, v in root.nsmap.items()}  # ✅ Handle empty namespaces
    print(f"✅ DEBUG: Extracted Namespaces from XBRL: {namespaces}")

    # ✅ Identify the correct namespace prefix dynamically
    possible_prefixes = list(namespaces.keys())
    ns_prefix = "us-gaap"  # Default to US GAAP
    for prefix in possible_prefixes:
        if prefix and prefix not in ["xsi", "xbrldi", "xlink", "iso4217", "link", "dei"]:
            ns_prefix = prefix
            break  # ✅ Use the first valid namespace found

    # ✅ Key Mappings for US GAAP & IFRS
    key_mappings = {
        "Revenue": [
            "Revenue", "Revenues", "SalesRevenueNet", "TotalRevenue",
            "OperatingRevenue", "OperatingRevenues",
            "Turnover", "GrossRevenue",
            "TotalNetSales", "TotalNetRevenues",
            "RevenuesFromContractsWithCustomers"  # ✅ Expanded for Airbnb
        ],
        "NetIncome": ["NetIncomeLoss", "ProfitLoss", "OperatingIncomeLoss"],
        "TotalAssets": ["Assets"],
        "TotalLiabilities": ["Liabilities"],
        "OperatingCashFlow": [
            "CashFlowsFromOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivities",
            "CashGeneratedFromOperations",
            "NetCashFlowsOperating"
        ],
        "CurrentAssets": ["AssetsCurrent", "CurrentAssets"],
        "CurrentLiabilities": ["LiabilitiesCurrent", "CurrentLiabilities"],
        "CashPosition": [  
            "CashAndCashEquivalentsAtCarryingValue",
            "CashAndCashEquivalents",
            "CashCashEquivalentsAndShortTermInvestments",
            "CashAndShortTermInvestments",
            "CashEquivalents"
        ]
    }

    # ✅ Extract Financial Data
    financials = {}
    for key, tags in key_mappings.items():
        for tag in tags:
            full_tag = f"{ns_prefix}:{tag}" if ns_prefix else tag
            values = root.xpath(f"//*[local-name()='{tag}']/text()", namespaces=namespaces)
            if values:
                financials[key] = values[-1].replace(",", "")  # ✅ Take last value (most recent)
                break  # ✅ Stop at first match

    # ✅ Debugging: Print Available Tags if Revenue is Missing
    if "Revenue" not in financials:
        all_tags = {etree.QName(el).localname for el in root.iter()}
        print(f"⚠️ WARNING: Revenue missing! Available tags: {all_tags}")

    # ✅ Assign Final Debt Values
    financials["Debt"] = str(int(sum([
        float(value.replace(",", "")) for tag in [
            "LongTermDebt", "LongTermDebtNoncurrent", "ShortTermBorrowings",
            "NotesPayableCurrent", "DebtInstrument", "DebtObligations",
            "Borrowings", "LoansPayable", "DebtSecurities",
            "DebtAndFinanceLeases", "FinancialLiabilities", "LeaseLiabilities",
            "ConvertibleDebt", "InterestBearingLoans"
        ] if (value := root.xpath(f"//*[local-name()='{tag}']/text()", namespaces=namespaces))
    ]))) if any(root.xpath(f"//*[local-name()='{tag}']", namespaces=namespaces)) else "N/A"

    print(f"✅ DEBUG: Extracted financials: {financials}")
    return financials

# 🔹 STEP 4: FETCH SEC FINANCIALS
def get_sec_financials(cik):
    """Fetches SEC financial data and handles failures gracefully."""
    sec_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/index.json"
    
    data = fetch_with_retries(sec_url)
    if data is None:
        return {"error": "SEC data is temporarily unavailable. Please try again in a few minutes."}

    xbrl_url = find_xbrl_url(sec_url)
    if not xbrl_url:
        return {"error": "XBRL file not found. The company may not have submitted structured data."}

    return extract_summary(xbrl_url)
