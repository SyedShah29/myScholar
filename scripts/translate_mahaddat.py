import json
import csv
import time
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv
import os

def translate_mahaddat():
    load_dotenv()
    print("Starting translation of MAHADDAT...")
    csv_file = Path("app/data/MAHADDAT.csv")
    out_file = Path("app/data/translated_mahaddat.json")
    
    if not csv_file.exists():
        print("MAHADDAT.csv not found.")
        return
        
    client = Groq(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com")
    
    # Load existing to resume
    translated = []
    if out_file.exists():
        translated = json.loads(out_file.read_text(encoding="utf-8")).get("fabricated_hadith", [])
        
    seen = {t["phrase"] for t in translated}
    
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
        # Headers: ['Book', 'No.', 'Full Hadith', 'Isnad', 'Matan', "Author's Comments", 'Degree', 'Authenticity', 'Topic']
        rows = list(reader)
        
    print(f"Total rows in CSV: {len(rows)}")
    print(f"Already translated: {len(translated)}")
    
    # Process batch
    # To avoid 12k TPM limits over 2400 rows, we will process 50 at a time, then sleep
    # Actually, we'll just process in small batches of 10.
    
    batch_size = 10
    system_prompt = """You are an expert Islamic hadith translator. Translate the following fabricated (Mawdu) Arabic hadith texts into English. 
You MUST NOT alter the meaning. Translate them as accurately as possible so they can be identified.
Return ONLY a valid JSON array of objects.
Each object must have exactly these keys:
"phrase": The English translation of the fabricated text (matan).
"correction": A short English explanation that this is a fabricated hadith (Mawdu').
"status": "fabricated"
"arabic": The original Arabic text.
Do NOT wrap in markdown blocks like ```json. Just raw JSON array."""

    try:
        for i in range(len(translated), len(rows), batch_size):
            batch = rows[i:i+batch_size]
            prompt = "Translate these Arabic fabricated hadiths to English:\n\n"
            for row in batch:
                arabic_matan = row[4] # Matan
                prompt += f"- {arabic_matan}\n"
                
            print(f"Processing batch {i} to {i+len(batch)}...")
            
            success = False
            retries = 3
            while not success and retries > 0:
                try:
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1
                    )
                    content = response.choices[0].message.content.strip()
                    if content.startswith("```json"): content = content[7:]
                    if content.endswith("```"): content = content[:-3]
                    
                    items = json.loads(content)
                    if isinstance(items, list):
                        translated.extend(items)
                        success = True
                        
                        # Save progress safely
                        out_file.write_text(json.dumps({"fabricated_hadith": translated}, indent=2, ensure_ascii=False), encoding="utf-8")
                    else:
                        print("Invalid JSON structure returned. Retrying...")
                        retries -= 1
                        time.sleep(2)
                except Exception as e:
                    print(f"API Error: {e}")
                    # If rate limit (429), sleep longer
                    if "429" in str(e):
                        print("Rate limit reached. Sleeping for 20 seconds...")
                        time.sleep(20)
                    else:
                        retries -= 1
                        time.sleep(5)
            
            if not success:
                print(f"Failed to process batch at {i} after retries.")
            
            # Sleep to respect rate limits (12k TPM)
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("Interrupted by user.")
        
    print(f"Finished. Total translated: {len(translated)}")

if __name__ == "__main__":
    translate_mahaddat()
