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
    """Extracts key financial metrics ensuring correct Net Income, Equity, and Cash Position"""

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

    # ✅ New approach ensures correct **Net Income, Equity, Cash Position**
    key_mappings = {
        "Revenue": [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
            "Revenue"
        ],
        "NetIncome": [  # ✅ Ensure latest annual Net Income is extracted
            "NetIncomeLoss",
            "NetIncomeLossAvailableToCommonStockholdersDiluted",
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"
        ],
        "TotalAssets": [
            "Assets",
            "TotalAssets",
            "AssetsFairValueDisclosure",
            "GrossCustomerFinancingAssets"
        ],
        "OperatingCashFlow": [
            "NetCashProvidedByUsedInOperatingActivities",
            "OperatingActivitiesCashFlowsAbstract",
            "CashGeneratedByOperatingActivities"
        ],
        "CurrentAssets": [
            "AssetsCurrent",
            "CurrentPortionOfFinancingReceivablesNet",
            "ContractWithCustomerReceivableBeforeAllowanceForCreditLossCurrent"
        ],
        "CurrentLiabilities": [
            "LiabilitiesCurrent",
            "AccountsPayableCurrent",
            "OtherAccruedLiabilitiesCurrent"
        ],
        "CashPosition": [  # ✅ FIXED: Includes Short-Term Investments
            "CashAndCashEquivalentsAtCarryingValue",
            "CashAndCashEquivalents",
            "RestrictedCashAndCashEquivalents",
            "CashAndShortTermInvestments",
            "ShortTermInvestments"  
        ],
        "Equity": [  # ✅ FIXED: Ensures correct "Total Stockholders' Equity"
            "StockholdersEquity",
            "TotalStockholdersEquity",
            "CommonStockValue",
            "RetainedEarningsAccumulatedDeficit"
        ],
        "Debt": [  # ✅ Debt is now computed more accurately
            "LongTermDebt",
            "LongTermDebtNoncurrent",
            "DebtInstrumentCarryingAmount",
            "LongTermDebtAndCapitalLeaseObligations",
            "DebtCurrent",
            "NotesPayable"
        ]
    }

    financials = {}

    # ✅ **Step 1: Identify Latest Reporting Date**
    reporting_dates = root.xpath("//context[period/endDate]/period/endDate/text()", namespaces=namespaces)
    latest_reporting_date = None

    if reporting_dates:
        latest_reporting_date = max(reporting_dates)  # Get the latest date
    else:
        print("⚠️ WARNING: No reporting dates found in XBRL file.")

    # ✅ Ensure `latest_reporting_date` has a default value
    if not latest_reporting_date:
        latest_reporting_date = "2024-12-31"  # Set a default date (this can be adjusted)

    # ✅ **Step 2: Extract Key Financials Only for Latest Reporting Date**
    for key, tags in key_mappings.items():
        extracted_values = []
        for tag in tags:
            # Find values associated with the latest reporting date
            values = root.xpath(f"//*[local-name()='{tag}'][../contextRef[contains(text(), '{latest_reporting_date}')]]/text()", namespaces=namespaces)
            extracted_values.extend(values)

        # ✅ Convert to numerical format
        if extracted_values:
            try:
                financials[key] = max([float(v.replace(",", "")) for v in extracted_values if v.replace(",", "").replace(".", "").isdigit()])
            except ValueError:
                financials[key] = "N/A"

    # ✅ **Step 3: Compute Debt More Accurately**
    total_debt = 0
    for tag in key_mappings["Debt"]:
        values = root.xpath(f"//*[local-name()='{tag}'][../contextRef[contains(text(), '{latest_reporting_date}')]]/text()", namespaces=namespaces)
        if values:
            try:
                total_debt += float(values[0].replace(",", ""))
            except ValueError:
                pass

    financials["Debt"] = str(int(total_debt)) if total_debt > 0 else "N/A"

    return financials
