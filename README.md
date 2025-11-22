# PyPerNode
PyPerNode is a lightweight, visual node-based workflow engine for Python. Features inline code editing, smart caching, topological execution, and one-click export to Python scripts.

## 🚀 Features

* **Visual Editor:** Build graphs via drag & drop from the node palette.
* **Dynamic Execution:** Run the graph in a background thread with automatic topological dependency sorting.
* **Inline Editing:** Edit parameters and function code directly on the node.
* **Result Display:** Execution results are shown directly on each node (in green).
* **Inspector:** Detailed view of node parameters, source code, and execution/error logs.
* **Custom Nodes:** Write arbitrary Python code inside a node and save it as a new type in the library.
* **Caching:** Smart recomputation — only nodes with changed inputs or parameters are recalculated.
* **Import/Export:** Save the graph as JSON and export the workflow to a `.py` script.

## 🛠 Requirements and Installation

The application is written in Python using the **PyQt5** library.

### 1. Install Dependencies

You will need Python 3.6+ and PyQt5:

```bash
pip install PyQt5
```

### 2. Launch

Save the application code into a file (for example, `node_editor.py`) and run:

```bash
python node_editor.py
```

## 📖 User Guide

### Basic Actions

1. **Adding Nodes:** Drag the desired node (e.g., `Constant`, `Add`, `Output`) from the **Nodes** panel onto the canvas.
2. **Connecting Nodes:** Click the output pin (right side) of one node and drag to the input pin (left side) of another.
3. **Configuring Parameters:**

   * For simple nodes (such as `Constant`): enter a value directly in the field on the node.
   * For others: click the node to open the **Inspector** panel on the right.
4. **Run Workflow:** Click **Run Workflow** on the top toolbar.

   * Green text on the node: Successful execution + result.
   * Red outline: Error (see Inspector for details).

### Writing Your Own Code (Custom Nodes)

Every node in the editor is backed by a Python script. You can modify any node’s logic on the fly:

1. Add a node (e.g., `Custom` or any other).
2. Click the **`<>`** button in the upper-right corner of the node.
3. The built-in code editor will open.
4. Use the `inputs` and `outputs` dictionaries to implement logic:

   ```python
   # Example: Calculate hypotenuse
   import math
   # inputs['x'] and inputs['y'] come from input pins
   outputs['out'] = math.sqrt(inputs['x']**2 + inputs['y']**2)
   ```
5. Collapse the editor with **`<>`** and click **Run**.

### Creating New Node Types

If you wrote a useful algorithm inside a node, you can save it for later use:

1. Right-click the node.
2. Select **Save as New Node Type**.
3. Enter a name. The new node will appear in the panel on the left.

### Export and Save

* **Save JSON:** Saves the graph structure so you can continue working later.
* **Export Python:** Generates a `.py` file containing the entire workflow logic as a sequential Python script. This script can run without the editor.

## ⌨️ Controls

* **Left Mouse Button (Drag & Drop):** Drag nodes from the palette.
* **Left Mouse Button (on canvas):** Select and move nodes.
* **Mouse Wheel:** Zoom in/out.
* **Left Mouse Button (on socket):** Create a connection (drag from output to input).
* **Right Mouse Button (on node):** Context menu (Save as new type).

## ⚙️ Architecture

* **Graph:** Directed acyclic graph (DAG). The system checks for cycles before execution.
* **Execution:** Uses `QThreadPool` to run computations in the background without blocking the UI.
* **Security:** The application uses `exec()` to run node code.

  > ⚠️ **Warning:** Run workflows only from trusted sources, as `exec()` allows execution of arbitrary Python code on your machine.

## 📄 License

This project is an MVP (Minimum Viable Product) and is freely distributed for educational and personal use.
