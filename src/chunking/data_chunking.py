import nltk
import json
from tqdm import tqdm
nltk.download('punkt', quiet=True)
from nltk.tokenize import sent_tokenize

def sentence_chunk_text(text, max_chars=2000):
    """Split text into sentence-based chunks (≈2000 chars each)."""
    sentences = sent_tokenize(text)
    chunks, current = [], ""

    for s in sentences:
        if len(current) + len(s) <= max_chars:
            current += " " + s
        else:
            chunks.append(current.strip())
            current = s
    if current:
        chunks.append(current.strip())
    return chunks

def process_jsonl_files(filenames, chunk_size=2000):
    data = []

    for filename in tqdm(filenames, desc="Processing files"):
        with open(filename, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in tqdm(lines, desc=f"Chunking {filename}", leave=False):
            entry = json.loads(line)
            text = entry["page_content"]
            source = entry["source"]
            page_index = entry["page_index"]

            for i, chunk in enumerate(sentence_chunk_text(text, chunk_size)):
                data.append({
                    "source": source,
                    "page_index": page_index,
                    "chunk_id": i,
                    "text": chunk
                })
    return data


filenames = [
    "barnard_2024_2025.jsonl",
    "columbia_college_2024_2025.jsonl",
    "columbia_engineering_2024_2025.jsonl"
]
chunked_data = process_jsonl_files(filenames, chunk_size=300)

# Save to JSONL for embedding later
with open("chunked_bulletins.jsonl", "w", encoding="utf-8") as f:
    for record in chunked_data:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
