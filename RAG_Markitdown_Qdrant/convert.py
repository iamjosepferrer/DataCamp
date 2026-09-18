"""Batch-convert everything in knowledge_base/ to Markdown with MarkItDown."""
from pathlib import Path
from markitdown import MarkItDown, UnsupportedFormatException

SOURCE = Path("knowledge_base")
TARGET = Path("markdown")
TARGET.mkdir(exist_ok=True)

md = MarkItDown(enable_plugins=False)

for path in sorted(SOURCE.iterdir()):
    if not path.is_file():
        continue
    try:
        # convert_local() only reads local paths; convert() also accepts URLs and streams
        result = md.convert_local(path)
    except UnsupportedFormatException:
        print(f"skip  {path.name} (no converter for this format)")
        continue
    except Exception as exc:  # a broken file should not stop the batch
        print(f"fail  {path.name}: {exc}")
        continue

    out = TARGET / f"{path.stem}.md"
    out.write_text(result.markdown, encoding="utf-8")
    print(f"ok    {path.name:22s} -> {out}  ({len(result.markdown):,} chars)")
