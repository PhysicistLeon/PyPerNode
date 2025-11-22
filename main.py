import sys
import json
import hashlib
import time
from collections import OrderedDict
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# ==============================================================================
# 1. NODE REGISTRY & LOGIC
# ==============================================================================

class NodeRegistry:
    _definitions = {}

    @classmethod
    def register_node(cls, type_name, inputs, outputs, code, params=None):
        cls._definitions[type_name] = {
            'inputs': inputs,
            'outputs': outputs,
            'code': code,
            'params': params or {}
        }

    @classmethod
    def get_definition(cls, type_name):
        return cls._definitions.get(type_name, None)

    @classmethod
    def get_all_types(cls):
        return list(cls._definitions.keys())

# Register Standard Nodes
NodeRegistry.register_node('Constant', [], ['Val'], 
    code="outputs['Val'] = float(params['value'])",
    params={'value': 0.0})

NodeRegistry.register_node('Add', ['A', 'B'], ['Result'], 
    code="outputs['Result'] = inputs['A'] + inputs['B']")

NodeRegistry.register_node('Subtract', ['A', 'B'], ['Result'], 
    code="outputs['Result'] = inputs['A'] - inputs['B']")

NodeRegistry.register_node('Multiply', ['A', 'B'], ['Result'], 
    code="outputs['Result'] = inputs['A'] * inputs['B']")

NodeRegistry.register_node('Divide', ['A', 'B'], ['Result'], 
    code="if inputs['B'] == 0: raise ValueError('Div by Zero')\noutputs['Result'] = inputs['A'] / inputs['B']")

NodeRegistry.register_node('Output', ['In'], [], 
    code="pass # Data is simply cached")

NodeRegistry.register_node('Custom', ['x', 'y'], ['out'], 
    code="# Custom Python Code\nimport math\noutputs['out'] = math.sqrt(inputs['x']**2 + inputs['y']**2)")

# ==============================================================================
# 2. DATA MODELS
# ==============================================================================

class NodeData:
    def __init__(self, node_type, x=0, y=0, id=None):
        self.id = id if id else str(int(time.time() * 1000)) + str(id)
        self.type = node_type
        self.x = x
        self.y = y
        
        defn = NodeRegistry.get_definition(node_type)
        if not defn:
            defn = {'inputs': [], 'outputs': [], 'code': 'pass', 'params': {}}

        self.inputs = defn['inputs'][:]
        self.outputs = defn['outputs'][:]
        self.code = defn['code']
        self.params = defn['params'].copy()
        
        # Runtime State
        self.last_output = {} # {pin_name: value}
        self.last_error = None
        self.cache_hash = None

    def compute_hash(self, input_values):
        hasher = hashlib.sha256()
        hasher.update(json.dumps(self.params, sort_keys=True).encode('utf-8'))
        hasher.update(self.code.encode('utf-8'))
        hasher.update(str(input_values).encode('utf-8'))
        return hasher.hexdigest()

    def execute(self, input_data):
        local_scope = {'inputs': input_data, 'outputs': {}, 'params': self.params}
        exec(self.code, {}, local_scope)
        return local_scope['outputs']

# ==============================================================================
# 3. EXECUTION ENGINE
# ==============================================================================

class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    node_started = pyqtSignal(str)
    node_completed = pyqtSignal(str, object) # id, result
    node_error = pyqtSignal(str, str)

