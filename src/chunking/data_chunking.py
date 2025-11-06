import nltk
import json
from tqdm import tqdm

# Download NLTK sentence tokenizer if not already present
nltk.download('punkt', quiet=True)
from nltk.tokenize import sent_tokenize

def sentence_chunk_text(text, max_chars=300):
    """
    Split text into chunks <= max_chars.
    Tries to keep sentences intact, but splits long sentences on punctuation or
    forcibly at max_chars if needed.
    """
    import re
    # use nltk to split sentences semantically
    sentences = sent_tokenize(text)
    chunks, current = [], ""

    for s in sentences:
        # Split long sentences further on commas/semicolons
        parts = re.split(r'([,;])', s)
        for part in parts:
            part = part.strip()
            while len(part) > max_chars:
                # Hard split if part is too long
                chunks.append(part[:max_chars])
                part = part[max_chars:].strip()
            # Append to current chunk if it fits
            if len(current) + len(part) + 1 <= max_chars:
                current += " " + part if current else part
            else:
                if current:
                    chunks.append(current.strip())
                current = part

    if current:
        chunks.append(current.strip())
    return chunks


def process_jsonl_files(filenames, max_chars=300):
    """
    Read JSONL files and split page_content into sentence-based chunks.
    Returns a list of dictionaries containing source, page_index, chunk_id, and text.
    """
    data = []

    for filename in tqdm(filenames, desc="Processing files"):
        with open(filename, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in tqdm(lines, desc=f"Chunking {filename}", leave=False):
            entry = json.loads(line)
            text = entry["page_content"]
            source = entry["source"]
            page_index = entry["page_index"]

            for i, chunk in enumerate(sentence_chunk_text(text, max_chars=max_chars)):
                data.append({
                    "source": source,
                    "page_index": page_index,
                    "chunk_id": i,
                    "text": chunk
                })

    return data


# Example files
filenames = [
    "barnard_2024_2025.jsonl",
    "columbia_college_2024_2025.jsonl",
    "columbia_engineering_2024_2025.jsonl"
]

# Process files into chunks
chunked_data = process_jsonl_files(filenames, max_chars=300)

# Save the chunks to a new JSONL file for embeddings
with open("chunked_bulletins.jsonl", "w", encoding="utf-8") as f:
    for record in chunked_data:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

print(f"Saved {len(chunked_data)} chunks to chunked_bulletins.jsonl")
