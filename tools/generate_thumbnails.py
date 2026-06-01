#!/usr/bin/env python3
"""
GFIELD thumbnail pipeline
- Extract first page from each PDF
- Normalize to 300x400 (3:4)
- Save WebP to ./thumbnails
- Upsert thumbnail_path into materials.json
"""

from __future__ import annotations

import json
from pathlib import Path

from pdf2image import convert_from_path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "pdfs"
THUMB_DIR = ROOT / "thumbnails"
MATERIALS = ROOT / "materials.json"
WIDTH, HEIGHT = 300, 400
FALLBACK_THUMB = "thumbnails/_default_cover.webp"


def make_thumb(pdf_path: Path, out_path: Path) -> None:
    pages = convert_from_path(str(pdf_path), first_page=1, last_page=1, dpi=200)
    if not pages:
        raise RuntimeError(f"No page extracted: {pdf_path}")
    img = pages[0].convert("RGB")
    fitted = ImageOps.fit(img, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fitted.save(out_path, "WEBP", quality=82, method=6)


def load_materials() -> list[dict]:
    if not MATERIALS.exists():
        return []
    return json.loads(MATERIALS.read_text(encoding="utf-8"))


def save_materials(rows: list[dict]) -> None:
    MATERIALS.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def upsert_material(rows: list[dict], book_id: str, name: str, thumb_rel: str, pdf_rel: str) -> None:
    payload = {
        "book_id": book_id,
        "display_name": name,
        "thumbnail_path": thumb_rel,
        "path": pdf_rel,
        "thumbnail_updated_at": str(int(Path(ROOT / pdf_rel).stat().st_mtime)),
    }
    for i, row in enumerate(rows):
        if row.get("book_id") == book_id:
            rows[i] = {**row, **payload}
            return
    rows.append(payload)


def main() -> None:
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_materials()
    for pdf in sorted(PDF_DIR.rglob("*.pdf")):
        book_id = pdf.stem
        thumb = THUMB_DIR / f"{book_id}.webp"
        try:
            prev = next((r for r in rows if r.get("book_id") == book_id), None)
            mtime = str(int(pdf.stat().st_mtime))
            if prev and prev.get("thumbnail_updated_at") == mtime and thumb.exists():
                print(f"skip: {book_id}")
            else:
                make_thumb(pdf, thumb)
                print(f"ok: {book_id}")
            thumb_rel = f"thumbnails/{book_id}.webp"
        except Exception:
            thumb_rel = FALLBACK_THUMB
            print(f"fallback: {book_id}")
        upsert_material(
            rows=rows,
            book_id=book_id,
            name=book_id,
            thumb_rel=thumb_rel,
            pdf_rel=str(pdf.relative_to(ROOT)).replace("\\", "/"),
        )
    save_materials(rows)
    print("done")


if __name__ == "__main__":
    main()
