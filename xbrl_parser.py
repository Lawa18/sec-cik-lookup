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

    # ✅ Key Mappings for US GAAP & IFRS
    key_mappings = {
        "Revenue": [
            "Revenue", "Revenues", "SalesRevenueNet", "TotalRevenue",
            "OperatingRevenue", "OperatingRevenues",
            "Turnover", "GrossRevenue",
            "TotalNetSales", "TotalNetRevenues"  # ✅ Apple's label for Revenue
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
        "CashPosition": [  # ✅ Correct tag for cash position
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
            value = root.xpath(f"//*[local-name()='{tag}']/text()", namespaces=namespaces)
            if value:
                financials[key] = value[0].replace(",", "")
                break  # ✅ Stop at first match

    # ✅ Debt Extraction (Sum all debt-related tags)
    debt_tags = [
        "LongTermDebt", "LongTermDebtNoncurrent", "ShortTermBorrowings",
        "NotesPayableCurrent", "DebtInstrument", "DebtObligations",
        "Borrowings", "LoansPayable", "DebtSecurities",
        "DebtAndFinanceLeases", "FinancialLiabilities", "LeaseLiabilities",
        "ConvertibleDebt", "InterestBearingLoans"
    ]
    
    total_debt = 0
    for tag in debt_tags:
        value = root.xpath(f"//*[local-name()='{tag}']/text()", namespaces=namespaces)
        if value:
            try:
                total_debt += float(value[0].replace(",", ""))
            except ValueError:
                pass

    # ✅ Assign Final Debt Values
    financials["Debt"] = str(int(total_debt)) if total_debt > 0 else "N/A"

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

# 🔹 STEP 5: XBRL VALUE EXTRACTION HELPER
def extract_xbrl_value(tree, tag, ns=None):
    """Extracts the value of a specific XBRL financial tag using namespace handling."""
    try:
        if ns is None:
            ns = {}

        xpath_query = f"//*[local-name()='{tag}']"
        value = tree.xpath(xpath_query + "/text()", namespaces=ns)

        if value:
            extracted_value = value[0]
            print(f"✅ DEBUG: Found {tag}: {extracted_value}")
            return extracted_value
        else:
            print(f"⚠️ WARNING: {tag} not found in XBRL document.")
            return "N/A"

    except Exception as e:
        print(f"❌ ERROR: Could not extract {tag}: {str(e)}")
        return "N/A"
