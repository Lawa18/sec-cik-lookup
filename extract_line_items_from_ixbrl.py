from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

def extract_line_items_from_ixbrl(htm_text, fallback_tags):
    soup = BeautifulSoup(htm_text, "lxml")
    extracted = {}

    ix_elements = soup.find_all(True)  # find all tags once (shallow and memory-safe)

    for metric, tag_list in fallback_tags.items():
        found = False
        for tag_name in tag_list:
            for tag in ix_elements:
                if tag.name.lower() in ["ix:nonfraction", "ix:nonnumeric"]:
                    name = tag.get("name", "")
                    if name and tag_name.lower() in name.lower():
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
