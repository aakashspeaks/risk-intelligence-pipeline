from risk_intel.stage1_document.layout import classify, count_columns


def word(x0, x1, top):
    return {"x0": x0, "x1": x1, "top": top, "text": "word"}


def test_classify_each_type():
    assert classify(10, 0, 0, 0.0) == "graphic"
    assert classify(300, 1, 5, 0.5) == "numeric_table"
    assert classify(300, 1, 10, 0.1) == "table_or_matrix"
    assert classify(300, 3, 0, 0.0) == "multi_column"
    assert classify(300, 2, 0, 0.0) == "two_column"
    assert classify(300, 1, 0, 0.0) == "single_block"


def test_count_two_columns():
    words = []
    for j in range(20):
        top = 100 + j * 10
        words += [word(40, 150, top), word(160, 300, top),   # left column
                  word(340, 450, top), word(460, 600, top)]  # right column
    assert count_columns(words, 842) == 2


def test_too_few_words_means_zero_columns():
    assert count_columns([word(40, 100, 100)], 842) == 0