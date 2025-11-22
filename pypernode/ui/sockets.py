from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QPen, QPainter
from PyQt5.QtWidgets import QGraphicsItem

from ..node_types import ValueType


class QNodeSocket(QGraphicsItem):
    def __init__(self, parent, name, index, is_output, value_type: ValueType):
        super().__init__(parent)
        self.name = name
        self.index = index
        self.is_output = is_output
        self.value_type = value_type
        self.radius = 6
        self.setAcceptHoverEvents(True)
        self.color = QColor(value_type.color())
        self.setToolTip(f"{name}: {value_type.value}")

    def boundingRect(self):
        return QRectF(-self.radius, -self.radius, 2 * self.radius, 2 * self.radius)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setBrush(self.color)
        painter.setPen(Qt.white)
        painter.drawEllipse(-self.radius, -self.radius, 2 * self.radius, 2 * self.radius)

    def get_scene_pos(self):
        return self.mapToScene(0, 0)
