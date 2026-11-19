from services.chunking_service import split_text_into_chunks


def test_empty_text():
    assert split_text_into_chunks("") == []


def test_short_text():
    text = "FastAPI is a Python framework."
    chunks = split_text_into_chunks(text)

    assert len(chunks) == 1
    assert chunks[0] == text


def test_long_text():
    text = "FastAPI is a Python framework. " * 200
    chunks = split_text_into_chunks(text)

    assert len(chunks) > 1