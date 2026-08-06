"""OnyxPad — jalankan dengan:  python main.py"""

import sys

from PySide6.QtWidgets import QApplication

from src.app import OnyxPad
from src.version import APP_NAME


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    win = OnyxPad()
    win.resize(1280, 800)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
