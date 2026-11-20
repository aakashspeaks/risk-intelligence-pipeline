import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
key = os.environ.get("OPENAI_API_KEY")
model = os.environ.get("RISK_LLM_MODEL")
print("key set:", bool(key), "| model:", model)   # prints True or False, never the key itself
if not key or not model:
    raise SystemExit("Set OPENAI_API_KEY and RISK_LLM_MODEL in the .env file")

client = OpenAI()
response = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "Reply with the single word: ready"}],
)
print("reply:", response.choices[0].message.content)