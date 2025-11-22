from PyQt5.QtCore import QMimeData
from PyQt5.QtWidgets import QListWidget


class NodePalette(QListWidget):
    def __init__(self):
        super().__init__()
        self.setDragEnabled(True)

    def mimeData(self, items):
        mime = QMimeData()
        if items:
            mime.setText(items[0].text())
        return mime
