from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

def extract_line_items_from_ixbrl(htm_text, fallback_tags):
    try:
        soup = BeautifulSoup(htm_text, "lxml")
    except Exception as e:
        print(f"⚠️ LXML failed, retrying with html.parser: {e}")
        soup = BeautifulSoup(htm_text, "html.parser")

    extracted = {}
    for metric, tag_names in fallback_tags.items():
        found = False
        for tag in soup.find_all(["ix:nonfraction", "ix:nonnumeric"]):
            if not hasattr(tag, "attrs") or "name" not in tag.attrs:
                continue

            tag_name_attr = tag["name"].lower()
            for fallback_tag in tag_names:
                if fallback_tag.lower() in tag_name_attr:
                    val = tag.get_text(strip=True).replace(",", "").replace("(", "-").replace(")", "")
                    try:
                        extracted[metric] = float(val) if val.replace(".", "", 1).isdigit() else val
                    except:
                        extracted[metric] = val
                    found = True
                    break
            if found:
                break
        if not found:
            extracted[metric] = "Missing tag"

    print(f"📊 Extracted {len(extracted)} iXBRL metrics.")
    return extracted
