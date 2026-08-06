"""Konversi PNG logo menjadi favicon.ico (diperlukan Pillow).

Penggunaan:  python convert_icon.py logo_utama.png
"""

import sys
from pathlib import Path

from PIL import Image

SIZES = [16, 24, 32, 48, 64, 128, 256]


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "assets/logo_utama.png"
    out = Path("favicon.ico")
    img = Image.open(src).convert("RGBA")
    img.save(out, format="ICO", sizes=[(s, s) for s in SIZES])
    print(f"OK -> {out} ({len(SIZES)} ukuran)")


if __name__ == "__main__":
    main()
