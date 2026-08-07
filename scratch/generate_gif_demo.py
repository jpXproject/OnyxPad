"""Generator Animated GIF Demo untuk Terminal & Asciinema Recorder OnyxPad."""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Path folder keluaran
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = PROJECT_ROOT / "docs" / "demo"
DEMO_DIR.mkdir(parents=True, exist_ok=True)
GIF_PATH = DEMO_DIR / "terminal-asciinema.gif"

# Konfigurasi Dimensi & Warna (Dracula / Catppuccin Theme)
WIDTH, HEIGHT = 760, 440
BG_COLOR = (24, 24, 37)        # #181825
HEADER_BG = (30, 30, 46)       # #1e1e2e
TERM_BG = (17, 17, 27)         # #11111b
BORDER_COLOR = (69, 71, 90)    # #45475a
TEXT_COLOR = (205, 214, 244)   # #cdd6f4
GREEN_COLOR = (166, 227, 161)  # #a6e3a1
CYAN_COLOR = (148, 226, 213)   # #94e2d5
RED_COLOR = (243, 139, 168)    # #f38ba8
BLUE_COLOR = (137, 180, 250)   # #89b4fa
YELLOW_COLOR = (249, 226, 175) # #f9e2af

# Load Font
try:
    font_main = ImageFont.truetype("consola.ttf", 15)
    font_bold = ImageFont.truetype("consolab.ttf", 15)
    font_sm = ImageFont.truetype("arial.ttf", 12)
except Exception:
    font_main = ImageFont.load_default()
    font_bold = font_main
    font_sm = font_main

def draw_base_ui(draw, rec_active=True, rec_blink=True):
    # Window Frame & Shadow
    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=BG_COLOR)
    
    # Header Bar
    draw.rectangle([0, 0, WIDTH, 35], fill=HEADER_BG)
    draw.line([0, 35, WIDTH, 35], fill=BORDER_COLOR, width=1)
    
    # Window Buttons (Mac/Linux Style Dots)
    draw.ellipse([12, 12, 22, 22], fill=(255, 95, 86))
    draw.ellipse([28, 12, 38, 22], fill=(255, 189, 46))
    draw.ellipse([44, 12, 54, 22], fill=(39, 201, 63))
    
    # Title
    draw.text((70, 10), "OnyxPad Pro — Embedded Terminal & Asciinema Recorder", fill=TEXT_COLOR, font=font_sm)

    # Terminal Toolbar
    draw.rectangle([10, 45, WIDTH - 10, 80], fill=HEADER_BG, outline=BORDER_COLOR)
    draw.text((20, 53), "Shell: [ PowerShell v7 ]  |  [ 🧹 Clear ]  [ 🔄 Restart ]", fill=TEXT_COLOR, font=font_sm)
    
    # REC Button Status
    rec_x = WIDTH - 240
    if rec_active:
        dot_color = RED_COLOR if rec_blink else (100, 40, 50)
        draw.ellipse([rec_x, 57, rec_x + 10, 67], fill=dot_color)
        draw.text((rec_x + 15, 53), "REC RECORDING (.cast)", fill=RED_COLOR if rec_blink else TEXT_COLOR, font=font_sm)
    else:
        draw.text((rec_x + 15, 53), "⏺ Rekam Asciinema", fill=TEXT_COLOR, font=font_sm)
        
    draw.text((WIDTH - 90, 53), "[ ▶ Putar .cast ]", fill=BLUE_COLOR, font=font_sm)

    # Terminal Body Area
    draw.rectangle([10, 85, WIDTH - 10, HEIGHT - 15], fill=TERM_BG, outline=BORDER_COLOR)

def create_frames():
    frames = []

    lines_history = [
        ("\x1b[36mWelcome to OnyxPad Pro Integrated Terminal v2.5\x1b[0m", CYAN_COLOR),
        ("Type commands or press Ctrl+Shift+R to record session into .cast format", TEXT_COLOR),
        ("", TEXT_COLOR),
    ]

    prompt = "PS C:\\Users\\XCODE\\notepadblack> "
    target_cmd = "python -m pytest tests/test_terminal_recorder.py"
    
    # Phase 1: Typing command letter by letter
    typed_text = ""
    for i in range(len(target_cmd) + 1):
        typed_text = target_cmd[:i]
        
        img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(img)
        draw_base_ui(draw, rec_active=True, rec_blink=(i % 2 == 0))
        
        # Render historical lines
        y = 95
        for text, color in lines_history:
            draw.text((20, y), text, fill=color, font=font_main)
            y += 22

        # Render prompt & current typing
        draw.text((20, y), prompt, fill=GREEN_COLOR, font=font_bold)
        prompt_w = draw.textlength(prompt, font=font_bold)
        draw.text((20 + prompt_w, y), typed_text + ("█" if (i % 2 == 0) else " "), fill=TEXT_COLOR, font=font_main)

        frames.append((img, 120))

    # Phase 2: Press Enter & Output Execution Results
    output_lines = [
        (prompt + target_cmd, TEXT_COLOR),
        ("======================== test session starts ========================", CYAN_COLOR),
        ("platform win32 -- Python 3.13.7, pytest-8.3.4", TEXT_COLOR),
        ("collected 6 items", TEXT_COLOR),
        ("tests/test_terminal_recorder.py ......                    [100%]", GREEN_COLOR),
        ("162 passed in 15.92s", GREEN_COLOR),
        ("", TEXT_COLOR),
        ("[Asciinema] Session recorded! Saved to docs/demo/onyxpad_terminal_demo.cast", YELLOW_COLOR),
        (prompt, GREEN_COLOR)
    ]

    for frame_step in range(1, len(output_lines) + 1):
        img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(img)
        draw_base_ui(draw, rec_active=(frame_step < len(output_lines) - 1), rec_blink=(frame_step % 2 == 0))

        y = 95
        for text, color in lines_history:
            draw.text((20, y), text, fill=color, font=font_main)
            y += 22

        for text, color in output_lines[:frame_step]:
            if text.startswith("PS C:"):
                draw.text((20, y), prompt, fill=GREEN_COLOR, font=font_bold)
            else:
                draw.text((20, y), text, fill=color, font=font_main)
            y += 22

        frames.append((img, 400 if frame_step in (len(output_lines)-1, len(output_lines)) else 250))

    # Hold last frame
    for _ in range(8):
        img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(img)
        draw_base_ui(draw, rec_active=False, rec_blink=False)
        y = 95
        for text, color in lines_history:
            draw.text((20, y), text, fill=color, font=font_main)
            y += 22
        for text, color in output_lines:
            if text.startswith("PS C:"):
                draw.text((20, y), prompt, fill=GREEN_COLOR, font=font_bold)
            else:
                draw.text((20, y), text, fill=color, font=font_main)
            y += 22
        draw.text((20 + draw.textlength(prompt, font=font_bold), y - 22), "█", fill=TEXT_COLOR, font=font_main)
        frames.append((img, 300))

    return frames

def main():
    print("Membuat animasi demo GIF untuk Terminal & Asciinema Recorder...")
    frames_data = create_frames()
    images = [f[0] for f in frames_data]
    durations = [f[1] for f in frames_data]

    images[0].save(
        GIF_PATH,
        save_all=True,
        append_images=images[1:],
        optimize=True,
        duration=durations,
        loop=0
    )
    print(f"[OK] GIF berhasil dibuat dan disimpan di: {GIF_PATH}")

if __name__ == "__main__":
    main()
