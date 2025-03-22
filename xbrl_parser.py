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
        elif response.status_code in [403, 500]:
            time.sleep(RETRY_DELAY)  # ✅ Wait before retrying
        else:
            break  # No need to retry on other errors

    return None if response.status_code != 200 else response.json()

# 🔹 STEP 3: EXTRACT FINANCIAL DATA FROM XBRL
def extract_summary(xbrl_url):
    """Parses XBRL data to extract key financial metrics."""
    if not xbrl_url:
        print("❌ ERROR: Invalid XBRL URL")
        return {}

    time.sleep(REQUEST_DELAY)  # ✅ Prevent SEC rate limit issues
    response = requests.get(xbrl_url, headers=HEADERS, timeout=5)

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
