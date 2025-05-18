import requests
import time
import os
import lxml.etree as ET
import yaml
import re
from ixbrl_parser import parse_ixbrl_metrics  # ✅ updated import

HEADERS = {
    'User-Agent': 'Lars Wallin (lars.e.wallin@gmail.com)',
    'Accept-Encoding': 'gzip, deflate',
    'Accept': '*/*',
    'Connection': 'keep-alive'
}

SEC_API_BASE = 'https://data.sec.gov'

# ... [no changes to the rest of the file until get_sec_financials]

def get_sec_financials(cik):
    assert callable(parse_ixbrl_metrics), "❌ parse_ixbrl_metrics is not callable"  # ✅ defense

    data = fetch_sec_data(cik)
    if not data:
        return {
            "company": "Unknown",
            "cik": cik,
            "historical_annuals": [],
            "historical_quarters": []
        }

    filings = data.get("filings", {}).get("recent", {})
    combined = list(zip(
        filings.get("form", []),
        filings.get("filingDate", []),
        filings.get("accessionNumber", []),
        filings.get("primaryDocument", [])
    ))

    combined.sort(key=lambda x: x[1], reverse=True)
    fallback_tags = load_fallback_tags()
    all_annuals = []

    for form, filing_date, accession_number, doc in combined:
        if form not in ["10-K", "20-F"]:
            continue

        print(f"📄 Checking {form} filed on {filing_date}")
        index_data = get_filing_index(cik, accession_number)
        xbrl_url = find_xbrl_url(index_data)

        xbrl_text = None
        parsed_items = {}

        if xbrl_url and xbrl_url.endswith(".xml"):
            xbrl_text = safe_get(xbrl_url).text
            parsed_items = extract_line_items(xbrl_text, fallback_tags)

        elif doc.endswith(".htm") or doc.endswith(".html"):
            htm_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number.replace('-', '')}/{doc}"
            print(f"🌐 Using iXBRL HTML: {htm_url}")
            htm_text = safe_get(htm_url).text
            xbrl_text = htm_text

            parsed_items = parse_ixbrl_metrics(htm_text, fallback_tags)  # ✅ updated usage

        fiscal_year = get_fiscal_year_from_xbrl(xbrl_text or "")
        print(f"🗓️ Fiscal Year Detected: {fiscal_year}")

        all_annuals.append({
            "formType": form,
            "filingDate": filing_date,
            "fiscalYear": fiscal_year,
            "filingUrl": f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number.replace('-', '')}/{doc}",
            "xbrlUrl": xbrl_url,
            "xbrl_text": xbrl_text,
            "extracted": parsed_items
        })

    historical_annuals = sorted(
        [f for f in all_annuals if f["fiscalYear"]],
        key=lambda x: x["fiscalYear"],
        reverse=True
    )[:1]

    print("🔍 Extracted values for debugging:")
    for filing in historical_annuals:
        print(f"\n🗂️ Filing: {filing['filingDate']} – Form {filing['formType']}")
        for k, v in filing["extracted"].items():
            print(f"{k}: {v}")

    return {
        "company": data.get("name", "Unknown"),
        "cik": cik,
        "historical_annuals": historical_annuals,
        "historical_quarters": []
    }

# ... [rest of sec_api.py unchanged]

def get_company_sic_info(cik):
    cik = cik.zfill(10)
    url = f"{SEC_API_BASE}/submissions/CIK{cik}.json"
    data = safe_get(url).json()
    sic = data.get("companyInfo", {}).get("sic")
    description = data.get("companyInfo", {}).get("sicDescription")
    return sic, description

def download_multiple_xbrl(cik, save_dir='xbrl_files'):
    os.makedirs(save_dir, exist_ok=True)
    filings = fetch_sec_data(cik).get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    accession_numbers = filings.get("accessionNumber", [])
    filing_dates = filings.get("filingDate", [])

    downloaded_files = []
    for i, form in enumerate(forms):
        if form not in ["10-K", "10-Q", "20-F"]:
            continue
        acc = accession_numbers[i]
        date = filing_dates[i]
        index_data = get_filing_index(cik, acc)
        xbrl_url = find_xbrl_url(index_data)
        if xbrl_url:
            response = safe_get(xbrl_url)
            filename = f"{cik}_{form}_{date}.xml"
            filepath = os.path.join(save_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(response.text)
            downloaded_files.append(filepath)
    return downloaded_files
