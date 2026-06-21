import httpx
import json
from pathlib import Path

def fetch_and_convert_hisn():
    print("Downloading Hisn Al-Muslim API...")
    url = "https://raw.githubusercontent.com/wafaaelmaandy/Hisn-Muslim-Json/master/husn_en.json"
    data = httpx.get(url).json()
    
    categories = data.get("English", [])
    
    # Load existing generated duas
    duas_file = Path("app/data/duas.json")
    existing_duas = []
    if duas_file.exists():
        raw = json.loads(duas_file.read_text(encoding="utf-8"))
        existing_duas = raw.get("duas", [])
        
    print(f"Loaded {len(existing_duas)} existing generated duas.")
    
    new_duas = []
    for cat in categories:
        title = cat.get("TITLE", "")
        for item in cat.get("TEXT", []):
            arabic = item.get("ARABIC_TEXT", "")
            english = item.get("TRANSLATED_TEXT", "")
            source = item.get("LANGUAGE_ARABIC_TRANSLATED_TEXT", "")
            
            new_duas.append({
                "id": f"hisn_api_{item.get('ID', len(new_duas))}",
                "context": title,
                "arabic": arabic,
                "transliteration": "", # Not provided by this API
                "text": english,
                "source": source
            })
            
    print(f"Extracted {len(new_duas)} duas from API.")
    
    # Combine them
    combined = existing_duas + new_duas
    
    # Deduplicate by ID
    seen = set()
    unique_duas = []
    for d in combined:
        if d['id'] not in seen:
            seen.add(d['id'])
            unique_duas.append(d)
            
    duas_file.write_text(json.dumps({"duas": unique_duas}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(unique_duas)} total duas to {duas_file}")

if __name__ == "__main__":
    fetch_and_convert_hisn()
