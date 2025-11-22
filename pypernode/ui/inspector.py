import json
from PyQt5.QtWidgets import QFormLayout, QLabel, QLineEdit, QTextEdit, QVBoxLayout, QWidget


class InspectorWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.current_node = None

        self.lbl_type = QLabel("No Selection")
        self.lbl_type.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.layout.addWidget(self.lbl_type)

        self.form_layout = QFormLayout()
        self.layout.addLayout(self.form_layout)

        self.layout.addWidget(QLabel("Implementation Code:"))
        self.txt_code = QTextEdit()
        self.txt_code.setStyleSheet("font-family: Consolas; font-size: 11px;")
        self.txt_code.setMaximumHeight(150)
        self.txt_code.textChanged.connect(self.on_code_changed)
        self.layout.addWidget(self.txt_code)

        self.layout.addWidget(QLabel("Execution Result:"))
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(100)
        self.layout.addWidget(self.txt_log)

        self.layout.addStretch()

    def set_node(self, node_data):
        self.current_node = node_data
        self.lbl_type.setText(f"{node_data.type} ({node_data.id[-4:]})")

        while self.form_layout.count():
            child = self.form_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for k, v in node_data.params.items():
            le = QLineEdit(str(v))
            le.textChanged.connect(lambda val, key=k: self.on_param_changed(key, val))
            self.form_layout.addRow(k, le)

        self.txt_code.blockSignals(True)
        self.txt_code.setPlainText(node_data.code)
        self.txt_code.blockSignals(False)

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
                if '.' in val:
                    self.current_node.params[key] = float(val)
                else:
                    self.current_node.params[key] = int(val)
            except Exception:
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
            if child.widget():
                child.widget().deleteLater()
