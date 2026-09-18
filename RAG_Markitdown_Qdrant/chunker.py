"""Split MarkItDown output on Markdown headings and keep the heading path as metadata."""
import re
from pathlib import Path

HEADING = re.compile(r"^(#{1,3})\s+(.*)$")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)  # MarkItDown marks pptx slides this way
MIN_CHARS = 40  # drop title-only slivers


def split_on_headings(markdown: str, source_file: str) -> list[dict]:
    """One chunk per heading section. Text before the first heading becomes its own chunk."""
    chunks, path, buffer = [], [], []
    doc_title = Path(source_file).stem.replace("_", " ").title()

    def flush():
        text = "\n".join(buffer).strip()
        if len(text) >= MIN_CHARS:
            chunks.append({
                "text": text,
                "source_file": source_file,
                "heading_path": " > ".join([doc_title] + path),
            })
        buffer.clear()

    for line in HTML_COMMENT.sub("", markdown).splitlines():
        m = HEADING.match(line)
        if m:
            flush()
            level, title = len(m.group(1)), m.group(2).strip()
            path[:] = path[: level - 1] + [title]
        else:
            buffer.append(line)
    flush()
    return chunks


def load_chunks(folder: str = "markdown") -> list[dict]:
    chunks = []
    for md_file in sorted(Path(folder).glob("*.md")):
        source = md_file.stem + ".md"
        chunks.extend(split_on_headings(md_file.read_text(encoding="utf-8"), source))
    return chunks


if __name__ == "__main__":
    for c in load_chunks():
        print(f"[{c['heading_path']}]  ({len(c['text'])} chars)")
        print("   " + c["text"][:90].replace("\n", " | ") + ("..." if len(c["text"]) > 90 else ""))
