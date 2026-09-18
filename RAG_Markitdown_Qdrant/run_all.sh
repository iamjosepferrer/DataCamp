#!/usr/bin/env bash
# Runs the whole pipeline in the order the article introduces it.
set -e
python make_corpus.py          # 1. generate knowledge_base/ (4 files)
python convert.py              # 2. MarkItDown -> markdown/
python compare_extract.py      # 3. pypdf versus MarkItDown, token counts
python windows.py              # 4. blind 64-token windows of the raw PDF text
python compare_retrieval.py    # 5. naive pipeline versus MarkItDown chunk, same question
python chunker.py              # 6. heading-split chunks with heading_path
python index_qdrant.py         # 7. embed, upsert, query in-memory Qdrant
