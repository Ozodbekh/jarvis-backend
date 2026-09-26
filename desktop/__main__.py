import sys

from PySide6.QtWidgets import QApplication

from desktop.window import MainWindow


def main() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName("JARVIS")
    window = MainWindow()
    window.show()
    window.start()
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
