import pdfplumber

PDF = "data/raw/VestasAnnualReport2025.pdf"

with pdfplumber.open(PDF) as pdf:
    page = pdf.pages[50]
    variants = {
        "default": page.extract_words(),
        "with extra_attrs=size": page.extract_words(extra_attrs=["size"]),
    }

for name, words in variants.items():
    print(f"--- {name} ({len(words)} words) ---")
    for w in words:
        text = w["text"]
        if "increase" in text or text.startswith("risks,"):
            hidden = [hex(ord(c)) for c in text if not c.isascii()]
            print(f"  {text!r}  x={w['x0']:.0f}..{w['x1']:.0f}  top={w['top']:.0f}  non-ascii={hidden}")