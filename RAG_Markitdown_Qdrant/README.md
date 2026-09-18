# Building a RAG Pipeline With MarkItDown and Qdrant

Companion code for the DataCamp tutorial. Converts a mixed folder (PDF, DOCX, XLSX, PPTX) to Markdown with MarkItDown, splits it on headings, and queries it in an in-memory Qdrant collection.

## Setup

Python 3.10 or newer.

```bash
python -m venv .venv && source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu   # CPU-only torch, avoids the multi-GB CUDA download
pip install -r requirements.txt
```

## Run

```bash
./run_all.sh
```

Or one script at a time, in this order:

| Step | Script | What it prints |
|---|---|---|
| 1 | `make_corpus.py` | the 4 generated files in `knowledge_base/` and their sizes |
| 2 | `convert.py` | one `ok` line per file, output in `markdown/` |
| 3 | `compare_extract.py` | chars and tokens for pypdf versus MarkItDown, plus the House Blend line from each |
| 4 | `windows.py` | the raw PDF text cut into 64-token windows |
| 5 | `compare_retrieval.py` | top 3 naive hits and the MarkItDown hit for "How much is a 12oz House Blend?" |
| 6 | `chunker.py` | the 10 heading-split chunks with their `heading_path` |
| 7 | `index_qdrant.py` | 4 queries against the `coffee_docs` collection |

Steps 5 and 7 download `all-MiniLM-L6-v2` (about 90 MB) on first run. Everything runs on CPU and nothing persists; Qdrant runs in `:memory:` mode.

Scripts 2 through 7 only need `knowledge_base/` to exist, so you can drop your own files in there instead of running step 1.
