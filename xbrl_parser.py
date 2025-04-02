import requests
import time
import json
from lxml import etree

# ✅ SEC API Rate Limit (~8-10 requests/sec)
REQUEST_DELAY = 0.5
MAX_RETRIES = 5
RETRY_DELAY = 5
TIMEOUT = 10

# ✅ Standard Headers
HEADERS = {"User-Agent": "Lars Wallin lars.e.wallin@gmail.com"}

# 🔹 STEP 1: FETCH DATA WITH IMPROVED ERROR HANDLING
def fetch_with_retries(url):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if response.status_code == 200:
                return response.json()
            elif response.status_code in [403, 500, 503]:
                time.sleep(RETRY_DELAY)
            else:
                break
        except requests.exceptions.Timeout:
            time.sleep(RETRY_DELAY)
        except requests.exceptions.RequestException:
            time.sleep(RETRY_DELAY)
    return None

# 🔹 STEP 2: FIND XBRL URL
def find_xbrl_url(index_url):
    time.sleep(REQUEST_DELAY)
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
    return None

# 🔹 STEP 3: EXTRACT FINANCIAL DATA FROM XBRL
def extract_summary(xbrl_url):
    if not xbrl_url:
        return {}

    time.sleep(REQUEST_DELAY)
    response = requests.get(xbrl_url, headers=HEADERS, timeout=TIMEOUT)
    if response.status_code != 200:
        return {}

    try:
        root = etree.fromstring(response.content)
    except etree.XMLSyntaxError:
        return {}

    namespaces = {k if k else "default": v for k, v in root.nsmap.items()}

    key_mappings = {
        "Revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet", "Revenue"],
        "NetIncome": ["NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersDiluted"],
        "TotalAssets": ["Assets", "TotalAssets", "AssetsFairValueDisclosure"],
        "OperatingCashFlow": ["NetCashProvidedByUsedInOperatingActivities"],
        "CurrentAssets": ["AssetsCurrent"],
        "CurrentLiabilities": ["LiabilitiesCurrent"],
        "CashPosition": ["CashAndCashEquivalents"],
        "Equity": ["StockholdersEquity", "TotalStockholdersEquity"],
        "CapEx": ["PaymentsToAcquirePropertyPlantAndEquipment"],
        "IncomeTaxExpense": ["IncomeTaxExpenseBenefit"],
        "Debt": ["LongTermDebt", "DebtCurrent"]
    }

    financials = {}

    for key, tags in key_mappings.items():
        best_value = None
        for tag in tags:
            values = root.xpath(f"//*[local-name()='{tag}']", namespaces=namespaces)
            for node in values:
                value = node.text
                context = node.get("contextRef", "")
                if value and value.replace("-", "").replace(",", "").replace(".", "").isdigit():
                    try:
                        float_val = float(value.replace(",", ""))
                        if best_value is None or ("2025" in context and abs(float_val) > abs(best_value)):
                            best_value = float_val
                    except ValueError:
                        continue
        if best_value is not None:
            financials[key] = best_value
        else:
            financials[key] = "N/A"

    total_debt = 0
    for tag in key_mappings["Debt"]:
        for node in root.xpath(f"//*[local-name()='{tag}']", namespaces=namespaces):
            context = node.get("contextRef", "")
            value = node.text
            if value and "2025" in context:
                try:
                    total_debt += float(value.replace(",", ""))
                except ValueError:
                    continue
    if total_debt > 0:
        financials["Debt"] = round(total_debt, 2)

    return financials
