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
    """Fetches data from the SEC API with retries & improved error handling."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code in [403, 500, 503]:
                print(f"⚠️ WARNING: SEC API rate limit hit or server issue. Retrying in {RETRY_DELAY} sec (Attempt {attempt}/{MAX_RETRIES})...")
                time.sleep(RETRY_DELAY)
            else:
                print(f"❌ ERROR: Unexpected API response ({response.status_code}) - {response.text}")
                break

        except requests.exceptions.Timeout:
            print(f"⏳ TIMEOUT: SEC API did not respond. Retrying in {RETRY_DELAY} sec (Attempt {attempt}/{MAX_RETRIES})...")
            time.sleep(RETRY_DELAY)

        except requests.exceptions.RequestException as e:
            print(f"❌ ERROR: API request failed ({str(e)}). Retrying in {RETRY_DELAY} sec (Attempt {attempt}/{MAX_RETRIES})...")
            time.sleep(RETRY_DELAY)

    print("🚨 FINAL ERROR: SEC API failed after multiple attempts. Please try again later.")
    return None  

# 🔹 STEP 2: FIND XBRL URL
def find_xbrl_url(index_url):
    """Finds the XBRL file URL from an SEC index.json."""
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
    """Parses XBRL data to extract key financial metrics accurately."""
    
    if not xbrl_url:
        print("❌ ERROR: Invalid XBRL URL")
        return {}

    time.sleep(REQUEST_DELAY)
    response = requests.get(xbrl_url, headers=HEADERS, timeout=TIMEOUT)

    if response.status_code != 200:
        print("❌ ERROR: Failed to fetch XBRL file")
        return {}

    try:
        root = etree.fromstring(response.content)
    except etree.XMLSyntaxError:
        print("❌ ERROR: XML parsing failed")
        return {}

    namespaces = {k if k else "default": v for k, v in root.nsmap.items()}  

    # ✅ **Stable Key Mappings**
    key_mappings = {
        "Revenue": [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
            "Revenue"
        ],
        "NetIncome": [  
            "NetIncomeLoss",
            "NetIncomeLossAvailableToCommonStockholdersDiluted"
        ],
        "TotalAssets": [  
            "Assets",
            "TotalAssets"
        ],
        "OperatingCashFlow": [
            "NetCashProvidedByUsedInOperatingActivities"
        ],
        "CurrentAssets": [
            "AssetsCurrent"
        ],
        "CurrentLiabilities": [  
            "LiabilitiesCurrent"
        ],
        "CashPosition": [  
            "CashAndCashEquivalentsAtCarryingValue",
            "CashAndCashEquivalents",
            "ShortTermInvestments"  # ✅ Only include short-term, no restricted cash
        ],
        "Equity": [  
            "StockholdersEquity",
            "TotalStockholdersEquity"
        ],
        "Debt": [  
            "LongTermDebt",
            "LongTermDebtNoncurrent",
            "DebtCurrent"
        ]
    }

    financials = {}

    # ✅ **Extract Key Financials Correctly**
    for key, tags in key_mappings.items():
        extracted_values = []
        for tag in tags:
            values = root.xpath(f"//*[local-name()='{tag}']/text()", namespaces=namespaces)
            extracted_values.extend(values)

        if extracted_values:
            try:
                latest_values = [float(v.replace(",", "")) for v in extracted_values if v.replace(",", "").replace(".", "").isdigit()]
                if latest_values:
                    financials[key] = latest_values[-1]  
            except ValueError:
                financials[key] = "N/A"

    # ✅ **Fix for Cash Position (Summing Only Liquid Assets)**
    cash_values = root.xpath("//*[local-name()='CashAndCashEquivalents' or local-name()='ShortTermInvestments']/text()", namespaces=namespaces)
    if cash_values:
        try:
            financials["CashPosition"] = sum(float(value.replace(",", "")) for value in cash_values)
        except ValueError:
            financials["CashPosition"] = "N/A"

    # ✅ **Fix for Total Assets (Ensuring Correct Period Selection)**
    total_assets_values = root.xpath("//*[local-name()='Assets' or local-name()='TotalAssets']/text()", namespaces=namespaces)
    if total_assets_values:
        try:
            financials["TotalAssets"] = max(float(value.replace(",", "")) for value in total_assets_values)
        except ValueError:
            financials["TotalAssets"] = "N/A"

    # ✅ **Fix for Total Debt (Ensuring Correct Inclusion)**
    total_debt = 0
    for tag in key_mappings["Debt"]:
        values = root.xpath(f"//*[local-name()='{tag}']/text()", namespaces=namespaces)
        if values:
            try:
                total_debt += float(values[-1].replace(",", ""))
            except ValueError:
                pass

    financials["Debt"] = str(int(total_debt)) if total_debt > 0 else "N/A"

    # ✅ **Fix for Equity Extraction**
    equity_values = root.xpath("//*[local-name()='StockholdersEquity' or local-name()='TotalStockholdersEquity']/text()", namespaces=namespaces)
    if equity_values:
        try:
            financials["Equity"] = float(equity_values[-1].replace(",", ""))
        except ValueError:
            financials["Equity"] = "N/A"

    return financials
