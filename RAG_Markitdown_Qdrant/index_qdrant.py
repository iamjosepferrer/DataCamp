"""Embed the heading-split chunks, load them into an in-memory Qdrant collection, run one query."""
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer
from chunker import load_chunks

COLLECTION = "coffee_docs"

model = SentenceTransformer("all-MiniLM-L6-v2")  # 384-dim, runs on CPU
client = QdrantClient(":memory:")  # nothing persists; fine for a demo

if client.collection_exists(COLLECTION):
    client.delete_collection(COLLECTION)
client.create_collection(
    collection_name=COLLECTION,
    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
)

chunks = load_chunks("markdown")
# Embed the heading path together with the text so "Returns Policy > Damaged Bags" is searchable
vectors = model.encode([f"{c['heading_path']}\n{c['text']}" for c in chunks])

client.upsert(
    collection_name=COLLECTION,
    points=[
        PointStruct(id=i, vector=vec.tolist(), payload=chunk)
        for i, (vec, chunk) in enumerate(zip(vectors, chunks))
    ],
)
print(f"Indexed {len(chunks)} chunks into '{COLLECTION}'\n")

for question in ["How much is a 12oz House Blend?",
                 "What do I do if my bag of beans arrived torn?",
                 "What was total revenue in Q2?"]:
    hit = client.query_points(
        collection_name=COLLECTION,
        query=model.encode(question).tolist(),
        limit=1,
    ).points[0]
    print(f"Q: {question}")
    print(f"   score={hit.score:.3f}  source={hit.payload['source_file']}  path={hit.payload['heading_path']}")
    print("   " + hit.payload["text"][:160].replace("\n", " | ") + "\n")

# Two documents share a "Whole Bean Bags" heading. source_file in the payload tells them apart.
hits = client.query_points(
    collection_name=COLLECTION,
    query=model.encode("How much does a 250g bag of beans cost?").tolist(),
    limit=2,
).points
print("Q: How much does a 250g bag of beans cost?")
for h in hits:
    print(f"   score={h.score:.3f}  source={h.payload['source_file']}  path={h.payload['heading_path']}")
