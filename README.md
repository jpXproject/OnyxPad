# NotepadBlack — Editor Split Panes Pro (PySide6)

Notepad hitam bertema gelap yang di-upgrade penuh: **split panes bertingkat gaya
tmux / VS Code**, tab per pane, syntax highlighting multi-bahasa, find &
replace, tema lengkap, sesi otomatis, dan penjelajah folder.

## Fitur

| Area | Fitur |
|---|---|
| **Split panes** | `Ctrl+\` split kanan, `Ctrl+'` split bawah, bisa split di dalam split (bertingkat) |
| **Tab per pane** | Setiap pane punya tab sendiri (drag untuk pindah posisi tab) |
| **Navigasi pane** | `Ctrl+Tab` ganti pane, `Alt+←↑→↓` fokus pane ke arahnya |
| **Syntax highlighting** | Python, JS/TS, HTML, CSS, C/C++, Java, JSON, Markdown, Shell, YAML — auto-deteksi dari ekstensi |
| **Find & replace** | `Ctrl+F` / `Ctrl+H`, opsi Aa / kata utuh / regex, hitung jumlah cocok, Ganti Semua |
| **Editor pro** | Nomor baris, highlight baris aktif, pencocokan kurung, auto-pair `(){}[]""` (termasuk overtype kutip), tab stop (Tab melompat keluar pasangan), auto-indent, indentasi 4 spasi, komentari `Ctrl+/` |
| **Multi-kursor** | `Ctrl+D` pilih kata/kemunculan berikutnya, `Ctrl+U` buang kursor terakhir, `Esc` selesai — ketik/backspace/Enter berlaku di semua kursor sekaligus |
| **Tema** | 7 tema: Dracula, One Dark, Monokai, Matrix Green, Nord, Solarized Dark, Light |
| **File explorer** | Sidebar folder (`Ctrl+Shift+O`), klik dua kali untuk buka, menu kanan: buka di pane baru |
| **Sesi** | Layout split + file terbuka + tema diingat otomatis (tersimpan di `~/.notepadblack/settings.json`) |
| **Lainnya** | Buka Cepat `Ctrl+P`, Recent files, drag&drop file ke jendela, status bar (Ln/Col/kata/encoding/bahasa/zoom), zoom `Ctrl+wheel` |

## Menjalankan

```bash
python main.py
```

## Menjalankan Test

Suite test otomatis (pytest, berjalan headless via Qt offscreen):

```bash
pip install pytest pytest-qt
pytest
```

Mencakup: editor (auto-pair, indent, komentar, I/O file), find & replace
(literal, case, kata utuh, regex), UI SearchBar (pytest-qt: visibilitas,
tombol, keyboard, replace), syntax highlighting, tema/QSS, sistem split panes
(split, navigasi, tutup, sesi), dan integrasi aplikasi (tema, sesi, recent
files, scan folder).

## Membangun .exe (opsional)

```bash
pip install pyinstaller
python -m PyInstaller --noconfirm --windowed --icon favicon.ico --name NotepadBlack ^
    --add-data "favicon.ico;." main.py
# hasil di dist/NotepadBlack/NotepadBlack.exe
```

## Pintasan Penting

```
Ctrl+\        Split kanan            Ctrl+'        Split bawah
Ctrl+Tab      Pane berikutnya        Alt+←↑→↓     Fokus pane ke arah
Ctrl+S        Simpan                 Ctrl+Shift+S Simpan sebagai
Ctrl+Alt+S    Simpan semua           Ctrl+W        Tutup tab
Ctrl+Shift+W  Tutup pane             Ctrl+F/H      Cari / Ganti
Ctrl+P        Buka cepat             Ctrl+/        Komentari
Ctrl+G        Pergi ke baris         F1            Pintasan lengkap
Ctrl+D        Pilih kata berikutnya   Ctrl+U        Buang kursor terakhir
```
