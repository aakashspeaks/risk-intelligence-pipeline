"""Find the pages where PyMuPDF and pdfplumber disagree most on word count."""
import pdfplumber
import pymupdf

PDF = "data/raw/VestasAnnualReport2025.pdf"

doc = pymupdf.open(PDF)
rows = []
with pdfplumber.open(PDF) as pdf:
    for number, (fitz_page, plumber_page) in enumerate(zip(doc, pdf.pages), start=1):
        a = len(fitz_page.get_text("words"))
        b = len(plumber_page.extract_words())
        rows.append((abs(a - b), number, a, b))

rows.sort(reverse=True)
print("page | PyMuPDF | pdfplumber | difference")
for diff, number, a, b in rows[:10]:
    print(f"{number:4d} | {a:7d} | {b:10d} | {diff}")
print("pages with identical counts:", sum(1 for r in rows if r[0] == 0), "of", len(rows))