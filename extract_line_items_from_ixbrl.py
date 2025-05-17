from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

def extract_line_items_from_ixbrl(htm_text, fallback_tags):
    soup = BeautifulSoup(htm_text, "lxml")
    extracted = {}

    for metric, tag_names in fallback_tags.items():
        found = False
        for tag in soup.descendants:
            if not hasattr(tag, "name"):
                continue
            tagname = tag.name.lower()
            if tagname not in ["ix:nonfraction", "ix:nonnumeric"]:
                continue

            name_attr = tag.get("name", "").lower()
            for fallback in tag_names:
                if fallback.lower() in name_attr:
                    try:
                        val = tag.text.strip().replace(",", "").replace("(", "-").replace(")", "")
                        extracted[metric] = float(val) if val.replace(".", "", 1).isdigit() else val
                        found = True
                        break
                    except Exception:
                        continue
            if found:
                break

        if not found:
            extracted[metric] = "Missing tag"

    print(f"📊 Extracted {len(extracted)} iXBRL metrics.")
    return extracted
