import json
from datetime import date
from typing import Any

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..node_types import ValueType


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

    def _create_editor(self, value_type: ValueType, value: Any):
        if value_type == ValueType.NUMBER:
            spin = QDoubleSpinBox()
            spin.setRange(-1e9, 1e9)
            spin.setDecimals(4)
            spin.setValue(float(value) if value is not None else 0.0)
            return spin, spin.setValue
        if value_type == ValueType.STRING:
            te = QTextEdit()
            te.setPlainText("" if value is None else str(value))
            te.setFixedHeight(60)
            return te, te.setPlainText
        if value_type == ValueType.BOOLEAN:
            cb = QCheckBox()
            cb.setChecked(bool(value))
            return cb, cb.setChecked
        if value_type == ValueType.DATE:
            de = QDateEdit()
            de.setCalendarPopup(True)
            if isinstance(value, date):
                de.setDate(QDate(value.year, value.month, value.day))
            else:
                de.setDate(QDate.currentDate())
            return de, de.setDate

        te = QTextEdit()
        te.setPlainText("" if value is None else str(value))
        return te, te.setPlainText

    def set_node(self, node_data):
        self.current_node = node_data
        self.lbl_type.setText(f"{node_data.type} ({node_data.id[-4:]})")

        while self.form_layout.count():
            child = self.form_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for sock in node_data.input_defs:
            widget, _ = self._create_editor(sock.type, node_data.params.get(sock.name, sock.default))
            widget.setToolTip(f"{sock.name}: {sock.type.value}")
            if hasattr(widget, 'valueChanged'):
                widget.valueChanged.connect(lambda val, key=sock.name: self.on_param_changed(key, val))
            elif isinstance(widget, QTextEdit):
                widget.textChanged.connect(lambda key=sock.name, w=widget: self.on_param_changed(key, w.toPlainText()))
            elif isinstance(widget, QCheckBox):
                widget.stateChanged.connect(lambda state, key=sock.name: self.on_param_changed(key, bool(state)))
            elif isinstance(widget, QDateEdit):
                widget.dateChanged.connect(
                    lambda d, key=sock.name: self.on_param_changed(key, d.toPyDate())
                )
            self.form_layout.addRow(sock.name, widget)

        self.txt_code.blockSignals(True)
        self.txt_code.setPlainText(node_data.code)
        self.txt_code.blockSignals(False)

        if node_data.last_error:
            self.txt_log.setStyleSheet("color: #FF5555;")
            self.txt_log.setPlainText(node_data.last_error)
        elif node_data.last_output:
            self.txt_log.setStyleSheet("color: #55FF55;")
            self.txt_log.setPlainText(json.dumps(node_data.last_output, indent=2, default=str))
        else:
            self.txt_log.setStyleSheet("color: #AAA;")
            self.txt_log.setPlainText("Not executed yet.")

    def on_param_changed(self, key, val):
        if not self.current_node:
            return

        target_type = ValueType.ANY
        for sock in self.current_node.input_defs:
            if sock.name == key:
                target_type = sock.type
                break

        try:
            if target_type == ValueType.NUMBER:
                self.current_node.params[key] = float(val)
            elif target_type == ValueType.BOOLEAN:
                self.current_node.params[key] = bool(val)
            elif target_type == ValueType.DATE:
                if isinstance(val, date):
                    self.current_node.params[key] = val
                elif isinstance(val, QDate):
                    self.current_node.params[key] = val.toPyDate()
            else:
                self.current_node.params[key] = str(val)
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
