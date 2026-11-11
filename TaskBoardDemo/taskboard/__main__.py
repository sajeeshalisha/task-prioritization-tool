import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .ui import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("TaskBoard")
    # The process is Python itself, so without this the Dock shows Python's icon.
    app.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), "resources", "icon.png")))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
