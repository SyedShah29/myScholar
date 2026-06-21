import os
import json
from pathlib import Path

def analyze_repo(repo_path, glob_pattern="**/*.json"):
    print(f"\n=== Inspecting {repo_path} ===")
    path = Path(repo_path)
    if not path.exists():
        print("Not cloned yet.")
        return
        
    for p in path.glob(glob_pattern):
        if "node_modules" in str(p) or ".git" in str(p):
            continue
        print(f"\nFile: {p.name}")
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    print(f"Type: List of {len(data)} items.")
                    if len(data) > 0:
                        print(f"Sample keys: {list(data[0].keys())}")
                elif isinstance(data, dict):
                    print(f"Type: Dict with {len(data.keys())} keys.")
                    print(f"Keys: {list(data.keys())[:10]}")
        except Exception as e:
            print(f"Could not read JSON: {e}")

if __name__ == "__main__":
    scratch_dir = r"C:\Users\Syed Hasaan Shah\.gemini\antigravity-ide\brain\36299a47-8a4d-4141-81b0-539269dfb95d\scratch"
    analyze_repo(os.path.join(scratch_dir, "fitrahive"))
    analyze_repo(os.path.join(scratch_dir, "kindunes"))
    analyze_repo(os.path.join(scratch_dir, "khalidhussain"))
