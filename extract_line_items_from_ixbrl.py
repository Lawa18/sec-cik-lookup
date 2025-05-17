from bs4 import BeautifulSoup
import warnings

def extract_line_items_from_ixbrl(htm_text, fallback_tags):
    # Use robust HTML parser instead of lxml (to prevent crashes)
    soup = BeautifulSoup(htm_text, "html.parser")

    extracted = {}

    for metric, tag_names in fallback_tags.items():
        found = False
        for tag in soup.find_all(True):  # True returns all tags
            if tag.name and tag.name.lower() in ["ix:nonfraction", "ix:nonnumeric"]:
                tag_name_attr = tag.get("name", "").lower()
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
