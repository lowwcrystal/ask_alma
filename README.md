# Ask Alma

A Retrieval-Augmented Generation (RAG) system for answering questions about Columbia College, Columbia Engineering, and Barnard College using course bulletins.

## Overview

This system uses OpenAI's `text-embedding-3-small` model to embed course bulletin information and stores them in Supabase (PostgreSQL with pgvector). It can then answer questions about courses, requirements, and academic policies using semantic search and LLM generation.

## Architecture

The system consists of three main components:

1. **embedder.py** - Loads chunks from JSONL files and creates embeddings using OpenAI
2. **upload_embeddings.py** - Uploads the embeddings to Supabase/PostgreSQL with pgvector
3. **rag_query.py** - Queries the system using semantic search and generates answers

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the `src/embedder/embeddings/` directory with:

```env
# OpenAI API Key (required for embeddings)
OPENAI_API_KEY=your_openai_api_key_here

# Supabase/PostgreSQL connection (required for storage)
DATABASE_URL=postgresql://user:password@host:port/database
```

### 3. Data Files

The system expects three JSONL files in the root directory:
- `barnard_2024_2025.jsonl`
- `columbia_college_2024_2025.jsonl`
- `columbia_engineering_2024_2025.jsonl`

Each JSONL file should contain records with:
- `page_content`: The text content to embed
- `page_index`: The page number (optional)
- `source`: The source document name

## Usage

### Step 1: Generate Embeddings

Navigate to the embeddings directory and run the embedder:

```bash
cd src/embedder/embeddings
python embedder.py
```

This will:
- Load all chunks from the three JSONL files
- Generate embeddings using OpenAI's `text-embedding-3-small` model (1536 dimensions)
- Save embeddings to `emb_out/openai_text-embedding-3-small.npy`
- Save metadata to `emb_out/openai_text-embedding-3-small.meta.tsv`

**Note:** This step will use OpenAI API credits. With ~1420 chunks, expect this to process several hundred chunks.

### Step 2: Upload to Supabase

After embeddings are generated, upload them to your database:

```bash
python upload_embeddings.py
```

This will:
- Create the `documents` table with pgvector extension
- Create an IVFFlat index for fast cosine similarity search
- Upload all embeddings in batches of 500

### Step 3: Query the System

Run queries against your knowledge base:

```bash
python rag_query.py
```

By default, this runs an example query. You can modify the script or import the `rag_answer` function:

```python
from rag_query import rag_answer

result = rag_answer("What are the prerequisites for computer science courses?")
print(result["answer"])
```

## Configuration

### Embedding Model

The system is configured to use OpenAI's `text-embedding-3-small` model. To change models, edit `embedder.py`:

```python
ENABLED_MODELS: List[str] = [
    "openai:text-embedding-3-small",  # Current
    # "ollama:nomic-embed-text",      # Alternative: Local model
    # "hf:all-MiniLM-L6-v2",          # Alternative: HuggingFace
]
```

### Query Parameters

In `rag_query.py`, you can adjust:
- `TOP_K = 5` - Number of relevant chunks to retrieve
- `MAX_CONTEXT_CHARS = 8000` - Maximum context length for the LLM
- `GEN_MODEL = "llama3.1"` - The Ollama model for answer generation

## Database Schema

The `documents` table structure:

```sql
CREATE TABLE documents (
  id text PRIMARY KEY,                    -- SHA256 hash of content
  content text NOT NULL,                  -- The actual text chunk
  source text DEFAULT 'manual',           -- Source identifier
  model text DEFAULT 'text-embedding-3-small',  -- Embedding model used
  embedding vector(1536) NOT NULL,        -- The embedding vector
  created_at timestamptz DEFAULT now()    -- Timestamp
);

-- Index for fast similarity search
CREATE INDEX documents_embedding_cosine_idx 
  ON documents USING ivfflat (embedding vector_cosine_ops) 
  WITH (lists = 100);
```

## Project Structure

```
ask_alma/
├── README.md
├── requirements.txt
├── barnard_2024_2025.jsonl
├── columbia_college_2024_2025.jsonl
├── columbia_engineering_2024_2025.jsonl
├── pdfs/
│   └── [source PDF files]
└── src/
    ├── data_extraction/
    │   └── pdf_reader.py
    ├── chunking/
    │   └── data_chunking.py
    └── embedder/
        └── embeddings/
            ├── embedder.py           # Generate embeddings
            ├── upload_embeddings.py  # Upload to database
            ├── rag_query.py         # Query and generate answers
            └── emb_out/             # Generated embeddings
```

## Costs

- **OpenAI API**: ~$0.02 per 1M tokens for `text-embedding-3-small`
- **Supabase**: Free tier includes 500MB database and 2GB bandwidth

## Troubleshooting

### "OPENAI_API_KEY not set"
Make sure you've created a `.env` file with your OpenAI API key in the `src/embedder/embeddings/` directory.

### "DATABASE_URL not set"
Add your PostgreSQL connection string to the `.env` file.

### "Failed to connect to database"
Verify your DATABASE_URL is correct and your database is accessible. Supabase requires SSL connections.

### Import errors
Run `pip install -r requirements.txt` to install all dependencies.

## Next Steps

- Add more bulletins or course catalogs
- Tune the retrieval parameters (TOP_K, probes)
- Experiment with different embedding models
- Add source citations to answers
- Build a web interface for queries
