"""Parse a wayback-dumped markdown article into structured blocks.

Output schema:
    {
        "slug": "crafting-a-result-pattern-in-c-a-comprehensive-guide",
        "title": "Crafting a Result Pattern in C#: A Comprehensive Guide",
        "source": "https://forevka.dev/articles/...",
        "intro": {
            "title": "...",
            "description": "...",        # short subtitle / dek
            "body_title": "...",
            "body_description": "...",
            "read_time": 12,
        },
        "blocks": [
            {"type": "text", "html": "<p>...</p>"},
            {"type": "code", "text": "public class ...", "language": "csharp"},
            {"type": "image", "src": "https://forevka.dev/media/.../foo.png",
             "filename": "foo.png", "alt": "..."},
        ],
        "image_refs": [
            {"src": "...", "filename": "..."},
        ],
    }

Code-block detection: 4-space-indented blocks AND ```fenced``` blocks both count.
Image block: `![alt](url)` on its own line at paragraph scope. Inline images
inside paragraphs are kept as html in the text block.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any

try:
    import markdown as md_lib
except ImportError:
    md_lib = None  # type: ignore

DUMP_DIR = os.path.join(os.path.dirname(__file__), "..", "forevka_dump")
DUMP_DIR = os.path.normpath(DUMP_DIR)


@dataclass
class Block:
    kind: str  # 'text' | 'code' | 'image'
    text: str = ""
    html: str = ""
    language: str = ""
    src: str = ""
    filename: str = ""
    alt: str = ""

    def to_dict(self) -> dict[str, Any]:
        if self.kind == "text":
            return {"type": "text", "html": self.html}
        if self.kind == "code":
            return {"type": "code", "text": self.text, "language": self.language}
        if self.kind == "image":
            return {"type": "image", "src": self.src, "filename": self.filename, "alt": self.alt}
        raise ValueError(self.kind)


@dataclass
class Article:
    slug: str
    title: str
    source: str
    body: str
    blocks: list[Block] = field(default_factory=list)
    intro: dict[str, Any] = field(default_factory=dict)
    image_refs: list[dict[str, str]] = field(default_factory=list)


def _read_md(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read().replace("\r\n", "\n").replace("\r", "\n")


def _split_header(text: str) -> tuple[str, str, str]:
    """Pull the leading `# Title`, `> Source: ...`, `---`, and return (title, source, body)."""
    title_match = re.match(r"^#\s+(.+?)\n", text)
    title = title_match.group(1).strip() if title_match else ""
    source_match = re.search(r"^>\s*Source:\s*(\S+)", text, re.MULTILINE)
    source = source_match.group(1).strip() if source_match else ""
    after_separator = text.split("\n---\n", 1)
    body = after_separator[1].lstrip("\n") if len(after_separator) == 2 else text
    if body.startswith("# "):
        body = body.split("\n", 1)[1] if "\n" in body else ""
    body = body.lstrip("\n")
    return title, source, body


_FENCE_RE = re.compile(r"^```([A-Za-z0-9_+-]*)\s*$")
_IMG_LINE_RE = re.compile(r"^!\[(?P<alt>[^\]]*)\]\((?P<url>[^)\s]+)(?:\s+\"[^\"]*\")?\)\s*$")
_INDENT_CODE_RE = re.compile(r"^( {4}|\t)(.*)$")


def _filename_from_url(url: str) -> str:
    base = url.rsplit("/", 1)[-1]
    base = base.split("?", 1)[0]
    return base


def _split_blocks(body: str) -> list[Block]:
    """Walk markdown line-by-line; pull out code fences, indented code, and standalone image lines.
    Everything else accumulates into prose buffers that get rendered to HTML."""
    blocks: list[Block] = []
    prose: list[str] = []
    lines = body.split("\n")

    def flush_prose() -> None:
        if not prose:
            return
        text = "\n".join(prose).strip()
        if text:
            html = _markdown_to_html(text)
            if html.strip():
                blocks.append(Block(kind="text", html=html))
        prose.clear()

    i = 0
    while i < len(lines):
        line = lines[i]
        fence = _FENCE_RE.match(line)
        if fence:
            flush_prose()
            lang = fence.group(1).strip().lower() or "csharp"
            i += 1
            buf: list[str] = []
            while i < len(lines) and not _FENCE_RE.match(lines[i]):
                buf.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            blocks.append(Block(kind="code", text="\n".join(buf).rstrip(), language=lang))
            continue

        # 4-space-indented code block: only treat it as code if the previous
        # line was blank (to avoid grabbing list-item continuations).
        if (
            _INDENT_CODE_RE.match(line)
            and (not prose or prose[-1].strip() == "")
        ):
            flush_prose()
            buf = []
            while i < len(lines):
                m = _INDENT_CODE_RE.match(lines[i])
                if m:
                    buf.append(m.group(2))
                    i += 1
                elif lines[i].strip() == "":
                    buf.append("")
                    i += 1
                    if i < len(lines) and not _INDENT_CODE_RE.match(lines[i]):
                        # blank line not followed by more code — end of block
                        break
                else:
                    break
            text = "\n".join(buf).rstrip()
            if text.strip():
                lang = _guess_language(text)
                blocks.append(Block(kind="code", text=text, language=lang))
            continue

        img = _IMG_LINE_RE.match(line.strip())
        if img:
            flush_prose()
            url = img.group("url")
            blocks.append(
                Block(
                    kind="image",
                    src=url,
                    filename=_filename_from_url(url),
                    alt=img.group("alt").strip(),
                )
            )
            i += 1
            continue

        prose.append(line)
        i += 1

    flush_prose()
    return blocks


def _markdown_to_html(text: str) -> str:
    if md_lib is None:
        # extremely minimal fallback: paragraphs only
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        return "".join(f"<p>{p}</p>" for p in paragraphs)
    return md_lib.markdown(
        text,
        extensions=["extra", "sane_lists", "smarty"],
        output_format="html",
    )


def _guess_language(code_text: str) -> str:
    snippet = code_text[:600]
    if re.search(r"\b(public|private|namespace|using|class|interface|async\s+Task|var)\b", snippet):
        return "csharp"
    if re.search(r"#include\s*<|std::|::\w", snippet):
        return "cpp"
    if re.search(r"\bdef\s+\w+\(|\bimport\s+\w+|->|self\b", snippet):
        return "python"
    if re.search(r"\bfunction\s+\w+\(|\bconst\s+\w+\s*=", snippet):
        return "javascript"
    return "csharp"


_DEFAULT_READ_TIMES = {
    "crafting-a-result-pattern-in-c-a-comprehensive-guide": 12,
    "developing-a-cross-platform-pdf-to-svgpng-wrapper-for-net": 8,
    "discriminated-unions-result-pattern-part-1": 6,
}


def _slug_from_filename(path: str) -> str:
    name = os.path.splitext(os.path.basename(path))[0]
    if name.startswith("articles_"):
        name = name[len("articles_") :]
    return name


def _extract_intro(article_title: str, blocks: list[Block]) -> tuple[str, str, str, str, list[Block]]:
    """First text block's first paragraph is description. Returns (title, description, bodyTitle,
    bodyDescription, remaining_blocks). The remaining_blocks have the intro text block stripped."""
    description = ""
    body_title = article_title
    body_description = ""
    if blocks and blocks[0].kind == "text":
        first_html = blocks[0].html
        # Pull out a leading H1 as bodyTitle if present
        h1 = re.search(r"<h1[^>]*>(.*?)</h1>", first_html, re.DOTALL | re.IGNORECASE)
        if h1:
            body_title = re.sub(r"<[^>]+>", "", h1.group(1)).strip()
            first_html = first_html[h1.end() :]
        first_p = re.search(r"<p[^>]*>(.*?)</p>", first_html, re.DOTALL | re.IGNORECASE)
        if first_p:
            description = re.sub(r"<[^>]+>", "", first_p.group(1)).strip()
            body_description = description.split(".")[0][:200]
            first_html = first_html[: first_p.start()] + first_html[first_p.end() :]
        blocks[0].html = first_html.strip()
        if not blocks[0].html:
            blocks = blocks[1:]
    return article_title, description, body_title, body_description, blocks


def parse_article(path: str) -> Article:
    raw = _read_md(path)
    title, source, body = _split_header(raw)
    blocks = _split_blocks(body)
    title, description, body_title, body_description, blocks = _extract_intro(title, blocks)
    slug = _slug_from_filename(path)
    read_time = _DEFAULT_READ_TIMES.get(slug, max(3, len(body.split()) // 200))

    image_refs: list[dict[str, str]] = []
    for b in blocks:
        if b.kind == "image":
            image_refs.append({"src": b.src, "filename": b.filename})

    art = Article(
        slug=slug,
        title=title,
        source=source,
        body=body,
        blocks=blocks,
        intro={
            "title": title,
            "description": description,
            "body_title": body_title,
            "body_description": body_description,
            "read_time": read_time,
        },
        image_refs=image_refs,
    )
    return art


def parse_all(dump_dir: str = DUMP_DIR) -> list[Article]:
    out: list[Article] = []
    for fn in sorted(os.listdir(dump_dir)):
        if fn.startswith("articles_") and fn.endswith(".md"):
            out.append(parse_article(os.path.join(dump_dir, fn)))
    return out


def main() -> int:
    arts = parse_all()
    summary = []
    for a in arts:
        block_kinds: dict[str, int] = {}
        for b in a.blocks:
            block_kinds[b.kind] = block_kinds.get(b.kind, 0) + 1
        summary.append(
            {
                "slug": a.slug,
                "title": a.title,
                "intro": a.intro,
                "block_count": len(a.blocks),
                "block_kinds": block_kinds,
                "image_refs": a.image_refs,
            }
        )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
