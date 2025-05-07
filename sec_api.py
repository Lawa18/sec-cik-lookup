import requests
import time
import os
import lxml.etree as ET
import yaml
from flask import Flask, request, jsonify
from xbrl_parser import find_xbrl_url

app = Flask(__name__)

HEADERS = {
    'User-Agent': 'Lars Wallin (lars.e.wallin@gmail.com)',
    'Accept-Encoding': 'gzip, deflate',
    'Accept': '*/*',
    'Connection': 'keep-alive'
}

SEC_API_BASE = 'https://data.sec.gov'

FALLBACK_TAGS = {'Revenue': ['us-gaap:Revenues', 'us-gaap:SalesRevenueNet', 'us-gaap:SalesRevenueGoodsGross', 'us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax', 'us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax', 'us-gaap:RevenueFromContractWithCustomer', 'us-gaap:Revenue', 'us-gaap:RevenueFromContractsWithCustomers'], 'COGS': ['us-gaap:CostOfRevenue', 'us-gaap:CostOfRevenues', 'us-gaap:CostOfGoodsSold', 'us-gaap:CostOfGoodsAndServicesSold', 'us-gaap:CostOfSales', 'PG_CostOfGoodsSold'], 'OperatingIncome': ['us-gaap:OperatingIncomeLoss', 'us-gaap:ProfitLossFromOperatingActivities'], 'EBITDA': ['us-gaap:EBITDA', 'us-gaap:EarningsBeforeInterestTaxesDepreciationAmortization', 'us-gaap:AdjustedEBITDA'], 'InterestExpense': ['us-gaap:InterestExpense', 'us-gaap:InterestAndDebtExpense', 'us-gaap:InterestIncomeExpenseNonoperatingNet', 'us-gaap:FinanceCosts', 'us-gaap:InterestExpenseDebt', 'us-gaap:InterestAndOtherDebtExpense', 'us-gaap:InterestExpenseAndFinanceCost'], 'NetIncome': ['us-gaap:NetIncomeLoss', 'us-gaap:ProfitLoss', 'us-gaap:NetIncome'], 'TotalAssets': ['us-gaap:Assets'], 'CurrentAssets': ['us-gaap:AssetsCurrent', 'us-gaap:CurrentAssets', 'us-gaap:CurrentAssetsAndOtherAssets'], 'Cash': ['us-gaap:CashAndCashEquivalentsAtCarryingValue', 'us-gaap:CashAndCashEquivalents', 'us-gaap:CashCashEquivalentsAndShortTermInvestments'], 'Receivables': ['us-gaap:AccountsReceivableNetCurrent', 'us-gaap:ReceivablesNetCurrent', 'us-gaap:TradeAndOtherReceivables', 'us-gaap:TradeReceivablesGrossCurrent', 'us-gaap:CurrentTradeReceivables'], 'Inventory': ['us-gaap:InventoryNet', 'us-gaap:Inventories', 'us-gaap:FinishedGoods', 'us-gaap:RawMaterials', 'us-gaap:WorkInProcess'], 'CurrentLiabilities': ['us-gaap:LiabilitiesCurrent', 'us-gaap:CurrentLiabilities'], 'ShortTermDebt': ['us-gaap:ShortTermBorrowings', 'us-gaap:ShorttermBorrowings', 'us-gaap:DebtCurrent', 'us-gaap:BorrowingsCurrent', 'us-gaap:DebtInstrumentCurrent'], 'LongTermDebt': ['us-gaap:LongTermDebt', 'us-gaap:NoncurrentBorrowings', 'us-gaap:BorrowingsNoncurrent', 'us-gaap:DebtInstrumentNoncurrent'], 'TotalLiabilities': ['us-gaap:Liabilities', 'us-gaap:LiabilitiesAndStockholdersEquity'], 'Equity': ['us-gaap:StockholdersEquity', 'us-gaap:Equity', 'us-gaap:EquityAttributableToOwnersOfParent', 'us-gaap:LiabilitiesAndStockholdersEquityIncludingPortionAttributableToNoncontrollingInterestMinusLiabilities'], 'OperatingCashFlow': ['us-gaap:NetCashProvidedByUsedInOperatingActivities', 'us-gaap:NetCashFlowsFromOperatingActivities', 'us-gaap:CashFlowsFromUsedInOperatingActivities', 'us-gaap:NetCashProvidedByOperatingActivities'], 'CapitalExpenditures': ['us-gaap:PaymentsToAcquirePropertyPlantAndEquipment', 'us-gaap:PurchaseOfPropertyPlantAndEquipment', 'us-gaap:PaymentsForPropertyPlantAndEquipment', 'us-gaap:CapitalExpenditurePayments']}

def safe_get(url, headers=HEADERS, retries=3, delay=1):
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(delay)
    raise Exception(f"Failed to fetch URL after {retries} attempts: {url}")

