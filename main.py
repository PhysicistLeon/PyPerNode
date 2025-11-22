import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QColor, QPalette

from pypernode import MainWindow


def apply_dark_theme(app: QApplication) -> None:
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, QColor(Qt.white))
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.Text, QColor(Qt.white))
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, QColor(Qt.white))
    app.setPalette(palette)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    apply_dark_theme(app)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
