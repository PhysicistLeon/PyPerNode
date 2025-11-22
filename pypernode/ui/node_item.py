from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsProxyWidget, QTextEdit

from ..models import NodeData
from .sockets import QNodeSocket


class QNodeItem(QGraphicsItem):
    def __init__(self, node_data: NodeData, master):
        super().__init__()
        self.node_data = node_data
        self.master = master
        self.width = 180
        self.base_height = 80
        self.radius = 8
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)

        self.is_code_visible = False
        self.code_proxy = None
        self.result_text = "..."

        self._init_sockets()
        self._init_ui()

    def _init_sockets(self):
        self.sockets = {'in': [], 'out': []}
        y = 40
        for i, sock in enumerate(self.node_data.input_defs):
            s = QNodeSocket(self, sock.name, i, False, sock.type)
            s.setPos(0, y)
            self.sockets['in'].append(s)
            y += 22

        y = 40
        for i, sock in enumerate(self.node_data.output_defs):
            s = QNodeSocket(self, sock.name, i, True, sock.type)
            s.setPos(self.width, y)
            self.sockets['out'].append(s)
            y += 22

        self.base_height = max(80, y + 10)

    def _init_ui(self):
        te = QTextEdit(self.node_data.code)
        te.setStyleSheet("QTextEdit { background: #1e1e1e; color: #ddd; font-family: Consolas; border: 1px solid #444; }")
        te.setMinimumSize(160, 100)
        te.textChanged.connect(self._on_code_changed)
        self.code_proxy = QGraphicsProxyWidget(self)
        self.code_proxy.setWidget(te)
        self.code_proxy.setPos(10, self.base_height + 5)
        self.code_proxy.hide()

    def _on_code_changed(self):
        self.node_data.code = self.code_proxy.widget().toPlainText()
        self.master.inspector_refresh_needed.emit()

    def toggle_code(self):
        self.is_code_visible = not self.is_code_visible
        if self.is_code_visible:
            self.code_proxy.show()
        else:
            self.code_proxy.hide()
        self.update()

    def update_result_label(self):
        if self.node_data.last_error:
            self.result_text = "Error"
        elif self.node_data.last_output:
            vals = list(self.node_data.last_output.values())
            if vals:
                v = vals[0]
                self.result_text = f"{v:.2f}" if isinstance(v, (int, float)) else str(v)
            else:
                self.result_text = "Done"
        else:
            self.result_text = "..."
        self.update()

    def boundingRect(self):
        h = self.base_height + 25
        if self.is_code_visible:
            h += 110
        return QRectF(0, 0, self.width, h)

    def paint(self, painter: QPainter, option, widget=None):
        rect = self.boundingRect()
        path = QPainterPath()
        path.addRoundedRect(rect, self.radius, self.radius)
        painter.setBrush(QColor("#333"))
        painter.setPen(QPen(QColor("#111"), 1))
        painter.drawPath(path)

        painter.setBrush(QColor("#444"))
        painter.drawRoundedRect(0, 0, self.width, 25, self.radius, self.radius)
        painter.drawRect(0, 15, self.width, 10)

        painter.setPen(Qt.white)
        painter.drawText(QRectF(0, 0, self.width, 25), Qt.AlignCenter, self.node_data.type)

        painter.setBrush(QColor("#555"))
        painter.drawRoundedRect(self.width - 25, 2, 20, 20, 3, 3)
        painter.drawText(QRectF(self.width - 25, 2, 20, 20), Qt.AlignCenter, "<>")

        painter.setPen(QColor("#AAA"))
        for s in self.sockets['in']:
            painter.drawText(QRectF(15, s.y() - 10, 100, 20), Qt.AlignLeft | Qt.AlignVCenter, s.name)
        for s in self.sockets['out']:
            painter.drawText(QRectF(0, s.y() - 10, self.width - 15, 20), Qt.AlignRight | Qt.AlignVCenter, s.name)

        res_y = self.base_height
        painter.setPen(Qt.green if not self.node_data.last_error else Qt.red)
        painter.drawText(QRectF(0, res_y, self.width, 20), Qt.AlignCenter, self.result_text)

        if self.isSelected():
            painter.setPen(QPen(Qt.yellow, 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect, self.radius, self.radius)

        if self.node_data.last_error:
            painter.setPen(QPen(Qt.red, 2))
            painter.drawRoundedRect(rect, self.radius, self.radius)

    def mousePressEvent(self, event):
        if event.pos().x() > self.width - 25 and event.pos().y() < 25:
            self.toggle_code()
            return
        self.master.inspector.set_node(self.node_data)
        super().mousePressEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.master.update_connections()
        return super().itemChange(change, value)
