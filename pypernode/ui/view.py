from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QGraphicsPathItem, QGraphicsProxyWidget, QGraphicsView

from .node_item import QNodeItem
from .sockets import QNodeSocket


class NodeView(QGraphicsView):
    def __init__(self, scene, master):
        super().__init__(scene)
        self.master = master
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setAcceptDrops(True)

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.scale(1.1, 1.1)
        else:
            self.scale(0.9, 0.9)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            node_type = event.mimeData().text()
            pos = self.mapToScene(event.pos())
            self.master.create_node(node_type, pos.x(), pos.y())
            event.acceptProposedAction()

    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if not isinstance(item, (QNodeItem, QGraphicsProxyWidget)):
            self.master.inspector.clear()

        if isinstance(item, QNodeSocket):
            self.setDragMode(QGraphicsView.NoDrag)
            self.scene().drag_start = item
            self.scene().drag_conn = QGraphicsPathItem()
            self.scene().drag_conn.setPen(QPen(Qt.white, 2, Qt.DashLine))
            self.scene().addItem(self.scene().drag_conn)
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if hasattr(self.scene(), 'drag_conn') and self.scene().drag_conn:
            p1 = self.scene().drag_start.get_scene_pos()
            p2 = self.mapToScene(event.pos())
            path = QPainterPath(p1)
            path.lineTo(p2)
            self.scene().drag_conn.setPath(path)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if hasattr(self.scene(), 'drag_conn') and self.scene().drag_conn:
            self.scene().removeItem(self.scene().drag_conn)
            self.scene().drag_conn = None
            item = self.itemAt(event.pos())
            if isinstance(item, QNodeSocket) and item != getattr(self.scene(), 'drag_start', None):
                if item.is_output != self.scene().drag_start.is_output:
                    s1, s2 = self.scene().drag_start, item
                    start = s1 if s1.is_output else s2
                    end = s2 if s1.is_output else s1
                    self.master.create_connection(start, end)
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        super().mouseReleaseEvent(event)
