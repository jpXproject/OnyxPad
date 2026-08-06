"""Konversi PNG logo menjadi favicon.ico (diperlukan Pillow).

Fitur:
- Menghapus background abu/checkerboard yang "terbakar" di PNG
  (flood-fill dari pojok, toleransi warna) -> transparan.
- Memotong hanya blok ikon mark (konten teratas), memisahkannya dari
  teks logo di bawahnya agar tetap terbaca di ukuran kecil (16-256 px).

Penggunaan:  python convert_icon.py ONYX.png
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

SIZES = [16, 24, 32, 48, 64, 128, 256]
THRESH = 60       # toleransi warna background (max selisih per kanal)
GAP_ROWS = 12     # baris transparan penuh berturut-turut = pemisah blok


def remove_background(img, thresh=THRESH):
    """Ubah region background yang terhubung ke pojok menjadi transparan."""
    img = img.convert("RGBA")
    for corner in [(1, 1), (img.width - 2, 1), (1, img.height - 2),
                   (img.width - 2, img.height - 2)]:
        ImageDraw.floodfill(img, corner, (0, 0, 0, 0), thresh=thresh)
    return img


def top_icon_block(img):
    """Ambil blok konten teratas (ikon mark), pisah dari teks di bawahnya."""
    alpha = img.getchannel("A")
    w, h = img.size
    row_has = [any(alpha.getpixel((x, y)) > 40 for x in range(w))
               for y in range(h)]
    y0 = next((y for y in range(h) if row_has[y]), 0)
    gap = None
    run = 0
    for y in range(y0, h):
        if not row_has[y]:
            run += 1
            if run >= GAP_ROWS:
                gap = y - run
                break
        else:
            run = 0
    y1 = gap if gap else h
    block = img.crop((0, y0, w, y1))
    bbox = block.getbbox()
    return block.crop(bbox) if bbox else block


def to_square(img, size=512):
    """Tengah-kan di kanvas persegi lalu resize (transparan di tepinya)."""
    w, h = img.size
    side = max(w, h)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - w) // 2, (side - h) // 2))
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def export_full_logo(src, out="docs/onyx-logo.png", width=960):
    """Hapus background lalu crop ketat seluruh logo (ikon + teks + subtitle)."""
    img = Image.open(src).convert("RGBA")
    img = remove_background(img)
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    if img.width > width:
        img = img.resize((width, int(img.height * width / img.width)),
                         Image.Resampling.LANCZOS)
    img.save(out, "PNG")
    print(f"OK -> {out} ({img.size}) - logo transparan")


def main():
    args = sys.argv[1:]
    if args and args[0] == "--logo":
        src = args[1] if len(args) > 1 else "ONYX.png"
        export_full_logo(src)
        return
    src = args[0] if args else "ONYX.png"
    out = Path("favicon.ico")
    img = Image.open(src).convert("RGBA")
    img = remove_background(img)
    mark = top_icon_block(img)
    square = to_square(mark)
    square.save(out, format="ICO", sizes=[(s, s) for s in SIZES])
    print(f"OK -> {out} ({len(SIZES)} ukuran), ikon mark {mark.size} -> "
          f"persegi {square.size}")


if __name__ == "__main__":
    main()
