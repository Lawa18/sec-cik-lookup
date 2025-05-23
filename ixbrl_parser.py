from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings

def parse_ixbrl_and_extract(htm_text, fallback_tags):
    print("🧪 ENTERED parse_ixbrl_and_extract()")

    if htm_text is None:
        print("❌ htm_text is None")
        return {"error": "htm_text is None"}

    if not isinstance(htm_text, str):
        print(f"❌ htm_text is not str — got {type(htm_text)}")
        return {"error": f"htm_text is not a string — got {type(htm_text)}"}

    if len(htm_text) < 10000:
        print(f"❌ htm_text too short — len={len(htm_text)}")
        return {"error": f"htm_text too short: {len(htm_text)}"}

    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

    soup = None
    try:
        print("🔍 Parsing iXBRL with html5lib...")
        soup = BeautifulSoup(htm_text, "html5lib")
        print("✅ html5lib parse successful")
    except Exception as e1:
        print(f"⚠️ html5lib failed: {e1}")
        try:
            print("🔁 Fallback: Parsing with html.parser...")
            soup = BeautifulSoup(htm_text, "html.parser")
            print("✅ html.parser fallback successful")
        except Exception as e2:
            print(f"❌ html.parser fallback also failed: {e2}")
            return {"error": "Soup parse failed for both html5lib and html.parser"}

    extracted = {}

    for metric, tag_names in fallback_tags.items():
        found = False

        for tag in soup.find_all(name=lambda x: x and "non" in x.lower()):
            if not hasattr(tag, "get"):
                print(f"⚠️ Skipping non-Tag element: {tag}")
                continue

            try:
                name_attr = tag.get("name", "").lower()
            except Exception as e:
                print(f"⚠️ tag.get('name') failed: {e}")
                continue

            if not name_attr:
                continue

            print(f"🔍 Tag found: <{tag.name}> with name='{name_attr}'")

            for fallback_tag in tag_names:
                if fallback_tag.lower() in name_attr:
                    text = tag.get_text(strip=True)
                    text = text.replace(",", "").replace("(", "-").replace(")", "")
                    try:
                        extracted[metric] = float(text)
                    except ValueError:
                        extracted[metric] = text
                    found = True
                    break

            if found:
                break

        if not found:
            extracted[metric] = "Missing tag"

    print(f"📊 Extracted {len(extracted)} iXBRL metrics.")
    return extracted
