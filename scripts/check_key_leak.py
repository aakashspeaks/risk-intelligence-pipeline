import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
key = os.environ.get("OPENAI_API_KEY", "")
print("key loaded:", bool(key), "| length:", len(key))   # never prints the key itself
if len(key) < 10:
    raise SystemExit("No usable key loaded, so this search would be meaningless")

SKIP = {".venv", ".git", ".pytest_cache", "__pycache__"}
hits = []
for path in Path(".").rglob("*"):
    if not path.is_file() or path.name == ".env" or SKIP & set(path.parts):
        continue
    try:
        if key in path.read_text(errors="ignore"):
            hits.append(str(path))
    except OSError:
        pass
print("files containing the key:", hits or "none")