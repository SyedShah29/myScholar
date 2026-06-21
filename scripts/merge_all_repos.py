import os
import json
import re
from pathlib import Path

def normalize_arabic(text: str) -> str:
    if not text:
        return ""
    # Remove all diacritics (tashkeel)
    text = re.sub(r'[\u0617-\u061A\u064B-\u0652]', '', text)
    # Normalize alef
    text = re.sub(r'[إأآا]', 'ا', text)
    # Remove punctuation
    text = re.sub(r'[^\w\s]', '', text)
    return text.replace(" ", "").strip()

def extract_from_fitrahive(scratch_dir: Path) -> list:
    duas = []
    fitrahive = scratch_dir / "fitrahive"
    if not fitrahive.exists(): return []
    
    for p in fitrahive.rglob("*.json"):
        if p.name not in ["en.json"]: continue
        if "node_modules" in str(p): continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        duas.append({
                            "arabic": item.get("arabic", ""),
                            "transliteration": item.get("latin", ""),
                            "text": item.get("translation", ""),
                            "context": item.get("title", ""),
                            "source": item.get("source", "")
                        })
        except:
            pass
    return duas

def merge_duas():
    base_file = Path("app/data/duas.json")
    scratch_dir = Path("C:/Users/Syed Hasaan Shah/.gemini/antigravity-ide/brain/36299a47-8a4d-4141-81b0-539269dfb95d/scratch")
    
    # 1. Load existing
    existing = []
    if base_file.exists():
        existing = json.loads(base_file.read_text(encoding="utf-8")).get("duas", [])
        
    print(f"Loaded {len(existing)} existing duas.")
    
    # Map normalized arabic to existing item
    arabic_map = {normalize_arabic(d.get("arabic", "")): d for d in existing if d.get("arabic")}
    text_map = {d.get("text", "").lower().strip(): d for d in existing if d.get("text")}
    
    # 2. Extract fitrahive
    fitrahive_duas = extract_from_fitrahive(scratch_dir)
    print(f"Extracted {len(fitrahive_duas)} duas from fitrahive.")
    
    merged_count = 0
    added_count = 0
    
    for fd in fitrahive_duas:
        if not fd["arabic"] and not fd["text"]:
            continue
            
        norm_ar = normalize_arabic(fd["arabic"])
        norm_en = fd["text"].lower().strip()
        
        target = None
        if norm_ar and norm_ar in arabic_map:
            target = arabic_map[norm_ar]
        elif norm_en and norm_en in text_map:
            target = text_map[norm_en]
            
        if target:
            # Merge transliteration if missing
            if not target.get("transliteration") and fd.get("transliteration"):
                target["transliteration"] = fd["transliteration"]
                merged_count += 1
        else:
            # New dua
            new_dua = {
                "id": f"merged_dua_{len(existing) + added_count}",
                "context": fd["context"],
                "arabic": fd["arabic"],
                "transliteration": fd["transliteration"],
                "text": fd["text"],
                "source": fd["source"]
            }
            existing.append(new_dua)
            if norm_ar: arabic_map[norm_ar] = new_dua
            if norm_en: text_map[norm_en] = new_dua
            added_count += 1
            
    print(f"Merged fields for {merged_count} existing duas.")
    print(f"Added {added_count} completely new duas.")
    print(f"Total duas: {len(existing)}")
    
    base_file.write_text(json.dumps({"duas": existing}, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    merge_duas()
