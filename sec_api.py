import requests
import time
import os
import lxml.etree as ET
import yaml
import re
import ixbrl_parser  # ✅ final import with module namespace

assert callable(ixbrl_parser.parse_ixbrl_and_extract), "❌ parse_ixbrl_and_extract is not callable"

HEADERS = {
    'User-Agent': 'Lars Wallin (lars.e.wallin@gmail.com)',
    'Accept-Encoding': 'gzip, deflate',
    'Accept': '*/*',
    'Connection': 'keep-alive'
}

SEC_API_BASE = 'https://data.sec.gov'

def safe_get(url, headers=HEADERS, retries=3, delay=1):
    for attempt in range(retries):
        try:
            print(f"🔗 Fetching: {url}")
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Attempt {attempt + 1} failed: {e}")
            time.sleep(delay)
    raise Exception(f"❌ Failed to fetch URL after {retries} attempts: {url}")

def fetch_sec_data(cik):
    sec_url = f"{SEC_API_BASE}/submissions/CIK{cik}.json"
    try:
        res = requests.get(sec_url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        return res.json()
    except requests.RequestException as e:
        print(f"❌ ERROR: Failed to fetch SEC data for CIK {cik}: {e}")
        return {}

def get_filing_index(cik, accession):
    acc_no_no_hyphens = accession.replace('-', '')
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_no_hyphens}/index.json"
    try:
        return safe_get(url).json()
    except Exception:
        fallback_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/index.json"
        return safe_get(fallback_url).json()

def find_xbrl_url(index_data):
    directory = index_data.get("directory", {})
    accession = directory.get("name", "")
    items = directory.get("item", [])
    acc_no = accession.replace("-", "")

    cik_fallback = directory.get("cik")
    if not cik_fallback:
        file_path = directory.get("file", "")
        cik_parts = file_path.split("/")
        cik_fallback = cik_parts[-3] if len(cik_parts) >= 3 else None

    if not cik_fallback:
        print("❌ Cannot determine CIK — directory['file'] is malformed or missing.")
        return None

    print(f"🔎 Searching for instance XML in accession: {accession}")

    for file in items:
        name = file["name"].lower()
        print(f"📁 Checking file: {name}")
        if name.endswith(".xml") and not any(bad in name for bad in ["_def", "_pre", "_lab", "_cal", "_sum", "schema"]):
            path = f"https://www.sec.gov/Archives/edgar/data/{int(cik_fallback)}/{acc_no}/{file['name']}"
            print(f"✅ Selected XBRL instance file: {path}")
            return path

    print("❌ No valid XBRL instance XML file found in filing.")
    return None

def load_fallback_tags(filepath="grouped_fallbacks.yaml"):
    try:
        with open(filepath, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ Failed to load fallback tags: {e}")
        return {}

def extract_line_items(xbrl_text, fallback_tags):
    extracted = {}
    try:
        root = ET.fromstring(xbrl_text.encode("utf-8"))
        for metric, tags in fallback_tags.items():
            for tag in tags:
                local_tag = tag.split(":")[-1]
                el = root.find(f".//{{*}}{local_tag}")
                if el is not None and el.text and el.text.strip():
                    try:
                        extracted[metric] = float(el.text.replace(",", "").replace("(", "-").replace(")", ""))
                    except:
                        extracted[metric] = el.text.strip()
                    break
            else:
                extracted[metric] = "Missing tag"
    except Exception as e:
        print(f"❌ XBRL Parse error: {e}")
    print(f"📊 Extracted {len(extracted)} metrics.")
    return extracted

def get_fiscal_year_from_xbrl(xbrl_text):
    match = re.search(r'<[^>]*DocumentPeriodEndDate[^>]*>(\d{4})-\d{2}-\d{2}</', xbrl_text)
    if match:
        return match.group(1)
    return None

def get_sec_financials(cik):
    assert callable(ixbrl_parser.parse_ixbrl_and_extract), "❌ parse_ixbrl_and_extract is not callable"

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
            parsed_items = ixbrl_parser.parse_ixbrl_and_extract(xbrl_text, fallback_tags)

        elif doc.endswith(".htm") or doc.endswith(".html"):
            htm_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number.replace('-', '')}/{doc}"
            print(f"🌐 Using iXBRL HTML: {htm_url}")
            htm_text = safe_get(htm_url).text
            xbrl_text = htm_text
            parsed_items = ixbrl_parser.parse_ixbrl_and_extract(htm_text, fallback_tags)

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
