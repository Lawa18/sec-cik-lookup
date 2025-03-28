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
                time.sleep(RETRY_DELAY)
            else:
                break
        except requests.exceptions.RequestException:
            time.sleep(RETRY_DELAY)

    return None  

# 🔹 STEP 2: FIND XBRL URL
def find_xbrl_url(index_url):
    """Finds the XBRL file URL from an SEC index.json."""
    time.sleep(REQUEST_DELAY)

    response = fetch_with_retries(index_url)
    if not response:
        return None

    try:
        for file in response.get("directory", {}).get("item", []):
            if file["name"].endswith(".xml") and "htm.xml" in file["name"]:
                return index_url.replace("index.json", file["name"])
    except json.JSONDecodeError:
        return None

    return None  

# 🔹 STEP 3: EXTRACT FINANCIAL DATA FROM XBRL
def extract_summary(xbrl_url):
    """Parses XBRL data to extract key financial metrics accurately."""
    
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

    # ✅ **Stable Key Mappings (Updated for Accuracy)**
    key_mappings = {
        "Revenue": [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
            "Revenue"
        ],
        "IncomeTaxes": [
            "IncomeTaxExpenseBenefit",
            "ProvisionForIncomeTaxes",
            "IncomeTaxesPaidNet"
        ],
        "NetIncome": [  
            "NetIncomeLoss",
            "NetIncomeLossAvailableToCommonStockholdersDiluted"
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
        "Capex": [
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "CapitalExpenditures",
            "PropertyPlantAndEquipmentAdditions"
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
        "CashPosition": [  
            "CashAndCashEquivalentsAtCarryingValue",
            "CashAndCashEquivalents",
            "RestrictedCashAndCashEquivalents",
            "CashAndShortTermInvestments",
            "ShortTermInvestments"
        ],
        "Equity": [  
            "StockholdersEquity",
            "TotalStockholdersEquity"
        ],
        "Debt": [  
            "LongTermDebt",
            "LongTermDebtNoncurrent",
            "DebtInstrumentCarryingAmount",
            "LongTermDebtAndCapitalLeaseObligations",
            "DebtCurrent",
            "NotesPayable"
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

    # ✅ **Fix for Cash Position (Summing Cash & Short-Term Investments)**
    cash_values = root.xpath("//*[local-name()='CashAndCashEquivalents' or local-name()='CashAndShortTermInvestments' or local-name()='ShortTermInvestments' or local-name()='RestrictedCashAndCashEquivalents']/text()", namespaces=namespaces)
    if cash_values:
        try:
            financials["CashPosition"] = sum(float(value.replace(",", "")) for value in cash_values)
        except ValueError:
            financials["CashPosition"] = "N/A"

    # ✅ **Fix for Total Debt Calculation**
    total_debt = 0
    for tag in key_mappings["Debt"]:
        values = root.xpath(f"//*[local-name()='{tag}']/text()", namespaces=namespaces)
        if values:
            try:
                total_debt += float(values[-1].replace(",", ""))  
            except ValueError:
                pass

    financials["Debt"] = str(int(total_debt)) if total_debt > 0 else "N/A"

    return financials
