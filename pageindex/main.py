#!/usr/bin/env python3
"""
PageIndex RAG Tutorial — local test script
==========================================
Run from the command line (NOT inside Jupyter):
    python pageindex_test.py

Requirements:
    pip install pageindex openai requests faiss-cpu pymupdf python-dotenv

Environment variables (set before running):
    export PAGEINDEX_API_KEY="your_key"
    export OPENAI_API_KEY="your_key"

NOTE FOR DATACAMP/JUPYTER READERS
----------------------------------
asyncio.run() works in a plain .py script. In a Jupyter notebook it will raise
"RuntimeError: This event loop is already running". In Jupyter, replace every
asyncio.run(some_coroutine()) with:
    result = await some_coroutine()
and wrap the comparison loop inside an async def that you then await.
See the "Jupyter adapter" comments below each relevant block.
"""

import os
import copy
import time
import json
import asyncio
import requests
import numpy as np
import faiss
from dotenv import load_dotenv
from pageindex import PageIndexClient
import pageindex.utils as utils
import openai
from openai import OpenAI

# ── Config ─────────────────────────────────────────────────────────────────────
# Loads PAGEINDEX_API_KEY and OPENAI_API_KEY from a .env file in the same folder.
# Create a .env file with these two lines (no quotes needed):
#   PAGEINDEX_API_KEY=your_key_here
#   OPENAI_API_KEY=your_key_here
load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY")
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY")

if not PAGEINDEX_API_KEY:
    raise ValueError("PAGEINDEX_API_KEY not found. Check your .env file.")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found. Check your .env file.")

pi_client     = PageIndexClient(api_key=PAGEINDEX_API_KEY)
openai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
sync_openai   = OpenAI(api_key=OPENAI_API_KEY)

# ── Step 1: Download the PDF ───────────────────────────────────────────────────
DOWNLOAD_DIR = "./data"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

PDF_URL  = "https://www.federalreserve.gov/publications/files/financial-stability-report-20231020.pdf"
PDF_PATH = os.path.join(DOWNLOAD_DIR, "fed_financial_stability_report_2023.pdf")

if not os.path.exists(PDF_PATH):
    print("Downloading Federal Reserve Financial Stability Report (Oct 2023)...")
    r = requests.get(PDF_URL, timeout=60)
    r.raise_for_status()
    with open(PDF_PATH, "wb") as f:
        f.write(r.content)
    print(f"Saved to {PDF_PATH}")
else:
    print(f"Already present: {PDF_PATH}")

# ── Step 2: Submit to PageIndex ────────────────────────────────────────────────
print("\nSubmitting document to PageIndex...")
submit_result = pi_client.submit_document(PDF_PATH)
doc_id = submit_result["doc_id"]
print(f"Document ID: {doc_id}")
print("(Save this ID — you can reuse it without re-uploading the file.)")

# ── Step 3: Poll until tree is ready ──────────────────────────────────────────
print("\nWaiting for tree generation (2-4 min for a 100-page PDF)...")
while True:
    status_result = pi_client.get_document(doc_id)
    status = status_result.get("status")
    print(f"  Status: {status}")
    if status == "completed":
        break
    elif status == "failed":
        raise RuntimeError(f"Processing failed: {status_result}")
    time.sleep(10)

print("Processing done.\n")

# IF YOU ALREADY PROCESSED YOUR DOCUMENT, YOU CAN SKIP STEP 1-3 AND USE THE DOCUMENT ID DIRECTLY. 
# doc_id = "pi-cmq2bp4ok00rx01qxmym7tnd1"
# print(f"Using existing document: {doc_id}")

# ── Step 4: Retrieve and inspect the tree ─────────────────────────────────────
# node_summary=True is required — without it, nodes have no summaries
# and the tree search prompt has nothing useful to reason over.
tree_result = pi_client.get_tree(doc_id, node_summary=True)
tree = tree_result["result"]

