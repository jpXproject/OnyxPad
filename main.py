"""NotepadBlack — jalankan dengan:  python main.py"""

import sys

from PySide6.QtWidgets import QApplication

from src.app import NotepadBlack


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("NotepadBlack")
    app.setOrganizationName("NotepadBlack")
    win = NotepadBlack()
    win.resize(1280, 800)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
