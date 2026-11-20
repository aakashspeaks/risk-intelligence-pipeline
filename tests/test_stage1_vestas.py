import pytest

from risk_intel.config import RAW_DIR
from risk_intel.stage1_document import read_document

PDF = RAW_DIR / "VestasAnnualReport2025.pdf"
pytestmark = pytest.mark.skipif(not PDF.exists(), reason="put the PDF in data/raw/")


@pytest.fixture(scope="module")
def doc():
    return read_document(PDF)  # reads all 195 pages once, shared by every test below


def page(doc, n):
    return doc.pages[n - 1]


def test_page_count_and_numbering(doc):
    assert doc.n_pages == 195
    assert [p.page_number for p in doc.pages] == list(range(1, 196))


def test_risk_management_opening_page(doc):
    p = page(doc, 50)
    assert p.title == "Risk management"
    assert p.part == "Our business"


def test_risk_matrix_page(doc):
    p = page(doc, 51)
    assert p.layout_type == "table_or_matrix"
    assert p.title == "Main risks"
    assert p.part == "Our business"
    assert "Risk management" in p.section


def test_sustainability_table_pages(doc):
    for n in (71, 72, 73, 74):
        assert page(doc, n).layout_type == "table_or_matrix"
    assert page(doc, 71).part == "Sustainability statement"
    assert page(doc, 71).title.startswith("Material impacts")


def test_cyber_page(doc):
    p = page(doc, 118)
    assert p.title == "Cyber security"
    assert p.part == "Sustainability statement"


def test_menu_not_in_body_text(doc):
    assert "Auditor and management statements" not in page(doc, 51).text


def test_most_pages_have_text_layer(doc):
    with_text = sum(p.has_text_layer for p in doc.pages)
    assert with_text / doc.n_pages > 0.9


def test_sections_cover_every_page(doc):
    covered = sum(s.end_page - s.start_page + 1 for s in doc.sections)
    assert covered == doc.n_pages