def extract_line_items(xbrl_text, fallback_tags):
    extracted = {}
    try:
        root = ET.fromstring(xbrl_text.encode("utf-8"))
        for metric, tags in fallback_tags.items():
            found = False
            for tag in tags:
                parts = tag.split(":")
                local_tag = parts[-1]
                el = root.find(f".//{*}{local_tag}")
                if el is not None and el.text and el.text.strip():
                    try:
                        extracted[metric] = float(el.text.replace(",", "").replace("(", "-").replace(")", ""))
                    except:
                        extracted[metric] = el.text.strip()
                    found = True
                    break
            if not found:
                extracted[metric] = "Missing tag"
    except Exception as e:
        print(f"❌ XBRL Parse error: {e}")
    return extracted

def fetch_sec_data(cik):
    sec_url = f"{SEC_API_BASE}/submissions/CIK{cik}.json"
    headers = {
        "User-Agent": "Lars Wallin lars.e.wallin@gmail.com",
        "Accept": "application/json"
    }
    try:
        sec_response = requests.get(sec_url, headers=headers, timeout=10)
        sec_response.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ ERROR: Failed to fetch SEC data for CIK {cik}: {e}")
        return {}
    return sec_response.json()

def get_company_submissions(cik):
    cik = cik.zfill(10)
    url = f"{SEC_API_BASE}/submissions/CIK{cik}.json"
    return safe_get(url).json()

def get_filing_index(cik, accession):
    acc_no_no_hyphens = accession.replace('-', '')
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_no_hyphens}/index.json"
    try:
        return safe_get(url).json()
    except Exception:
        hyphenated_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/index.json"
        return safe_get(hyphenated_url).json()

def get_sec_financials(cik):
    data = fetch_sec_data(cik)
    if not data:
        return {
            "company": "Unknown",
            "cik": cik,
            "historical_annuals": [],
            "historical_quarters": []
        }

    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    filing_dates = filings.get("filingDate", [])
    accession_numbers = filings.get("accessionNumber", [])
    primary_documents = filings.get("primaryDocument", [])

    historical_annuals = []
    historical_quarters = []
    seen_years = set()
    seen_quarters = 0

    for i, form in enumerate(forms):
        if i >= len(filing_dates) or i >= len(accession_numbers) or i >= len(primary_documents):
            continue

        filing_year = filing_dates[i][:4] if filing_dates[i] else "N/A"

        if form in ["10-K", "20-F"] and filing_year not in seen_years and len(seen_years) < 5:
            seen_years.add(filing_year)
        elif form in ["10-Q", "6-K"] and seen_quarters < 4:
            seen_quarters += 1
        else:
            continue

        accession_number = accession_numbers[i]
        if not accession_number:
            continue

        index_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number.replace('-', '')}/index.json"
        xbrl_url = find_xbrl_url(index_url)
        xbrl_text = safe_get(xbrl_url).text if xbrl_url else None
        extracted_data = extract_line_items(xbrl_text, FALLBACK_TAGS) if xbrl_text else {}

        filing_data = {
            "formType": form,
            "filingDate": filing_dates[i],
            "filingUrl": f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number.replace('-', '')}/{primary_documents[i]}",
            "xbrlUrl": xbrl_url if xbrl_url else "XBRL file not found.",
            "extracted": extracted_data
        }

        if form in ["10-K", "20-F"]:
            historical_annuals.append(filing_data)
        elif form in ["10-Q", "6-K"]:
            historical_quarters.append(filing_data)

    return {
        "company": data.get("name", "Unknown"),
        "cik": cik,
        "historical_annuals": historical_annuals,
        "historical_quarters": historical_quarters
    }

def find_instance_xbrl_url(index_data, cik, accession):
    acc_no = accession.replace('-', '')
    for file in index_data.get("directory", {}).get("item", []):
        print(f"🔍 Inspecting file: {file['name']}")
        filename = file['name'].lower()
        if filename.endswith(".xml") and '_def' not in filename and '_pre' not in filename and '_lab' not in filename and '_cal' not in filename:
            return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no}/{file['name']}"
    return None

@app.route("/resolve_cik", methods=["GET"])
def resolve_cik():
    company = request.args.get("company", "")
    if not company:
        return jsonify({"error": "Missing 'company' query parameter"}), 400

    try:
        url = "https://www.sec.gov/files/company_tickers.json"
        res = requests.get(url, headers=HEADERS)
        res.raise_for_status()
        tickers = res.json()
        for entry in tickers.values():
            if company.lower() in entry["title"].lower():
                return jsonify({"cik": str(entry["cik_str"]).zfill(10)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"error": f"CIK not found for company: {company}"}), 404

if __name__ == "__main__":
    app.run(debug=True)
