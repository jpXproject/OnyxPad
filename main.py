import sys
import traceback

from PySide6.QtWidgets import QApplication

from src.app import SETTINGS_DIR, OnyxPad
from src.version import APP_NAME


def global_excepthook(exc_type, exc_value, exc_tb):
    """Global exception handler to log errors without abrupt crashing."""
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    sys.__excepthook__(exc_type, exc_value, exc_tb)
    try:
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_DIR / "crash.log", "a", encoding="utf-8") as f:
            f.write(f"--- Crash Report ---\n{msg}\n")
    except Exception:
        pass


def main():
    sys.excepthook = global_excepthook
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    win = OnyxPad()
    win.resize(1280, 800)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
