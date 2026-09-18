"""Raw pypdf text versus MarkItDown Markdown for the same PDF, with token counts."""
import tiktoken
from pypdf import PdfReader
from markitdown import MarkItDown

pdf = "knowledge_base/catalog.pdf"
raw = "\n".join(p.extract_text() for p in PdfReader(pdf).pages)
md = MarkItDown().convert_local(pdf).markdown

enc = tiktoken.get_encoding("cl100k_base")
for name, text in [("pypdf", raw), ("markitdown", md)]:
    print(f"{name:11s} {len(text):>5} chars  {len(enc.encode(text)):>4} tokens")

print("\nLines mentioning House Blend:")
for name, text in [("pypdf", raw), ("markitdown", md)]:
    for line in text.splitlines():
        if "House Blend" in line and "base" not in line:
            print(f"  {name:11s} {line!r}")
