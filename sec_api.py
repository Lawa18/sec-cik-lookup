import requests
import time
import os
import lxml.etree as ET
import yaml
from flask import Flask, request, jsonify

app = Flask(__name__)

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
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(delay)
    raise Exception(f"Failed to fetch URL after {retries} attempts: {url}")

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
    return extracted

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
