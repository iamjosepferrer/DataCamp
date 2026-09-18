"""Does the naive pipeline actually fail the query? Index blind token windows of raw
pypdf text, index the MarkItDown chunk, and ask the same question of both."""
import tiktoken
from pypdf import PdfReader
from markitdown import MarkItDown
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

PDF = "knowledge_base/catalog.pdf"
WINDOW = 64  # small because the corpus is small; real pipelines use 300 to 800
QUESTION = "How much is a 12oz House Blend?"

model = SentenceTransformer("all-MiniLM-L6-v2")
client = QdrantClient(":memory:")


def index(name: str, texts: list[str]) -> None:
    client.create_collection(name, vectors_config=VectorParams(size=384, distance=Distance.COSINE))
    client.upsert(name, points=[
        PointStruct(id=i, vector=model.encode(t).tolist(), payload={"text": t})
        for i, t in enumerate(texts)
    ])


# Path A: raw pypdf text cut into blind token windows
raw = "\n".join(p.extract_text() for p in PdfReader(PDF).pages)
enc = tiktoken.get_encoding("cl100k_base")
tokens = enc.encode(raw)
index("naive_pdf", [enc.decode(tokens[i:i + WINDOW]) for i in range(0, len(tokens), WINDOW)])

# Path B: MarkItDown Markdown, whole file as one chunk (the PDF has no headings to split on)
markdown = MarkItDown().convert_local(PDF).markdown
index("markitdown_pdf", [markdown.strip()])

query = model.encode(QUESTION).tolist()
print(f"Q: {QUESTION}\n")
print("naive_pdf, top 3:")
for hit in client.query_points("naive_pdf", query=query, limit=3).points:
    print(f"  score={hit.score:.3f}  {hit.payload['text'][:70]!r}...")
print("\nmarkitdown_pdf, top 1:")
hit = client.query_points("markitdown_pdf", query=query, limit=1).points[0]
print(f"  score={hit.score:.3f}  {hit.payload['text'][:70]!r}...")
