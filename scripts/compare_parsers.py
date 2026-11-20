"""Compare PyMuPDF and pdfplumber: speed and word counts on the whole report."""
import time

import pdfplumber
import pymupdf

PDF = "data/raw/VestasAnnualReport2025.pdf"

start = time.time()
doc = pymupdf.open(PDF)
n_fitz = sum(len(page.get_text("words")) for page in doc)
print(f"PyMuPDF    {n_fitz} words  {time.time() - start:.1f} s")

start = time.time()
n_plumber = 0
with pdfplumber.open(PDF) as pdf:
    for page in pdf.pages:
        n_plumber += len(page.extract_words())
print(f"pdfplumber {n_plumber} words  {time.time() - start:.1f} s")