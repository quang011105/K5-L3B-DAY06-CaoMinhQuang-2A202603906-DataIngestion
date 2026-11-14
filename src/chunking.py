"""Traceable character windows and sentence/line-aware chunks."""
import hashlib
import re


def chunk_page(page, size=1000, overlap=100, structure=False):
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("Invalid chunk size/overlap")
    text = page["text"]
    boundaries = {m.end() for m in re.finditer(r"\n\s*\n|[.!?](?=\s+[A-Z])|(?m:^[^\n]{1,85}\n)", text)}
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if structure and end < len(text):
            end = max((b for b in boundaries if start + size//3 <= b <= end), default=end)
        body = text[start:end]
        method = "sentence_line_aware" if structure else "fixed"
        identity = f"{page['document_id']}:{page['page']}:{method}:{size}:{overlap}:{start}:{end}:{body}"
        if body.strip():
            chunks.append({"chunk_id": hashlib.sha256(identity.encode()).hexdigest(), "text": body,
                           "metadata": {**page["metadata"], "document_id": page["document_id"],
                                        "source": page["source"], "page": page["page"],
                                        "start_char": start, "end_char": end, "chunking": method}})
        if end == len(text):
            break
        start = end if structure else end-overlap
    return chunks
