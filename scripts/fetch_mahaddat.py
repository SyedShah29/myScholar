import httpx
from pathlib import Path

def fetch_mahaddat():
    print("Fetching MAHADDAT dataset as raw bytes...")
    url = "https://raw.githubusercontent.com/KamelGaanoun/MHDetection/main/MAHADDAT/MAHADDAT.csv"
    
    with httpx.Client(timeout=30.0) as client:
        r = client.get(url)
        r.raise_for_status()
        
    Path("app/data/MAHADDAT.csv").write_bytes(r.content)
    print("Saved to app/data/MAHADDAT.csv")

if __name__ == "__main__":
    fetch_mahaddat()
