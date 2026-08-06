"""Konversi logo PNG menjadi favicon.ico dan PNG transparan (perlu Pillow).

Mode:
    python convert_icon.py                # favicon.ico (multi-ukuran 16-256)
    python convert_icon.py --logo         # docs/onyx-logo.png (logo penuh)
    python convert_icon.py --mark         # docs/icon-mark.png (ikon saja)
    python convert_icon.py --all          # ketiganya sekaligus

Opsional:
    python convert_icon.py FOTO.png --out hasil.png --mark
      FOTO.png   sumber logo (default ONYX.png)
      --logo / --mark / --all   pilih mode
      --out PATH                ganti lokasi output (mode ico/logo/mark)
      -h, --help                bantuan ini

Background abu/checkerboard yang "terbakar" di PNG dihapus otomatis
(flood-fill dari tepi pada versi kecil + threshold vektor numpy) sehingga
semua hasilnya transparan.
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

SIZES = [16, 24, 32, 48, 64, 128, 256]
NEAR_WHITE = 195   # minimal kecerahan background
COLOR_TOL = 40     # toleransi selisih antar kanal (abu/checkerboard)
PROBE = 256        # ukuran versi kecil untuk flood-fill


# ------------------------------------------------------------- background
def _remove_bg_numpy(img):
    import numpy as np

    arr = np.array(img.convert("RGBA"))
    r, g, b, a = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]
    mn = np.minimum(np.minimum(r, g), b)
    mx = np.maximum(np.maximum(r, g), b)
    cand = (mn >= NEAR_WHITE) & ((mx - mn) <= COLOR_TOL)

    # flood-fill BFS pada versi kecil: region background yang terhubung ke tepi
    step = max(1, img.width // PROBE)
    small = cand[::step, ::step]
    h, w = small.shape
    out = np.zeros_like(small)
    stack = []
    for x in range(w):
        if small[0, x]:
            stack.append((0, x))
        if small[h - 1, x]:
            stack.append((h - 1, x))
    for y in range(h):
        if small[y, 0]:
            stack.append((y, 0))
        if small[y, w - 1]:
            stack.append((y, w - 1))
    while stack:
        y, x = stack.pop()
        if not (0 <= y < h and 0 <= x < w) or out[y, x] or not small[y, x]:
            continue
        out[y, x] = True
        stack.append((y + 1, x))
        stack.append((y - 1, x))
        stack.append((y, x + 1))
        stack.append((y, x - 1))

    # naikkan kembali ke resolusi penuh (nearest) lalu irisan dengan cand
    bg = np.kron(out, np.ones((step, step), dtype=bool))
    bg = bg[: img.height, : img.width]
    arr[..., 3] = np.where(cand & bg, 0, a)
    return Image.fromarray(arr)


def _remove_bg_slow(img):
    """Fallback tanpa numpy: flood-fill Pillow dari 4 pojok."""
    for corner in [(1, 1), (img.width - 2, 1), (1, img.height - 2),
                   (img.width - 2, img.height - 2)]:
        ImageDraw.floodfill(img, corner, (0, 0, 0, 0), thresh=60)
    return img


def remove_background(img):
    try:
        return _remove_bg_numpy(img)
    except ImportError:
        return _remove_bg_slow(img)


# ------------------------------------------------------------- pemotongan
GAP_ROWS = 12  # baris transparan penuh berturut-turut = pemisah blok


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


# ------------------------------------------------------------- ekspor
def export_ico(img, out="favicon.ico"):
    img = remove_background(img)
    mark = top_icon_block(img)
    square = to_square(mark)
    square.save(out, format="ICO", sizes=[(s, s) for s in SIZES])
    print(f"OK -> {out} ({len(SIZES)} ukuran, ikon mark {mark.size})")


def export_logo(img, out="docs/onyx-logo.png", width=960):
    img = remove_background(img)
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    if img.width > width:
        img = img.resize((width, int(img.height * width / img.width)),
                         Image.Resampling.LANCZOS)
    img.save(out, "PNG")
    print(f"OK -> {out} ({img.size}) logo transparan")


def export_mark(img, out="docs/icon-mark.png", size=512):
    img = remove_background(img)
    mark = top_icon_block(img)
    square = to_square(mark, size=size)
    square.save(out, "PNG")
    print(f"OK -> {out} ({square.size}) ikon transparan")


USAGE = __doc__.strip()


def main():
    args = sys.argv[1:]
    if not args or any(a in ("-h", "--help") for a in args):
        print(USAGE)
        return
    src = "ONYX.png"
    out = None
    modes = set()
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--logo", "--mark", "--all"):
            modes.add(a[2:])
        elif a == "--out":
            i += 1
            if i < len(args):
                out = args[i]
        elif not a.startswith("-"):
            src = a
        i += 1
    if not modes:
        modes.add("ico")

    img = Image.open(src).convert("RGBA")
    if "all" in modes:
        export_ico(img, out or "favicon.ico")
        export_logo(img, out or "docs/onyx-logo.png")
        export_mark(img, out or "docs/icon-mark.png")
        return
    if "ico" in modes:
        export_ico(img, out or "favicon.ico")
    if "logo" in modes:
        export_logo(img, out or "docs/onyx-logo.png")
    if "mark" in modes:
        export_mark(img, out or "docs/icon-mark.png")


if __name__ == "__main__":
    main()
