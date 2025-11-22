import time
from typing import Dict, List

from PyQt5.QtCore import QObject, QRunnable, pyqtSignal

from .models import NodeData


class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    node_started = pyqtSignal(str)
    node_completed = pyqtSignal(str, object)
    node_error = pyqtSignal(str, str)


class ExecutionWorker(QRunnable):
    def __init__(self, nodes: Dict[str, NodeData], connections: List[Dict[str, object]]):
        super().__init__()
        self.nodes = nodes
        self.connections = connections
        self.signals = WorkerSignals()

    def run(self):
        try:
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
                except Exception:
                    continue

            queue = [n for n in self.nodes if in_degree[n] == 0]
            sorted_nodes = []
            while queue:
                u = queue.pop(0)
                sorted_nodes.append(u)
                for v in adj[u]:
                    in_degree[v] -= 1
                    if in_degree[v] == 0:
                        queue.append(v)

            if len(sorted_nodes) != len(self.nodes):
                raise Exception("Cycle detected! Graph must be acyclic.")

            results_cache: Dict[str, Dict[str, object]] = {}
            for nid in sorted_nodes:
                node = self.nodes[nid]
                self.signals.node_started.emit(nid)

                node_inputs = {}
                for in_name in node.inputs:
                    if in_name in input_map[nid]:
                        src_id, src_pin = input_map[nid][in_name]
                        node_inputs[in_name] = results_cache.get(src_id, {}).get(src_pin, 0.0)
                    else:
                        node_inputs[in_name] = 0.0

                cur_hash = node.compute_hash(node_inputs)
                if node.cache_hash == cur_hash and not node.last_error and node.last_output:
                    results_cache[nid] = node.last_output
                    self.signals.node_completed.emit(nid, node.last_output)
                    time.sleep(0.05)
                    continue

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

                time.sleep(0.1)

            self.signals.finished.emit()
        except Exception as e:
            self.signals.error.emit(str(e))
