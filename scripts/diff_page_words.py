"""Show the words that only one parser sees on a given page."""
import sys
from collections import Counter

import pdfplumber
import pymupdf

PDF = "data/raw/VestasAnnualReport2025.pdf"
page_number = int(sys.argv[1])

fitz_words = Counter(w[4] for w in pymupdf.open(PDF)[page_number - 1].get_text("words"))
with pdfplumber.open(PDF) as pdf:
    plumber_words = Counter(w["text"] for w in pdf.pages[page_number - 1].extract_words())

only_plumber = plumber_words - fitz_words
only_fitz = fitz_words - plumber_words

print(f"Page {page_number}")
print("Only pdfplumber:", sum(only_plumber.values()), list(only_plumber.items())[:25])
print("Only PyMuPDF:   ", sum(only_fitz.values()), list(only_fitz.items())[:25])