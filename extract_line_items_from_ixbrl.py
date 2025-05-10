from bs4 import BeautifulSoup

def extract_line_items_from_ixbrl(htm_text, fallback_tags):
    soup = BeautifulSoup(htm_text, "lxml")
    extracted = {}

    for metric, tag_list in fallback_tags.items():
        found = False
        for tag in tag_list:
            tag_name = tag.split(":")[-1]

            elements = soup.find_all(["ix:nonfraction", "ix:nonnumeric"], {"name": True})
            for el in elements:
                if el.get("name", "").lower().endswith(tag_name.lower()):
                    try:
                        value = el.text.replace(",", "").replace("(", "-").replace(")", "").strip()
                        extracted[metric] = float(value)
                    except:
                        extracted[metric] = el.text.strip()
                    found = True
                    break
            if found:
                break
        if not found:
            extracted[metric] = "Missing tag"

    return extracted
