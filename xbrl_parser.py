import requests
import time
import json
from lxml import etree

# ✅ SEC API Rate Limit (~8-10 requests/sec)
REQUEST_DELAY = 0.5  # 500ms delay per request
MAX_RETRIES = 5  # Retry up to 5 times if request fails
RETRY_DELAY = 5  # Wait 5 sec before retrying failed requests
TIMEOUT = 10  # Increase API timeout

# ✅ Standard Headers
HEADERS = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}

# 🔹 STEP 1: FETCH DATA WITH IMPROVED ERROR HANDLING
def fetch_with_retries(url):
    """Fetches data from the SEC API with retries & improved error handling."""
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            
            # ✅ SUCCESS: Return JSON data if the request works
            if response.status_code == 200:
                return response.json()
            
            # 🚦 RATE LIMIT HIT: Handle 403 Errors
            elif response.status_code == 403:
                print(f"⚠️ WARNING: SEC API rate limit hit. Retrying in {RETRY_DELAY} sec (Attempt {attempt}/{MAX_RETRIES})...")
                time.sleep(RETRY_DELAY)

            # 🔄 SERVER DOWN: Handle 500/503 Errors
            elif response.status_code in [500, 503]:
                print(f"❌ ERROR: SEC API is down. Retrying in {RETRY_DELAY} sec (Attempt {attempt}/{MAX_RETRIES})...")
                time.sleep(RETRY_DELAY)

            # 🚨 UNKNOWN ERROR: Log it properly
            else:
                print(f"❌ ERROR: Unexpected API response ({response.status_code}) - {response.text}")
                break  # Do not retry unknown errors

        except requests.exceptions.Timeout:
            print(f"⏳ TIMEOUT: SEC API did not respond. Retrying in {RETRY_DELAY} sec (Attempt {attempt}/{MAX_RETRIES})...")
            time.sleep(RETRY_DELAY)

        except requests.exceptions.RequestException as e:
            print(f"❌ ERROR: API request failed ({str(e)}). Retrying in {RETRY_DELAY} sec (Attempt {attempt}/{MAX_RETRIES})...")
            time.sleep(RETRY_DELAY)

    print("🚨 FINAL ERROR: SEC API failed after multiple attempts. Please try again later.")
    return None  # Return None if all attempts fail

# 🔹 STEP 2: FIND XBRL URL
def find_xbrl_url(index_url):
    """Finds the XBRL file URL from an SEC index.json."""
    time.sleep(REQUEST_DELAY)  # ✅ Prevent SEC rate limit issues

    response = fetch_with_retries(index_url)
    if not response:
        return None

    try:
        if "directory" in response and "item" in response["directory"]:
            for file in response["directory"]["item"]:
                if file["name"].endswith(".xml") and "htm.xml" in file["name"]:
                    return index_url.replace("index.json", file["name"])
    except json.JSONDecodeError:
        return None

    return None  # No XBRL file found

# 🔹 STEP 3: EXTRACT FINANCIAL DATA FROM XBRL
def extract_summary(xbrl_url):
    """Parses XBRL data to extract key financial metrics."""
    if not xbrl_url:
        print("❌ ERROR: Invalid XBRL URL")
        return {}

    time.sleep(REQUEST_DELAY)  # ✅ Prevent SEC rate limit issues
    response = requests.get(xbrl_url, headers=HEADERS, timeout=TIMEOUT)

    if response.status_code != 200:
        print("❌ ERROR: Failed to fetch XBRL file")
        return {}

    try:
        root = etree.fromstring(response.content)  # ✅ Proper XML Parsing
    except etree.XMLSyntaxError:
        print("❌ ERROR: XML parsing failed")
        return {}

    namespaces = {k if k else "default": v for k, v in root.nsmap.items()}  

    # ✅ **Extract Revenue Efficiently**
    revenue_value = None
    correct_revenue_tags = [
        "Revenue", "TotalRevenue", "SalesRevenueNet",
        "OperatingRevenue", "TotalNetSales",
        "RevenueFromContractWithCustomerExcludingAssessedTax"
    ]

    for tag in correct_revenue_tags:
        values = root.xpath(f"//*[local-name()='{tag}']/text()", namespaces=namespaces)
        if values and values[0].strip():
            revenue_value = values[0].replace(",", "")
            break  # ✅ Stop at first valid match

    # ✅ Compute Debt
    debt_tags = [
        "LongTermDebt", "LongTermDebtNoncurrent", "ShortTermBorrowings",
        "NotesPayableCurrent", "DebtInstrument", "DebtObligations"
    ]
    
    total_debt = 0
    for tag in debt_tags:
        values = root.xpath(f"//*[local-name()='{tag}']/text()", namespaces=namespaces)
        if values:
            try:
                total_debt += float(values[0].replace(",", ""))
            except ValueError:
                pass

    # ✅ Extract Other Financials
    key_mappings = {
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

    financials = {"Revenue": revenue_value if revenue_value else "N/A"}

    # ✅ Extract Other Key Financials
    for key, tags in key_mappings.items():
        for tag in tags:
            values = root.xpath(f"//*[local-name()='{tag}']/text()", namespaces=namespaces)
            if values:
                financials[key] = values[-1].replace(",", "")
                break  # ✅ Stop at first match

    # ✅ Assign Debt Value
    financials["Debt"] = str(int(total_debt)) if total_debt > 0 else "N/A"

    return financials

# 🔹 STEP 4: GET SEC FINANCIALS
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
