#!/usr/bin/env python3
"""
Chunk the professor reviews from CULPA into 2000 character chunks
"""

import json
from tqdm import tqdm
import re


def simple_sentence_split(text):
    """Simple regex-based sentence splitting"""
    # Split on sentence boundaries (. ! ? followed by whitespace and capital letter or end)
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    return [s.strip() for s in sentences if s.strip()]


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
    # Simple sentence splitting
    sentences = simple_sentence_split(text)
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

def format_professor_text(professor):
    """Format professor information and reviews into text"""
    lines = []
    
    # Professor header
    lines.append(f"Professor: {professor['name']}")
    if professor.get('department'):
        lines.append(f"Department: {professor['department']}")
    if professor.get('overall_rating'):
        lines.append(f"Overall Rating: {professor['overall_rating']}/5.0")
    
    # Courses taught
    if professor.get('courses'):
        lines.append(f"Courses: {', '.join(professor['courses'])}")
    
    lines.append("")  # Blank line
    
    # Reviews
    if professor.get('reviews'):
        lines.append(f"Student Reviews ({len(professor['reviews'])} total):")
        lines.append("")
        
        for idx, review in enumerate(professor['reviews'], 1):
            review_lines = []
            if review.get('course'):
                review_lines.append(f"Review {idx} - {review['course']}")
            else:
                review_lines.append(f"Review {idx}")
            
            if review.get('date'):
                review_lines.append(f"Date: {review['date']}")
            
            if review.get('text'):
                review_lines.append(f"{review['text']}")
            
            if review.get('workload'):
                review_lines.append(f"Workload: {review['workload']}")
            
            review_lines.append("")  # Blank line after each review
            lines.extend(review_lines)
    
    return "\n".join(lines)


def chunk_culpa_reviews(input_file, output_file, min_chars=2000, max_chars=3000):
    """
    Process CULPA professor reviews JSON and create chunks
    
    Args:
        input_file: Path to culpa JSON file
        output_file: Path to output JSONL file
        min_chars: Minimum characters per chunk (default 2000)
        max_chars: Maximum characters per chunk (default 3000)
    """
    print(f"Loading {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    professors = data.get('professors', [])
    total_professors = len(professors)
    
    print(f"Processing {total_professors} professors...")
    
    chunked_data = []
    professors_with_chunks = 0
    
    for professor in tqdm(professors, desc="Chunking professors"):
        # Format professor information and reviews into text
        professor_text = format_professor_text(professor)
        
        # Skip if no meaningful content
        if len(professor_text.strip()) < 100:
            continue
        
        # Chunk the text
        chunks = sentence_chunk_text(professor_text, min_chars=min_chars, max_chars=max_chars, overlap_chars=200)
        
        if chunks:
            professors_with_chunks += 1
            
            # Create records for each chunk
            for chunk_idx, chunk_text in enumerate(chunks):
                record = {
                    "source": f"culpa.info - {professor['name']}",
                    "professor_name": professor['name'],
                    "professor_id": professor.get('id'),
                    "department": professor.get('department', ''),
                    "overall_rating": professor.get('overall_rating'),
                    "chunk_id": chunk_idx,
                    "text": chunk_text
                }
                chunked_data.append(record)
    
    # Save to JSONL
    print(f"\nSaving chunks to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        for record in chunked_data:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    # Print statistics
    avg_chunk_size = sum(len(c['text']) for c in chunked_data) / len(chunked_data) if chunked_data else 0
    
    print(f"\n✓ Successfully chunked professor reviews!")
    print(f"  Total professors processed: {total_professors}")
    print(f"  Professors with chunks: {professors_with_chunks}")
    print(f"  Total chunks created: {len(chunked_data)}")
    print(f"  Average chunk size: {avg_chunk_size:.0f} characters")
    print(f"  Saved to: {output_file}")


if __name__ == "__main__":
    input_file = "culpa_all_reviews_progress_4037_final.json"
    output_file = "chunked_culpa_reviews.jsonl"
    
    chunk_culpa_reviews(input_file, output_file, min_chars=2000, max_chars=3000)
    print("\n✅ Done!")