# Flatten the nested tree into a dict keyed by node_id for fast lookups.
# Use create_node_mapping (not get_node_map — that function does not exist).
node_map = utils.create_node_mapping(tree)

print(f"Top-level nodes ({len(tree)} sections):\n")
for node in tree:
    print(f"  [{node['node_id']}] {node['title']}")
    print(f"       Page {node.get('page_index', '?')}")
    print(f"       {node.get('summary', '')[:120]}...")
    print()

# ── PageIndex pipeline ─────────────────────────────────────────────────────────
TREE_SEARCH_PROMPT = """\
You are a document retrieval assistant.
Given a document's tree structure and a user query, identify which nodes (sections)
are most likely to contain the answer.

Document tree:
{tree_json}

User query: {query}

Return a JSON object with the following format:
{{
  "reasoning": "Your step-by-step reasoning about which sections to retrieve",
  "node_ids": ["id1", "id2", ...]
}}

Return ONLY the JSON object, no other text."""

ANSWER_PROMPT = """\
You are a financial document analyst. Answer the user's question
using ONLY the provided context. Cite the specific section(s) you are drawing from.
If the context does not contain enough information to answer, say so clearly.

Context:
{context}

Question: {question}

Provide a precise, well-cited answer."""


async def tree_search(tree, query: str, model: str = "gpt-4o") -> dict:
    """Use an LLM to reason over the tree and return relevant node IDs."""
    # remove_fields mutates in place, so deep-copy first to protect the original tree.
    # The bug report uses tree.copy() (shallow); deepcopy is safer for nested structures.
    slim_tree = utils.remove_fields(copy.deepcopy(tree), fields=["text"])
    tree_json = json.dumps(slim_tree, indent=2)
    prompt = TREE_SEARCH_PROMPT.format(tree_json=tree_json, query=query)

    response = await openai_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


async def generate_answer(node_ids: list, query: str, node_map: dict,
                          model: str = "gpt-4o") -> str:
    """Extract text from the selected nodes and generate an answer."""
    context_parts = []
    for node_id in node_ids:
        node = node_map.get(node_id)
        if node:
            # Correct field names: start_index / end_index (not page_start / page_end)
            header = f"[{node['title']} | Page {node.get('page_index', '?')}]"
            context_parts.append(f"{header}\n{node.get('text', '')}")

    context = "\n\n---\n\n".join(context_parts)
    prompt = ANSWER_PROMPT.format(context=context, question=query)

    response = await openai_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return response.choices[0].message.content


async def pageindex_pipeline(tree, query: str, node_map: dict) -> dict:
    """Full PageIndex pipeline: tree search + answer generation."""
    search_result = await tree_search(tree, query)
    node_ids  = search_result["node_ids"]
    reasoning = search_result["reasoning"]
    answer    = await generate_answer(node_ids, query, node_map)
    return {
        "query":              query,
        "reasoning":          reasoning,
        "retrieved_sections": node_ids,
        "answer":             answer,
    }


# ── Quick smoke test for tree search only ─────────────────────────────────────
async def smoke_test():
    query_1 = (
        "What are the main vulnerabilities the Fed identified in asset valuations "
        "as of October 2023, and which markets were flagged as stretched?"
    )
    print(f"Smoke test query: {query_1}\n")
    result = await tree_search(tree, query_1)
    print("LLM Reasoning:")
    print(result["reasoning"])
    print(f"\nSelected node IDs: {result['node_ids']}")
    print("(IDs are zero-padded integers, e.g. '0003', '0004')\n")
    return result

# Jupyter adapter: replace with  result = await smoke_test()
smoke_result = asyncio.run(smoke_test())

