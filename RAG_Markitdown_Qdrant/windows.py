"""Cut the raw pypdf text of the catalog into fixed 64-token windows (a blind chunker)."""
import tiktoken
from pypdf import PdfReader

WINDOW = 64  # tiny on purpose so the cuts land inside the table; real pipelines use 300 to 800

raw = "\n".join(p.extract_text() for p in PdfReader("knowledge_base/catalog.pdf").pages)
enc = tiktoken.get_encoding("cl100k_base")
tokens = enc.encode(raw)

windows = [enc.decode(tokens[i:i + WINDOW]) for i in range(0, len(tokens), WINDOW)]
for n, text in enumerate(windows):
    print(f"--- window {n} ---")
    print(text)
