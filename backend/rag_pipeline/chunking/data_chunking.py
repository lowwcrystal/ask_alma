import nltk
import json
from tqdm import tqdm
from nltk.tokenize import sent_tokenize

import re
nltk.download('punkt', quiet=True)

def sentence_chunk_text(text, max_chars=1200, overlap_chars=None, min_chunk_chars=200):
 
    if overlap_chars is None:
        overlap_chars = min(200, max(0, int(max_chars * 0.10)))

    sentences = sent_tokenize(text)
    chunks, current = [], ""

    def push_current():
        nonlocal current
        if current:
            chunks.append(current.strip())
            current = ""

    for s in sentences:
       
        parts = re.split(r'([,;])', s)
       
        combined = []
        for p in parts:
            if not combined:
                combined.append(p)
            elif p in {",", ";"}:
                combined[-1] = (combined[-1] + p)
            else:
                combined.append(p)

        for part in combined:
            part = part.strip()
            
            while len(part) > max_chars:
               
                if not current:
                    chunks.append(part[:max_chars].strip())
                    part = part[max_chars:].strip()
                else:
                    push_current()

            if not current:
                current = part
            elif len(current) + 1 + len(part) <= max_chars:
                current = f"{current} {part}"
            else:
                prev = current
                push_current()
                if overlap_chars > 0:
                    tail = prev[-overlap_chars:]
                    room = max_chars - len(part) - 1  
                    if room > 0 and len(tail) > room:
                        tail = tail[-room:]
                    
                    if len(tail) >= min(20, overlap_chars): 
                        current = (tail + " " + part).strip()
                    else:
                        current = part
                else:
                    current = part

    if current:
        push_current()
    
    if len(chunks) >= 2 and len(chunks[-1]) < min_chunk_chars:
        last = chunks.pop()
        if len(chunks[-1]) + 1 + len(last) <= max_chars:
            chunks[-1] = f"{chunks[-1]} {last}".strip()
        else:
            chunks.append(last)

    return chunks


def process_jsonl_files(filenames, max_chars=1200):
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

filenames = [
    "barnard_2024_2025.jsonl",
    "columbia_college_2024_2025.jsonl",
    "columbia_engineering_2024_2025.jsonl"
]

chunked_data = process_jsonl_files(filenames, max_chars=1200)

with open("chunked_bulletins.jsonl", "w", encoding="utf-8") as f:
    for record in chunked_data:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

print(f"Saved {len(chunked_data)} chunks to chunked_bulletins.jsonl")
