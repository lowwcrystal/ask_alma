import nltk
import json
from tqdm import tqdm
import hashlib

# Download NLTK sentence tokenizer if not already present
nltk.download('punkt', quiet=True)
from nltk.tokenize import sent_tokenize

def sentence_chunk_text(text, max_chars=300, overlap_chars=50):
    """
    Split text into chunks <= max_chars with overlap between consecutive chunks.
    Tries to keep sentences intact, but splits long sentences on punctuation or
    forcibly at max_chars if needed.
    
    Args:
        text: Text to chunk
        max_chars: Maximum characters per chunk
        overlap_chars: Number of characters to overlap between consecutive chunks
    """
    import re
    # use nltk to split sentences semantically
    sentences = sent_tokenize(text)
    chunks, current = [], ""
    overlap_buffer = []  # Store sentences/parts for overlap

    for s in sentences:
        # Split long sentences further on commas/semicolons
        parts = re.split(r'([,;])', s)
        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            while len(part) > max_chars:
                # Hard split if part is too long
                chunks.append(part[:max_chars])
                # Update overlap buffer with the end of this chunk
                overlap_text = part[max_chars-overlap_chars:max_chars] if max_chars > overlap_chars else part[:max_chars]
                overlap_buffer = [overlap_text] if overlap_text.strip() else []
                part = part[max_chars:].strip()
            
            # Append to current chunk if it fits
            test_current = current + (" " + part if current else part)
            if len(test_current) <= max_chars:
                current = test_current
            else:
                # Save current chunk
                if current:
                    chunks.append(current.strip())
                    # Build overlap buffer from the end of current chunk
                    if len(current) >= overlap_chars:
                        overlap_text = current[-overlap_chars:].strip()
                        # Try to start overlap at a word boundary
                        first_space = overlap_text.find(' ')
                        if first_space > 0:
                            overlap_text = overlap_text[first_space+1:]
                        overlap_buffer = [overlap_text] if overlap_text else []
                    else:
                        overlap_buffer = [current.strip()] if current.strip() else []
                
                # Start new chunk with overlap from previous chunk
                if overlap_buffer:
                    overlap_str = " ".join(overlap_buffer)
                    current = overlap_str + " " + part if overlap_str else part
                else:
                    current = part

    if current:
        chunks.append(current.strip())
    return chunks


def process_jsonl_files(filenames, max_chars=300, overlap_chars=50):
    """
    Read JSONL files and split page_content into sentence-based chunks with overlap.
    Returns a list of dictionaries containing source, page_index, chunk_id, and text.
    Deduplicates chunks to avoid processing repeated content.
    
    Args:
        filenames: List of JSONL file paths
        max_chars: Maximum characters per chunk
        overlap_chars: Number of characters to overlap between consecutive chunks
    """
    data = []
    seen_chunks = set()  # Track unique chunks by hash
    duplicate_count = 0

    for filename in tqdm(filenames, desc="Processing files"):
        with open(filename, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in tqdm(lines, desc=f"Chunking {filename}", leave=False):
            entry = json.loads(line)
            text = entry["page_content"]
            source = entry["source"]
            page_index = entry["page_index"]

            for i, chunk in enumerate(sentence_chunk_text(text, max_chars=max_chars, overlap_chars=overlap_chars)):
                # Normalize chunk for comparison (strip whitespace, lowercase)
                normalized_chunk = chunk.strip().lower()
                
                # Create a hash of the normalized chunk
                chunk_hash = hashlib.md5(normalized_chunk.encode('utf-8')).hexdigest()
                
                # Only add if we haven't seen this chunk before
                if chunk_hash not in seen_chunks:
                    seen_chunks.add(chunk_hash)
                    data.append({
                        "source": source,
                        "page_index": page_index,
                        "chunk_id": i,
                        "text": chunk
                    })
                else:
                    duplicate_count += 1

    if duplicate_count > 0:
        print(f"\nSkipped {duplicate_count} duplicate chunks")
    
    return data


# Example files
filenames = [
    "seas_2026.jsonl",
    "barnard_2026.jsonl"
]

# Process files into chunks with 50 character overlap
chunked_data = process_jsonl_files(filenames, max_chars=300, overlap_chars=50)

# Save the chunks to a new JSONL file for embeddings
with open("chunked_bulletins.jsonl", "w", encoding="utf-8") as f:
    for record in chunked_data:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

print(f"Saved {len(chunked_data)} chunks to chunked_bulletins.jsonl")