class ExecutionWorker(QRunnable):
    def __init__(self, nodes, connections):
        super().__init__()
        self.nodes = nodes 
        self.connections = connections 
        self.signals = WorkerSignals()

    def run(self):
        try:
            # Build Graph
            adj = {n: [] for n in self.nodes}
            in_degree = {n: 0 for n in self.nodes}
            input_map = {n: {} for n in self.nodes} 

            for conn in self.connections:
                start_node, end_node = conn['start_node'], conn['end_node']
                try:
                    s_node = self.nodes[start_node]
                    e_node = self.nodes[end_node]
                    src_pin = s_node.outputs[conn['start_socket']]
                    tgt_pin = e_node.inputs[conn['end_socket']]
                    
                    adj[start_node].append(end_node)
                    in_degree[end_node] += 1
                    input_map[end_node][tgt_pin] = (start_node, src_pin)
                except: continue # Skip broken connections

            # Topo Sort
            queue = [n for n in self.nodes if in_degree[n] == 0]
            sorted_nodes = []
            while queue:
                u = queue.pop(0)
                sorted_nodes.append(u)
                for v in adj[u]:
                    in_degree[v] -= 1
                    if in_degree[v] == 0: queue.append(v)

            if len(sorted_nodes) != len(self.nodes):
                raise Exception("Cycle detected! Graph must be acyclic.")

            # Execution
            results_cache = {} 
            for nid in sorted_nodes:
                node = self.nodes[nid]
                self.signals.node_started.emit(nid)
                
                # Prepare Inputs
                node_inputs = {}
                for in_name in node.inputs:
                    if in_name in input_map[nid]:
                        src_id, src_pin = input_map[nid][in_name]
                        node_inputs[in_name] = results_cache.get(src_id, {}).get(src_pin, 0.0)
                    else:
                        node_inputs[in_name] = 0.0

                # Caching Logic
                cur_hash = node.compute_hash(node_inputs)
                if node.cache_hash == cur_hash and not node.last_error and node.last_output:
                    results_cache[nid] = node.last_output
                    self.signals.node_completed.emit(nid, node.last_output)
                    time.sleep(0.05)
                    continue

                # Run Node
                try:
                    outs = node.execute(node_inputs)
                    results_cache[nid] = outs
                    node.last_output = outs
                    node.last_error = None
                    node.cache_hash = cur_hash
                    self.signals.node_completed.emit(nid, outs)
                except Exception as e:
                    node.last_error = str(e)
                    self.signals.node_error.emit(nid, str(e))
                    raise e
                
                time.sleep(0.1) # UI Visual Delay

            self.signals.finished.emit()
        except Exception as e:
            self.signals.error.emit(str(e))

# ==============================================================================
# 4. GRAPHICS & UI COMPONENTS
# ==============================================================================

class QNodeSocket(QGraphicsItem):
    def __init__(self, parent, name, index, is_output):
        super().__init__(parent)
        self.name = name
        self.index = index
        self.is_output = is_output
        self.radius = 5
        self.setAcceptHoverEvents(True)
        self.color = QColor("#FF7700") if is_output else QColor("#0077FF")

    def boundingRect(self):
        return QRectF(-self.radius, -self.radius, 2*self.radius, 2*self.radius)

    def paint(self, painter, option, widget):
        painter.setBrush(self.color)
        painter.setPen(Qt.white)
        painter.drawEllipse(-self.radius, -self.radius, 2*self.radius, 2*self.radius)

    def get_scene_pos(self):
        return self.mapToScene(0, 0)

