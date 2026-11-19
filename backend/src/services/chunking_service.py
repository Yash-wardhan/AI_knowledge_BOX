
import tiktoken

CHUNK_SIZE = 500
CHUNK_OVERLAP = 75

encoding = tiktoken.encoding_for_model("text-embedding-3-small")


def split_text_into_chunks(text: str) -> list[str]:
    if not text or not text.strip():
        return []

    tokens = encoding.encode(text)

    chunks = []
    start = 0

    while start < len(tokens):
        end = start + CHUNK_SIZE

        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens).strip()

        if chunk_text:
            chunks.append(chunk_text)

        if end >= len(tokens):
            break

        start = end - CHUNK_OVERLAP

    return chunks