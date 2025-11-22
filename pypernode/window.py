import json
from PyQt5.QtCore import QThreadPool, pyqtSignal
from PyQt5.QtGui import QColor, QPainterPath, QPen
from PyQt5.QtWidgets import (
    QGraphicsScene,
    QHBoxLayout,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QWidget,
)

from .execution import ExecutionWorker
from .models import NodeData
from .registry import NodeRegistry
from .ui.connection_item import ConnectionItem
from .ui.inspector import InspectorWidget
from .ui.node_item import QNodeItem
from .ui.palette import NodePalette
from .ui.view import NodeView


class MainWindow(QMainWindow):
    inspector_refresh_needed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.resize(1300, 800)
        self.setWindowTitle("Final Python Node Editor")

        self.nodes = {}
        self.connections = []

        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QColor("#222"))
        self.view = NodeView(self.scene, self)

        self.palette = NodePalette()
        for t in NodeRegistry.get_all_types():
            self.palette.addItem(t)

        self.inspector = InspectorWidget()
        self.inspector_refresh_needed.connect(
            lambda: self.inspector.set_node(self.inspector.current_node) if self.inspector.current_node else None
        )

        main_widget = QWidget()
        layout = QHBoxLayout(main_widget)

        splitter = QSplitter()
        splitter.addWidget(self.palette)
        splitter.addWidget(self.view)
        splitter.addWidget(self.inspector)
        splitter.setSizes([150, 800, 300])

        layout.addWidget(splitter)
        self.setCentralWidget(main_widget)

        tb = self.addToolBar("Actions")
        tb.addAction("Run Workflow", self.run_workflow)
        tb.addSeparator()
        tb.addAction("Save JSON", self.save_json)
        tb.addAction("Load JSON", self.load_json)
        tb.addAction("Export Python", self.export_python)
        tb.addSeparator()
        tb.addAction("Clear", self.clear_graph)
        tb.addAction("Delete Selected", self.delete_selected_nodes)

        self.threadpool = QThreadPool()

    def create_node(self, type_name, x, y, id=None, params=None, code=None):
        node = NodeData(type_name, x, y, id)
        if params:
            node.params = params
        if code:
            node.code = code
        self.nodes[node.id] = node

        item = QNodeItem(node, self)
        item.setPos(x, y)
        self.scene.addItem(item)
        return item

    def create_connection(self, start_s, end_s):
        connection_item = ConnectionItem(self)
        connection_item.setPen(QPen(QColor("#AAA"), 2))
        self.scene.addItem(connection_item)
        self.connections.append({'item': connection_item, 'start': start_s, 'end': end_s})
        self.update_connections()

    def update_connections(self):
        for c in self.connections:
            p1 = c['start'].get_scene_pos()
            p2 = c['end'].get_scene_pos()
            if isinstance(c['item'], ConnectionItem):
                c['item'].update_path(p1, p2)
            else:
                path = QPainterPath(p1)
                dx = p2.x() - p1.x()
                path.cubicTo(p1.x() + dx * 0.5, p1.y(), p2.x() - dx * 0.5, p2.y(), p2.x(), p2.y())
                c['item'].setPath(path)

    def remove_connection(self, connection_item: ConnectionItem):
        to_remove = None
        for c in self.connections:
            if c['item'] is connection_item:
                to_remove = c
                break

        if to_remove:
            self.scene.removeItem(to_remove['item'])
            self.connections.remove(to_remove)
            self.inspector_refresh_needed.emit()

    def get_logical_conns(self):
        conns = []
        for c in self.connections:
            start_node = c['start'].parentItem().node_data
            end_node = c['end'].parentItem().node_data
            conns.append({
                'start_node': start_node.id,
                'start_socket': c['start'].index,
                'end_node': end_node.id,
                'end_socket': c['end'].index,
            })
        return conns

    def find_item(self, nid):
        for item in self.scene.items():
            if isinstance(item, QNodeItem) and item.node_data.id == nid:
                return item
        return None

    def run_workflow(self):
        worker = ExecutionWorker(self.nodes, self.get_logical_conns())
        worker.signals.node_completed.connect(self.on_node_done)
        worker.signals.error.connect(lambda e: QMessageBox.critical(self, "Error", e))
        self.threadpool.start(worker)

    def on_node_done(self, nid, res):
        item = self.find_item(nid)
        if item:
            item.update_result_label()
        if self.inspector.current_node and self.inspector.current_node.id == nid:
            self.inspector.set_node(self.inspector.current_node)

    def clear_graph(self):
        self.scene.clear()
        self.nodes = {}
        self.connections = []
        self.inspector.clear()

    def delete_selected_nodes(self):
        selected = [i for i in self.scene.selectedItems() if isinstance(i, QNodeItem)]
        for item in selected:
            self._delete_node_item(item)

    def _delete_node_item(self, item: QNodeItem):
        conns_to_remove = []
        for c in self.connections:
            if c['start'].parentItem() == item or c['end'].parentItem() == item:
                self.scene.removeItem(c['item'])
                conns_to_remove.append(c)

        for c in conns_to_remove:
            self.connections.remove(c)

        nid = item.node_data.id
        self.scene.removeItem(item)
        self.nodes.pop(nid, None)
        if self.inspector.current_node and self.inspector.current_node.id == nid:
            self.inspector.clear()

    def save_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save", "", "JSON (*.json)")
        if not path:
            return

        data = {"nodes": [], "connections": self.get_logical_conns()}
        for nid, n in self.nodes.items():
            item = self.find_item(nid)
            if item:
                n.x, n.y = item.x(), item.y()

            data["nodes"].append({
                "id": n.id, "type": n.type, "x": n.x, "y": n.y,
                "params": n.params, "code": n.code,
            })

        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def load_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load", "", "JSON (*.json)")
        if not path:
            return

        with open(path, 'r') as f:
            data = json.load(f)
        self.clear_graph()

        for n in data['nodes']:
            self.create_node(n['type'], n['x'], n['y'], n['id'], n['params'], n.get('code'))

        for c in data['connections']:
            s_item = self.find_item(c['start_node'])
            e_item = self.find_item(c['end_node'])
            if s_item and e_item:
                try:
                    s_sock = s_item.sockets['out'][c['start_socket']]
                    e_sock = e_item.sockets['in'][c['end_socket']]
                    self.create_connection(s_sock, e_sock)
                except Exception:
                    pass

    def export_python(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Python", "", "Python (*.py)")
        if not path:
            return

        script = "# Auto-Generated Workflow\n\n"
        script += "def run_workflow():\n"
        script += "    results = {}\n"

        conns = self.get_logical_conns()
        adj = {n: [] for n in self.nodes}
        in_degree = {n: 0 for n in self.nodes}
        for c in conns:
            adj[c['start_node']].append(c['end_node'])
            in_degree[c['end_node']] += 1

        queue = [n for n in self.nodes if in_degree[n] == 0]
        sorted_ids = []
        while queue:
            u = queue.pop(0)
            sorted_ids.append(u)
            for v in adj[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)

        for nid in sorted_ids:
            node = self.nodes[nid]
            script += f"\n    # Node: {node.type} ({nid})\n"
            script += f"    params = {node.params}\n"

            input_dict_str = "{"
            for i, inp_name in enumerate(node.inputs):
                src = "0.0"
                for c in conns:
                    if c['end_node'] == nid and c['end_socket'] == i:
                        s_node = self.nodes[c['start_node']]
                        s_out = s_node.outputs[c['start_socket']]
                        src = f"results.get('{c['start_node']}', {{}}).get('{s_out}', 0.0)"
                input_dict_str += f"'{inp_name}': {src}, "
            input_dict_str += "}"

            script += f"    inputs = {input_dict_str}\n"
            script += "    outputs = {}\n"

            code_lines = node.code.split('\n')
            for line in code_lines:
                script += f"    {line}\n"

            script += f"    results['{nid}'] = outputs\n"
            script += f"    print(f'Node {nid} Result: {{outputs}}')\n"

        script += "\nif __name__ == '__main__':\n    run_workflow()"

        with open(path, 'w') as f:
            f.write(script)
        QMessageBox.information(self, "Export", "Python script exported successfully.")
