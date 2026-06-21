import os
import glob
from pathlib import Path
import json
import csv

def inspect_mh():
    mh_dir = r"C:\Users\Syed Hasaan Shah\.gemini\antigravity-ide\brain\36299a47-8a4d-4141-81b0-539269dfb95d\scratch\MHDetection"
    path = Path(mh_dir)
    if not path.exists():
        print("Not cloned yet.")
        return
        
    print("Files in MHDetection:")
    files = list(path.rglob("*"))
    for f in files:
        if f.is_file() and ".git" not in str(f):
            print(f.relative_to(path))
            
    print("\nInspecting CSV/JSON files:")
    for ext in ["*.json", "*.csv", "*.txt"]:
        for f in path.rglob(ext):
            if ".git" in str(f): continue
            print(f"\n--- {f.name} ---")
            try:
                if f.suffix == ".json":
                    data = json.loads(f.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        print(f"List of {len(data)} items.")
                        if data: print(list(data[0].keys()))
                    else:
                        print("Dict keys:", list(data.keys())[:10])
                elif f.suffix == ".csv":
                    with open(f, "r", encoding="utf-8") as csvfile:
                        reader = csv.reader(csvfile)
                        headers = next(reader)
                        print(f"CSV Headers: {headers}")
                        count = sum(1 for row in reader)
                        print(f"Rows: {count}")
            except Exception as e:
                print(f"Error reading: {e}")

if __name__ == "__main__":
    inspect_mh()