# Full pipeline test
async def full_pipeline_test():
    query_1 = (
        "What are the main vulnerabilities the Fed identified in asset valuations "
        "as of October 2023, and which markets were flagged as stretched?"
    )
    result = await pageindex_pipeline(tree, query_1, node_map)
    print(f"Query: {result['query']}\n")
    print(f"Retrieved sections: {result['retrieved_sections']}\n")
    print(f"Answer:\n{result['answer']}")
    return result

# Jupyter adapter: replace with  result = await full_pipeline_test()
pipeline_result = asyncio.run(full_pipeline_test())

# ── Vector RAG baseline ────────────────────────────────────────────────────────
def extract_text_from_pdf(pdf_path: str) -> str:
    import fitz  # pymupdf
    doc = fitz.open(pdf_path)
    pages = []
    for page_num, page in enumerate(doc):
        text = page.get_text()
        if text.strip():
            pages.append(f"[Page {page_num + 1}]\n{text}")
    return "\n\n".join(pages)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    words = text.split()
    chunks, start = [], 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks


def embed_chunks(chunks: list[str], model: str = "text-embedding-3-small") -> np.ndarray:
    all_embeddings = []
    for i in range(0, len(chunks), 100):
        batch = chunks[i : i + 100]
        response = sync_openai.embeddings.create(input=batch, model=model)
        all_embeddings.extend([item.embedding for item in response.data])
    return np.array(all_embeddings, dtype="float32")


def build_faiss_index(embeddings: np.ndarray) -> faiss.IndexFlatIP:
    faiss.normalize_L2(embeddings)
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    return index


def vector_rag_pipeline(query: str, chunks: list[str],
                         index: faiss.IndexFlatIP, k: int = 5,
                         model: str = "gpt-4o") -> str:
    q_emb = sync_openai.embeddings.create(
        input=[query], model="text-embedding-3-small"
    ).data[0].embedding
    q_vec = np.array([q_emb], dtype="float32")
    faiss.normalize_L2(q_vec)

    _, idxs = index.search(q_vec, k)
    context = "\n\n---\n\n".join(chunks[i] for i in idxs[0] if i < len(chunks))

    response = sync_openai.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Answer the question using only the provided context. Be precise."},
            {"role": "user",   "content": f"Context:\n{context}\n\nQuestion: {query}"},
        ],
        temperature=0,
    )
    return response.choices[0].message.content


print("\nExtracting text from PDF...")
raw_text = extract_text_from_pdf(PDF_PATH)

print("Chunking text...")
chunks = chunk_text(raw_text, chunk_size=500, overlap=50)
print(f"  {len(chunks)} chunks created")

print("Embedding chunks (takes 1-2 min)...")
embeddings = embed_chunks(chunks)
print(f"  Embeddings shape: {embeddings.shape}")

print("Building FAISS index...")
faiss_index = build_faiss_index(embeddings)
print("Done.\n")

# ── Comparison run ─────────────────────────────────────────────────────────────
queries = [
    # Direct factual lookup — answer is in a specific section
    "What does the Fed consider the most significant near-term risk to financial stability as of October 2023?",

    # Cross-reference question — answer requires following the report's internal structure
    "What methodology does the Fed use to assess climate-related financial risks, and where in the report is it described?",

    # Multi-section comparison — requires reasoning across sections 1 and 3
    "How do elevated asset valuations interact with leverage in the financial sector to amplify systemic risk, according to the report?",
]


async def run_comparison():
    results = []
    for query in queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}\n")

        pi_result  = await pageindex_pipeline(tree, query, node_map)
        pi_answer  = pi_result["answer"]
        vec_answer = vector_rag_pipeline(query, chunks, faiss_index)

        results.append({
            "query":             query,
            "pageindex_answer":  pi_answer,
            "vector_rag_answer": vec_answer,
        })

        print("PageIndex answer:")
        print(pi_answer[:500])
        print("\nVector RAG answer:")
        print(vec_answer[:500])

    return results


# Jupyter adapter: replace with  results = await run_comparison()
results = asyncio.run(run_comparison())
print("\nAll done.")