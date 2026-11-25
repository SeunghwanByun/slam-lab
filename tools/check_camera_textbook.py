#!/usr/bin/env python3
"""Read-only source/PDF checks; contact sheets are evidence, not visual approval."""

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt
from PIL import Image, ImageDraw
import pypdfium2 as pdfium


ROOT = Path(__file__).resolve().parents[1]
VERSION = re.compile(r"문서\s*버전\s*:\s*(v\d+\.\d+\.\d+)")
CHAPTER_ID = r"(?:[1-9]|1[0-9]|2[0-4])(?!\d)"
DEFAULT_CHAPTER_PATTERN = rf"(?i)(?<![A-Za-z0-9])[CD]{CHAPTER_ID}|camera|카메라.*(?:교재|파트|부)|(?:교재|파트|부).*카메라"


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.refs = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == "a" and attrs.get("name"):
            self.ids.add(attrs["name"])
        key = "src" if tag == "img" else "href" if tag == "a" else None
        if key and attrs.get(key):
            self.refs.append((tag, attrs[key]))


def compact(text):
    return re.sub(r"\s+", "", text)


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def minimum_pages(min_pages=None, require_100_pages=False):
    return max(min_pages or 0, 100 if require_100_pages else 0)


def source_coverage(source_bytes, tokens, references, source_path):
    """Count H2 chapter IDs and rendered image references, not mentions in prose."""
    chapter_ids = []
    pattern = re.compile(rf"^D({CHAPTER_ID})(?=[.\s:]|$)", re.IGNORECASE)
    for i, token in enumerate(tokens[:-1]):
        if token.type == "heading_open" and token.tag == "h2":
            match = pattern.match(tokens[i + 1].content.strip())
            if match:
                chapter_ids.append(int(match.group(1)))
    image_ids = []
    for tag, href in references:
        if tag != "img":
            continue
        url = urlsplit(href)
        image_ids.append(href if url.scheme or url.netloc else
                         str((source_path.parent / unquote(url.path)).resolve()))
    return {
        "source_bytes": len(source_bytes),
        "source_lines": len(source_bytes.decode("utf-8").splitlines()),
        "new_d_chapter_count": len(set(chapter_ids)),
        "new_d_chapter_ids": [f"D{i}" for i in sorted(set(chapter_ids))],
        "duplicate_d_chapter_ids": [f"D{i}" for i in sorted(set(chapter_ids)) if chapter_ids.count(i) > 1],
        "missing_d_chapter_ids": [f"D{i}" for i in range(1, 25) if i not in chapter_ids],
        "image_occurrences": len(image_ids),
        "image_unique": len(set(image_ids)),
        "note": "Raw UTF-8 source bytes are not a prose-quality measure; image counts include external references, which are not fetched.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "docs/report.md")
    parser.add_argument("--pdf", type=Path, default=ROOT / "docs/report.pdf")
    parser.add_argument("--output", type=Path, default=ROOT / "research/computer-vision-textbook/artifacts/pdf-check")
    parser.add_argument("--require-100-pages", action="store_true")
    parser.add_argument("--min-pages", type=positive_int, help="Minimum PDF pages; combined with --require-100-pages using the larger minimum")
    parser.add_argument("--source-coverage", action="store_true", help="Include D1-D24 H2 coverage, image occurrence/unique counts, and raw source bytes")
    parser.add_argument("--require-navigation", action="store_true", help="Require PDF bookmarks and tagged structure")
    parser.add_argument("--expected-version", help="Also require this exact source version, e.g. v3.0.0")
    parser.add_argument("--chapter-pattern", default=DEFAULT_CHAPTER_PATTERN)
    parser.add_argument("--pages", default="", help="Additional 1-based high-resolution pages, comma separated")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source_bytes = args.source.read_bytes()
    source = source_bytes.decode("utf-8")
    errors, warnings = [], []
    version_match = VERSION.search(source)
    version = version_match.group(1) if version_match else None
    if not version:
        errors.append("Source document version missing")
    if args.expected_version and version != args.expected_version:
        errors.append(f"Source version {version} != expected {args.expected_version}")

    md = MarkdownIt("commonmark", {"html": True})
    refs = References()
    refs.feed(md.render(source))
    external = []
    images = 0
    for tag, href in refs.refs:
        url = urlsplit(href)
        if url.scheme or url.netloc:
            external.append(href)
            continue
        images += tag == "img"
        target = (args.source.parent / unquote(url.path)).resolve()
        if url.path and not target.exists():
            errors.append(f"Missing {tag} target: {href}")
        if not url.path and url.fragment and unquote(url.fragment) not in refs.ids:
            errors.append(f"Missing source anchor: {href}")
        if tag == "img" and target.is_file() and target.suffix.lower() != ".svg":
            try:
                with Image.open(target) as image:
                    image.verify()
            except Exception as exc:
                errors.append(f"Unreadable image {href}: {exc}")
    chapter_re = re.compile(args.chapter_pattern)
    tokens = md.parse(source)
    headings = ["".join(child.content for child in (tokens[i + 1].children or [])
                        if child.type in {"text", "code_inline"}) for i, token in enumerate(tokens[:-1])
                if token.type == "heading_open" and chapter_re.search(tokens[i + 1].content)]
    pdf_bytes = args.pdf.read_bytes()
    pdf = pdfium.PdfDocument(pdf_bytes)
    count = len(pdf)
    required_pages = minimum_pages(args.min_pages, args.require_100_pages)
    if count < required_pages:
        errors.append(f"Page count {count} < {required_pages}")
    if not count:
        errors.append("Empty PDF")
    selected = {1, count}
    selected.update(int(p) for p in args.pages.split(",") if p.strip())
    if any(p < 1 or p > count for p in selected):
        parser.error(f"--pages must be within 1..{count}")
    page_records, chapter_pages, sheets = [], {}, []
    sheet = None
    first_text = ""
    # Render every page. Ignore the footer and outer margins for blank-page checks.
    for index in range(count):
        page = pdf[index]
        textpage = page.get_textpage()
        text = textpage.get_text_range()
        textpage.close()
        if index == 0:
            first_text = text
        for heading in headings:
            if compact(heading) in compact(text):
                chapter_pages.setdefault(heading, []).append(index + 1)
                selected.add(index + 1)
        bitmap = page.render(scale=0.65)
        preview = bitmap.to_pil().convert("RGB")
        bitmap.close()
        width, height = preview.size
        body = preview.crop((int(width * .045), int(height * .045), int(width * .955), int(height * .945))).convert("L")
        ink = sum(body.histogram()[:235])
        blank = ink < 20
        if blank:
            errors.append(f"Blank body on page {index + 1}")
        page_records.append({"page": index + 1, "text_characters": len(text.strip()), "body_ink_pixels": ink, "blank": blank})
        slot = index % 12
        if slot == 0:
            sheet = Image.new("RGB", (4 * 320, 3 * 475), "#dddddd")
        preview.thumbnail((310, 440))
        x, y = (slot % 4) * 320, (slot // 4) * 475
        sheet.paste(preview, (x + (320 - preview.width) // 2, y + 25))
        ImageDraw.Draw(sheet).text((x + 10, y + 6), f"Page {index + 1}", fill="black")
        if slot == 11 or index == count - 1:
            name = f"contact-{index // 12 + 1:03d}.jpg"
            sheet.save(args.output / name, quality=90)
            sheets.append(name)
        page.close()
    pdf_version = VERSION.search(first_text)
    if not pdf_version or pdf_version.group(1) != version:
        errors.append("First-page PDF version does not match source")
    for heading in headings:
        if heading not in chapter_pages:
            errors.append(f"Chapter heading not found in PDF: {heading}")
    if not headings:
        warnings.append("No camera chapter headings matched; first/last and explicit pages selected only")
    highres = []
    for number in sorted(selected):
        page = pdf[number - 1]
        bitmap = page.render(scale=2.0)
        name = f"page-{number:03d}.png"
        bitmap.to_pil().save(args.output / name)
        bitmap.close()
        page.close()
        highres.append(name)
    bookmarks = [{"title": item.get_title(), "level": item.level} for item in pdf.get_toc()]
    tagged = bool(pdfium.raw.FPDFCatalog_IsTagged(pdf))
    if not bookmarks:
        warnings.append("PDF has no bookmarks (legacy renderer output is permitted)")
    if args.require_navigation and (not bookmarks or not tagged):
        errors.append("PDF bookmarks and tagged structure are required")
    pdf.close()
    if args.source.read_bytes() != source_bytes or args.pdf.read_bytes() != pdf_bytes:
        errors.append("Input changed during validation; rerun after writer finishes")
    report = {
        "ok": not errors, "source": str(args.source.resolve()), "pdf": str(args.pdf.resolve()),
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "pdf_sha256": hashlib.sha256(pdf_bytes).hexdigest(), "version": version,
        "pages": count, "require_100_pages": args.require_100_pages,
        "min_pages": args.min_pages, "effective_min_pages": required_pages,
        "local_images": images, "references_checked": len(refs.refs),
        "external_references_not_fetched": sorted(set(external)),
        "bookmarks": bookmarks, "tagged": tagged, "chapter_pages": chapter_pages,
        "contact_sheets": sheets, "high_resolution_pages": highres,
        "page_checks": page_records, "errors": errors, "warnings": warnings,
        "visual_review": "Required: inspect all contact sheets and high-resolution pages; automated checks do not detect all clipping, overlap or Korean glyph problems.",
    }
    if args.source_coverage:
        report["source_coverage"] = source_coverage(source_bytes, tokens, refs.refs, args.source)
    (args.output / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {k: report[k] for k in ("ok", "version", "pages", "effective_min_pages", "local_images", "errors", "warnings")}
    if args.source_coverage:
        summary["source_coverage"] = report["source_coverage"]
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
