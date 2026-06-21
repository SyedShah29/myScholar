import os
import json
import time
from groq import Groq
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com")

def generate_duas():
    duas = []
    # 25 * 6 = 150 duas
    for i in range(6):
        print(f"Generating Duas batch {i+1}/6...")
        
        PROMPT = f"""You are an expert Islamic scholar compiling 'Hisn al-Muslim' (Fortress of the Muslim).
Generate an array of 25 highly authentic daily Duas in JSON format. 
This is batch {i+1}. DO NOT repeat duas from previous batches. Include diverse contexts (e.g., anxiety, travel, eating, sleeping, waking, morning, evening, sickness, studying, decision making).

The output MUST be a valid JSON array of objects exactly like this:
[
  {{
    "id": "dua_gen_b{i}_0",
    "context": "When feeling anxious or stressed",
    "arabic": "اللَّهُمَّ إِنِّي أَعُوذُ بِكَ مِنَ الْهَمِّ وَالْحَزَنِ...",
    "transliteration": "Allahumma inni a'udhu bika minal-hammi wal-hazan...",
    "text": "O Allah, I seek refuge in You from anxiety and sorrow...",
    "source": "Sahih Bukhari 2893"
  }}
]

ONLY output the raw JSON array. No markdown formatting, no backticks, no explanations. Just [{{...}}]"""

        content = ""
        try:
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": PROMPT}],
                model="llama-3.3-70b-versatile",
                temperature=0.7,
                max_tokens=6000
            )
            
            content = response.choices[0].message.content.strip()
            
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
                
            batch = json.loads(content.strip())
            
            for idx, d in enumerate(batch):
                d['id'] = f"dua_gen_b{i}_{idx}"
                
            duas.extend(batch)
            print(f"Successfully added {len(batch)} duas. Total: {len(duas)}")
            
        except Exception as e:
            print(f"Failed to parse batch {i+1}: {e}")
            print(f"Raw output: {content[:100]}...")
        
        time.sleep(2)
        
    output_path = Path("app/data/duas.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"duas": duas}, f, ensure_ascii=False, indent=2)
        
    print(f"Saved {len(duas)} duas to {output_path}")

if __name__ == "__main__":
    generate_duas()
