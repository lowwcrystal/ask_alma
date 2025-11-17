import nltk
import json
from tqdm import tqdm
import hashlib

# Download NLTK sentence tokenizer if not already present
nltk.download('punkt', quiet=True)
from nltk.tokenize import sent_tokenize

def sentence_chunk_text(text, min_chars=2000, max_chars=3000, overlap_chars=200):
    """
    Split text into chunks with min_chars <= chunk <= max_chars with overlap between consecutive chunks.
    Tries to keep sentences intact, but splits long sentences on punctuation or
    forcibly at max_chars if needed. Ensures chunks are at least min_chars.
    
    Args:
        text: Text to chunk
        min_chars: Minimum characters per chunk (default 2000)
        max_chars: Maximum characters per chunk (default 3000)
        overlap_chars: Number of characters to overlap between consecutive chunks (default 200)
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
                
            # If a single part is longer than max_chars, split it
            while len(part) > max_chars:
                # Hard split if part is too long
                chunks.append(part[:max_chars])
                # Update overlap buffer with the end of this chunk
                overlap_text = part[max_chars-overlap_chars:max_chars] if max_chars > overlap_chars else part[:max_chars]
                overlap_buffer = [overlap_text] if overlap_text.strip() else []
                part = part[max_chars:].strip()
            
            # Append to current chunk if it fits
            test_current = current + (" " + part if current else part)
            
            # If adding this part would exceed max_chars, save current chunk
            if len(test_current) > max_chars:
                # Only save if current chunk meets minimum size
                if current and len(current.strip()) >= min_chars:
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
                else:
                    # Current chunk is too small, keep adding to it
                    current = test_current
            else:
                current = test_current

    # Save final chunk if it meets minimum size
    if current and len(current.strip()) >= min_chars:
        chunks.append(current.strip())
    elif current:
        # If final chunk is too small, append it to the last chunk if possible
        if chunks:
            chunks[-1] = chunks[-1] + " " + current.strip()
        else:
            # If it's the only chunk and too small, include it anyway
            chunks.append(current.strip())
    
    return chunks


def process_jsonl_files(filenames, min_chars=2000, max_chars=3000, overlap_chars=200):
    """
    Read JSONL files and split page_content into sentence-based chunks with overlap.
    Returns a list of dictionaries containing source, page_index, chunk_id, and text.
    Deduplicates chunks to avoid processing repeated content.
    
    Args:
        filenames: List of JSONL file paths
        min_chars: Minimum characters per chunk (default 2000)
        max_chars: Maximum characters per chunk (default 3000)
        overlap_chars: Number of characters to overlap between consecutive chunks (default 200)
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

            for i, chunk in enumerate(sentence_chunk_text(text, min_chars=min_chars, max_chars=max_chars, overlap_chars=overlap_chars)):
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


# All files to process (2024-2025 and 2026)
filenames = [
    "barnard_2024_2025.jsonl",
    "columbia_engineering_2024_2025.jsonl",
    "columbia_college_2024_2025.jsonl",
    "seas_2026.jsonl",
    "barnard_2026.jsonl",
    "columbia_college_2026.jsonl"
]

# Process files into chunks with at least 2000 characters, max 3000, with 200 character overlap
print("Starting chunking process...")
print(f"Chunk size: minimum {2000} chars, maximum {3000} chars, overlap {200} chars")
chunked_data = process_jsonl_files(filenames, min_chars=2000, max_chars=3000, overlap_chars=200)

# Save the chunks to a new JSONL file for embeddings
output_file = "chunked_all_bulletins.jsonl"
with open(output_file, "w", encoding="utf-8") as f:
    for record in chunked_data:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

print(f"\n✓ Saved {len(chunked_data)} chunks to {output_file}")
print(f"  Average chunk size: {sum(len(c['text']) for c in chunked_data) / len(chunked_data):.0f} characters")
