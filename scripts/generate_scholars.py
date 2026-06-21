import os
import json
import time
import re
from groq import Groq
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com")

def generate_quotes():
    quotes = []
    # 25 * 20 = 500 quotes
    for i in range(20):
        print(f"Generating batch {i+1}/20...")
        
        PROMPT = f"""You are an expert Islamic scholar. Generate an array of 25 highly authentic, famous classical Islamic quotes in JSON format. 
This is batch {i+1}. DO NOT repeat quotes from previous batches. Keep quotes profound and diverse.
Include classical scholars like Al-Ghazali, Ibn Taymiyyah, Ibn al-Qayyim, Imam Nawawi, Imam Abu Hanifa, Imam Malik, Imam Shafi'i, Ahmad bin Hanbal, Ibn Kathir, Al-Razi.

The output MUST be a valid JSON array of objects exactly like this:
[
  {{
    "id": "batch{i}_idx0",
    "scholar": "Imam Al-Ghazali",
    "died": "1111 CE",
    "school": "Shafi'i",
    "text": "Knowledge without action is vanity...",
    "arabic": "العلم بلا عمل...",
    "source": "Ihya Ulum al-Din",
    "topics": ["knowledge", "action"]
  }}
]

ONLY output the raw JSON array. No markdown formatting, no backticks, no explanations. Just [{{...}}]"""

        content = ""
        try:
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": PROMPT}],
                model="llama-3.3-70b-versatile",
                temperature=0.8,
                max_tokens=6000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean up potential markdown
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
                
            batch = json.loads(content.strip())
            
            # Auto-assign unique IDs if LLM messed up
            for idx, q in enumerate(batch):
                q['id'] = f"gen_b{i}_{idx}"
                
            quotes.extend(batch)
            print(f"Successfully added {len(batch)} quotes. Total: {len(quotes)}")
            
        except Exception as e:
            print(f"Failed to parse batch {i+1}: {e}")
            print(f"Raw output: {content[:100]}...")
        
        time.sleep(2)  # Respect rate limits
        
    output_path = Path("app/data/scholars.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"scholars": quotes}, f, ensure_ascii=False, indent=2)
        
    print(f"Saved {len(quotes)} quotes to {output_path}")

if __name__ == "__main__":
    generate_quotes()