class QNodeItem(QGraphicsItem):
    def __init__(self, node_data, master):
        super().__init__()
        self.node_data = node_data
        self.master = master
        self.width = 180
        self.base_height = 80
        self.radius = 8
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        
        # UI State
        self.is_code_visible = False
        self.code_proxy = None
        self.result_text = "..."
        
        self._init_sockets()
        self._init_ui()

    def _init_sockets(self):
        self.sockets = {'in': [], 'out': []}
        # Inputs
        y = 40
        for i, n in enumerate(self.node_data.inputs):
            s = QNodeSocket(self, n, i, False)
            s.setPos(0, y)
            self.sockets['in'].append(s)
            y += 22
        
        # Outputs
        y = 40
        for i, n in enumerate(self.node_data.outputs):
            s = QNodeSocket(self, n, i, True)
            s.setPos(self.width, y)
            self.sockets['out'].append(s)
            y += 22
        
        self.base_height = max(80, y + 10)

    def _init_ui(self):
        # Inline Params (e.g. Constant)
        if self.node_data.type == 'Constant':
            le = QLineEdit(str(self.node_data.params.get('value', 0.0)))
            le.setFixedWidth(60)
            le.setStyleSheet("QLineEdit { background: #222; color: white; border: 1px solid #555; }")
            le.textChanged.connect(self._on_param_changed)
            proxy = QGraphicsProxyWidget(self)
            proxy.setWidget(le)
            proxy.setPos(50, 38)

        # Code Editor (Hidden)
        te = QTextEdit(self.node_data.code)
        te.setStyleSheet("QTextEdit { background: #1e1e1e; color: #ddd; font-family: Consolas; border: 1px solid #444; }")
        te.setMinimumSize(160, 100)
        te.textChanged.connect(self._on_code_changed)
        self.code_proxy = QGraphicsProxyWidget(self)
        self.code_proxy.setWidget(te)
        self.code_proxy.setPos(10, self.base_height + 5)
        self.code_proxy.hide()

    def _on_param_changed(self, txt):
        try: self.node_data.params['value'] = float(txt)
        except: pass
        self.master.inspector_refresh_needed.emit()

    def _on_code_changed(self):
        self.node_data.code = self.code_proxy.widget().toPlainText()
        self.master.inspector_refresh_needed.emit()

    def toggle_code(self):
        self.is_code_visible = not self.is_code_visible
        if self.is_code_visible: self.code_proxy.show()
        else: self.code_proxy.hide()
        self.update()

    def update_result_label(self):
        # Logic to display result on node
        if self.node_data.last_error:
            self.result_text = "Error"
        elif self.node_data.last_output:
            # Show first output value for brevity
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
        h = self.base_height + 25 # Extra space for result
        if self.is_code_visible: h += 110
        return QRectF(0, 0, self.width, h)

    def paint(self, painter, option, widget):
        rect = self.boundingRect()
        
        # Body
        path = QPainterPath()
        path.addRoundedRect(rect, self.radius, self.radius)
        painter.setBrush(QColor("#333"))
        painter.setPen(QPen(QColor("#111"), 1))
        painter.drawPath(path)

        # Header
        painter.setBrush(QColor("#444"))
        painter.drawRoundedRect(0, 0, self.width, 25, self.radius, self.radius)
        painter.drawRect(0, 15, self.width, 10) # Squared bottom corners
        
        # Title
        painter.setPen(Qt.white)
        painter.drawText(QRectF(0,0,self.width,25), Qt.AlignCenter, self.node_data.type)

        # Toggle Button
        painter.setBrush(QColor("#555"))
        painter.drawRoundedRect(self.width-25, 2, 20, 20, 3, 3)
        painter.drawText(QRectF(self.width-25, 2, 20, 20), Qt.AlignCenter, "<>")

        # Labels
        painter.setPen(QColor("#AAA"))
        for s in self.sockets['in']:
            painter.drawText(QRectF(15, s.y()-10, 100, 20), Qt.AlignLeft|Qt.AlignVCenter, s.name)
        for s in self.sockets['out']:
            painter.drawText(QRectF(0, s.y()-10, self.width-15, 20), Qt.AlignRight|Qt.AlignVCenter, s.name)

        # Result Display (Bottom)
        res_y = self.base_height
        painter.setPen(Qt.green if not self.node_data.last_error else Qt.red)
        painter.drawText(QRectF(0, res_y, self.width, 20), Qt.AlignCenter, self.result_text)

        # Selection
        if self.isSelected():
            painter.setPen(QPen(Qt.yellow, 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect, self.radius, self.radius)

        # Status Ring
        if self.node_data.last_error:
            painter.setPen(QPen(Qt.red, 2))
            painter.drawRoundedRect(rect, self.radius, self.radius)

    def mousePressEvent(self, event):
        if event.pos().x() > self.width-25 and event.pos().y() < 25:
            self.toggle_code()
            return
        self.master.inspector.set_node(self.node_data)
        super().mousePressEvent(event)

# ==============================================================================
# 5. INSPECTOR & PALETTE
# ==============================================================================

class InspectorWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.current_node = None
        
        self.lbl_type = QLabel("No Selection")
        self.lbl_type.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.layout.addWidget(self.lbl_type)
        
        # Params Container
        self.form_layout = QFormLayout()
        self.layout.addLayout(self.form_layout)
        
        # Code Editor
        self.layout.addWidget(QLabel("Implementation Code:"))
        self.txt_code = QTextEdit()
        self.txt_code.setStyleSheet("font-family: Consolas; font-size: 11px;")
        self.txt_code.setMaximumHeight(150)
        self.txt_code.textChanged.connect(self.on_code_changed)
        self.layout.addWidget(self.txt_code)
        
        # Logs
        self.layout.addWidget(QLabel("Execution Result:"))
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(100)
        self.layout.addWidget(self.txt_log)
        
        self.layout.addStretch()

    def set_node(self, node_data):
        self.current_node = node_data
        self.lbl_type.setText(f"{node_data.type} ({node_data.id[-4:]})")
        
        # Params
        while self.form_layout.count():
            child = self.form_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            
        for k, v in node_data.params.items():
            le = QLineEdit(str(v))
            le.textChanged.connect(lambda val, key=k: self.on_param_changed(key, val))
            self.form_layout.addRow(k, le)
            
        # Code
        self.txt_code.blockSignals(True)
        self.txt_code.setPlainText(node_data.code)
        self.txt_code.blockSignals(False)
        
        # Result
        if node_data.last_error:
            self.txt_log.setStyleSheet("color: #FF5555;")
            self.txt_log.setPlainText(node_data.last_error)
        elif node_data.last_output:
            self.txt_log.setStyleSheet("color: #55FF55;")
            self.txt_log.setPlainText(json.dumps(node_data.last_output, indent=2))
        else:
            self.txt_log.setStyleSheet("color: #AAA;")
            self.txt_log.setPlainText("Not executed yet.")

    def on_param_changed(self, key, val):
        if self.current_node:
            try: 
                # Simple type inference for MVP
                if '.' in val: self.current_node.params[key] = float(val)
                else: self.current_node.params[key] = int(val)
            except:
                self.current_node.params[key] = val

    def on_code_changed(self):
        if self.current_node:
            self.current_node.code = self.txt_code.toPlainText()

    def clear(self):
        self.current_node = None
        self.lbl_type.setText("No Selection")
        self.txt_code.clear()
        self.txt_log.clear()
        while self.form_layout.count():
            child = self.form_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()

class NodePalette(QListWidget):
    def __init__(self):
        super().__init__()
        self.setDragEnabled(True)
    
    def mimeData(self, items):
        mime = QMimeData()
        if items: mime.setText(items[0].text())
        return mime

# ==============================================================================
# 6. MAIN WINDOW & CONTROLLERS
# ==============================================================================

class NodeView(QGraphicsView):
    def __init__(self, scene, master):
        super().__init__(scene)
        self.master = master
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setAcceptDrops(True)

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0: self.scale(1.1, 1.1)
        else: self.scale(0.9, 0.9)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText(): event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText(): event.acceptProposedAction()

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
            if isinstance(item, QNodeSocket) and item != self.scene().drag_start:
                if item.is_output != self.scene().drag_start.is_output:
                    s1, s2 = self.scene().drag_start, item
                    start = s1 if s1.is_output else s2
                    end = s2 if s1.is_output else s1
                    self.master.create_connection(start, end)
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        super().mouseReleaseEvent(event)

class MainWindow(QMainWindow):
    inspector_refresh_needed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.resize(1300, 800)
        self.setWindowTitle("Final Python Node Editor")
        
        self.nodes = {} # id -> NodeData
        self.connections = [] # Visual connection items
        
        # Components
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

        # Layout
        main_widget = QWidget()
        layout = QHBoxLayout(main_widget)
        
        splitter = QSplitter()
        splitter.addWidget(self.palette)
        splitter.addWidget(self.view)
        splitter.addWidget(self.inspector)
        splitter.setSizes([150, 800, 300])
        
        layout.addWidget(splitter)
        self.setCentralWidget(main_widget)
        
        # Toolbar
        tb = self.addToolBar("Actions")
        tb.addAction("Run Workflow", self.run_workflow)
        tb.addSeparator()
        tb.addAction("Save JSON", self.save_json)
        tb.addAction("Load JSON", self.load_json)
        tb.addAction("Export Python", self.export_python)
        tb.addSeparator()
        tb.addAction("Clear", self.clear_graph)

        self.threadpool = QThreadPool()

    # --- Graph Mgmt ---
    def create_node(self, type_name, x, y, id=None, params=None, code=None):
        node = NodeData(type_name, x, y, id)
        if params: node.params = params
        if code: node.code = code
        self.nodes[node.id] = node
        
        item = QNodeItem(node, self)
        item.setPos(x, y)
        self.scene.addItem(item)
        return item

    def create_connection(self, start_s, end_s):
        # Visual
        path = QGraphicsPathItem()
        path.setPen(QPen(QColor("#AAA"), 2))
        path.setZValue(-1)
        self.scene.addItem(path)
        self.connections.append({'item': path, 'start': start_s, 'end': end_s})
        self.update_connections()

    def update_connections(self):
        for c in self.connections:
            p1 = c['start'].get_scene_pos()
            p2 = c['end'].get_scene_pos()
            path = QPainterPath(p1)
            dx = p2.x() - p1.x()
            path.cubicTo(p1.x()+dx*0.5, p1.y(), p2.x()-dx*0.5, p2.y(), p2.x(), p2.y())
            c['item'].setPath(path)

    def get_logical_conns(self):
        conns = []
        for c in self.connections:
            start_node = c['start'].parentItem().node_data
            end_node = c['end'].parentItem().node_data
            conns.append({
                'start_node': start_node.id,
                'start_socket': c['start'].index,
                'end_node': end_node.id,
                'end_socket': c['end'].index
            })
        return conns

    def find_item(self, nid):
        for item in self.scene.items():
            if isinstance(item, QNodeItem) and item.node_data.id == nid:
                return item
        return None

    # --- Actions ---
    def run_workflow(self):
        worker = ExecutionWorker(self.nodes, self.get_logical_conns())
        worker.signals.node_completed.connect(self.on_node_done)
        worker.signals.error.connect(lambda e: QMessageBox.critical(self, "Error", e))
        self.threadpool.start(worker)

    def on_node_done(self, nid, res):
        item = self.find_item(nid)
        if item: item.update_result_label()
        if self.inspector.current_node and self.inspector.current_node.id == nid:
            self.inspector.set_node(self.inspector.current_node)

    def clear_graph(self):
        self.scene.clear()
        self.nodes = {}
        self.connections = []
        self.inspector.clear()

    # --- Serialization ---
    def save_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save", "", "JSON (*.json)")
        if not path: return
        
        data = {"nodes": [], "connections": self.get_logical_conns()}
        for nid, n in self.nodes.items():
            # Update positions
            item = self.find_item(nid)
            if item: n.x, n.y = item.x(), item.y()
            
            data["nodes"].append({
                "id": n.id, "type": n.type, "x": n.x, "y": n.y,
                "params": n.params, "code": n.code
            })
            
        with open(path, 'w') as f: json.dump(data, f, indent=2)

    def load_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load", "", "JSON (*.json)")
        if not path: return
        
        with open(path, 'r') as f: data = json.load(f)
        self.clear_graph()
        
        # Restore Nodes
        for n in data['nodes']:
            self.create_node(n['type'], n['x'], n['y'], n['id'], n['params'], n.get('code'))
            
        # Restore Connections
        for c in data['connections']:
            s_item = self.find_item(c['start_node'])
            e_item = self.find_item(c['end_node'])
            if s_item and e_item:
                try:
                    s_sock = s_item.sockets['out'][c['start_socket']]
                    e_sock = e_item.sockets['in'][c['end_socket']]
                    self.create_connection(s_sock, e_sock)
                except: pass

    def export_python(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Python", "", "Python (*.py)")
        if not path: return
        
        script = "# Auto-Generated Workflow\n\n"
        script += "def run_workflow():\n"
        script += "    results = {}\n"
        
        # Note: Real export requires topological sort. 
        # We reuse the worker logic logic or simply export all and rely on user to know flow.
        # For this MVP, we will try to sort topologically to make a runnable script.
        
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
                if in_degree[v] == 0: queue.append(v)
                
        for nid in sorted_ids:
            node = self.nodes[nid]
            script += f"\n    # Node: {node.type} ({nid})\n"
            script += f"    params = {node.params}\n"
            
            # Construct Inputs
            input_dict_str = "{"
            for i, inp_name in enumerate(node.inputs):
                # Find source
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
            
            # Inject Indented Code
            code_lines = node.code.split('\n')
            for line in code_lines:
                script += f"    {line}\n"
            
            script += f"    results['{nid}'] = outputs\n"
            script += f"    print(f'Node {nid} Result: {{outputs}}')\n"
            
        script += "\nif __name__ == '__main__':\n    run_workflow()"
        
        with open(path, 'w') as f: f.write(script)
        QMessageBox.information(self, "Export", "Python script exported successfully.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Dark Theme
    p = QPalette()
    p.setColor(QPalette.Window, QColor(53, 53, 53))
    p.setColor(QPalette.WindowText, Qt.white)
    p.setColor(QPalette.Base, QColor(25, 25, 25))
    p.setColor(QPalette.Text, Qt.white)
    p.setColor(QPalette.Button, QColor(53, 53, 53))
    p.setColor(QPalette.ButtonText, Qt.white)
    app.setPalette(p)
    
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())