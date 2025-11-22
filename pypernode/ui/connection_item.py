from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QPainter, QPainterPath
from PyQt5.QtWidgets import QGraphicsPathItem


class ConnectionItem(QGraphicsPathItem):
    """Visual representation of a connection with an explicit delete handle."""

    def __init__(self, master):
        super().__init__()
        self.master = master
        self.setZValue(-1)
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsPathItem.ItemIsSelectable, True)
        self.default_color = QColor("#AAA")
        self.highlight_color = QColor("#FFD166")
        self.handle_pos = QPointF()
        self.handle_radius = 8
        self.setToolTip("Click the handle to remove this connection")

    def update_path(self, p1: QPointF, p2: QPointF) -> None:
        path = QPainterPath(p1)
        dx = p2.x() - p1.x()
        path.cubicTo(p1.x() + dx * 0.5, p1.y(), p2.x() - dx * 0.5, p2.y(), p2.x(), p2.y())
        self.setPath(path)
        self.handle_pos = QPointF((p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2)

    def hoverEnterEvent(self, event):
        self.setPen(self._make_pen(self.highlight_color))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setPen(self._make_pen(self.default_color))
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if (event.pos() - self.handle_pos).manhattanLength() <= self.handle_radius * 1.2:
            self.master.remove_connection(self)
            return
        super().mousePressEvent(event)

    def paint(self, painter: QPainter, option, widget=None):
        if not self.pen().color().isValid():
            self.setPen(self._make_pen(self.default_color))
        super().paint(painter, option, widget)

        painter.setBrush(QColor("#C44536"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(self.handle_pos, self.handle_radius, self.handle_radius)

        painter.setPen(Qt.white)
        painter.drawText(
            QRectF(
                self.handle_pos.x() - self.handle_radius,
                self.handle_pos.y() - self.handle_radius,
                self.handle_radius * 2,
                self.handle_radius * 2,
            ),
            Qt.AlignCenter,
            "✕",
        )

    def _make_pen(self, color: QColor):
        pen = self.pen()
        pen.setColor(color)
        pen.setWidth(2)
        return pen
