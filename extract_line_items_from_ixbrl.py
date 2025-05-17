from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

def extract_line_items_from_ixbrl(htm_text, fallback_tags):
    soup = BeautifulSoup(htm_text, "lxml")
    extracted = {}

    for metric, tag_list in fallback_tags.items():
        found = False
        for tag_name in tag_list:
            candidates = soup.find_all(attrs={"name": True}, limit=1000)
            for tag in candidates:
                try:
                    name_attr = tag.attrs.get("name", "")
                    if name_attr and tag_name.lower() in name_attr.lower():
                        val = tag.text.strip().replace(",", "").replace("(", "-").replace(")", "")
                        extracted[metric] = float(val) if val.replace(".", "", 1).isdigit() else val
                        found = True
                        break
                except Exception as e:
                    continue
            if found:
                break
        if not found:
            extracted[metric] = "Missing tag"

    print(f"📊 Extracted {len(extracted)} iXBRL metrics.")
    return extracted
