import sys
import graphcore
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
    QGraphicsLineItem, QGraphicsItem, QToolBar, QPushButton,QGraphicsTextItem
)
from PySide6.QtCore import QLineF, Qt
from PySide6.QtGui import QPainter, QBrush, QPen, QColor

NODE_RADIUS = 22
NODE_BRUSH = QBrush(QColor("#4C8BF5"))
NODE_BRUSH_PENDING = QBrush(QColor("#F5A623"))
NODE_PEN = QPen(QColor("#1F3B73"), 2)
EDGE_PEN = QPen(QColor("#333333"), 2)
LEVEL_PEN = QPen(QColor("#CCCCCC"), 1, Qt.DashLine)

# Spacing between adjacent levels, and the starting two levels (centered on 0).
LEVEL_SPACING = 300.0
INITIAL_LEVEL_YS = [-LEVEL_SPACING / 2, LEVEL_SPACING / 2]

def parse_planar_output(levels: list[list[int]], level_ys_sorted: list[float], x_spacing: float = 200.0):
    positions = []
    
    if len(levels) != len(level_ys_sorted):
        print(
            f"Warning: out.out has {len(levels)} level lines but there are "
            f"{len(level_ys_sorted)} levels - positions may be misaligned"
        )
 
    for level_index, node_id_strs in enumerate(levels):
        if level_index >= len(level_ys_sorted):
            break
        y = level_ys_sorted[level_index]
        n = len(node_id_strs)
        start_x = -(n - 1) * x_spacing / 2
        for order, node_id_str in enumerate(node_id_strs):
            node_id = int(node_id_str)
            x = start_x + order * x_spacing
            positions.append((node_id, x, y))
 
    return positions


class GraphModel:

    def __init__(self):
        self._next_id = -1
        self.nodes = set()
        self.levels = {x: set() for x in INITIAL_LEVEL_YS}
        self.edges = set()

    def add_node(self,level_y):
        self._next_id += 1
        node_id = self._next_id
        self.nodes.add(node_id)
        self.levels[level_y].add(node_id)
        return node_id

    def add_edge(self, a, b):
        if a == b or a not in self.nodes or b not in self.nodes:
            return False
        key = frozenset((a, b))
        if key in self.edges:
            return False
        self.edges.add(key)
        return True

    def planarize(self):
        levels_sorted = [sorted(self.levels[l]) for l in sorted(self.levels)]
        edges = [tuple(e) for e in self.edges]
        try:
            return graphcore.planarize(
                num_nodes=len(self.nodes),
                levels=levels_sorted,
                edges=edges,
            )
        except Exception as exc:
            print(f"planarize() failed: {exc}")
            return None



class NodeItem(QGraphicsEllipseItem):

    def __init__(self, node_id: int, x: float, level_y: float):
        super().__init__(-NODE_RADIUS, -NODE_RADIUS, NODE_RADIUS * 2, NODE_RADIUS * 2)
        self.node_id = node_id
        self.edges: list["EdgeItem"] = []
        self.level_y = level_y
        self.setPos(x, self.level_y)
        self.setBrush(NODE_BRUSH)
        self.setPen(NODE_PEN)
        self.setZValue(1)  # draw on top of edges
        self.setFlags(
            QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            new_pos = value
            new_pos.setY(self.level_y)
            return new_pos
        if change == QGraphicsItem.ItemPositionHasChanged:
            for edge in self.edges:
                edge.update_position()
        return super().itemChange(change, value)

    def add_edge(self, edge: "EdgeItem"):
        self.edges.append(edge)

    def set_pending(self, pending: bool):
        self.setBrush(NODE_BRUSH_PENDING if pending else NODE_BRUSH)


class EdgeItem(QGraphicsLineItem):

    def __init__(self, node_a: NodeItem, node_b: NodeItem):
        super().__init__()
        self.node_a = node_a
        self.node_b = node_b
        self.setPen(EDGE_PEN)
        self.setZValue(0)
        node_a.add_edge(self)
        node_b.add_edge(self)
        self.update_position()

    def update_position(self):
        self.setLine(QLineF(self.node_a.pos(), self.node_b.pos()))

class PlanarNodeItem(QGraphicsEllipseItem):
 
    def __init__(self, node_id: int, x: float, y: float):
        super().__init__(-NODE_RADIUS, -NODE_RADIUS, NODE_RADIUS * 2, NODE_RADIUS * 2)
        self.setPos(x, y)
        self.setBrush(NODE_BRUSH)
        self.setPen(NODE_PEN)
        self.setZValue(1)
 
        label = QGraphicsTextItem(str(node_id), self)
        label.setDefaultTextColor(Qt.white)
        rect = label.boundingRect()
        label.setPos(-rect.width() / 2, -rect.height() / 2)


class PlanarDrawingWindow(QMainWindow):
 
    def __init__(self, positions: list[tuple[int, float, float]], edges: set):
        super().__init__()
        self.setWindowTitle("Planar Drawing")
        self.resize(1000, 700)
 
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(-2000, -2000, 4000, 4000)
        
        node_items = {}
        for node_id, x, y in positions:
            item = PlanarNodeItem(node_id, x, y)
            self.scene.addItem(item)
            node_items[node_id] = item
 
        for a, b in [tuple(e) for e in edges]:
            if a in node_items and b in node_items:
                line = QGraphicsLineItem(QLineF(node_items[a].pos(), node_items[b].pos()))
                line.setPen(EDGE_PEN)
                line.setZValue(0)
                self.scene.addItem(line)
 
        view = QGraphicsView(self.scene)
        view.setRenderHint(QPainter.Antialiasing)
        self.setCentralWidget(view)


class GraphScene(QGraphicsScene):

    def __init__(self, model: GraphModel):
        super().__init__()
        self.model = model
        self.node_armed = False
        self.edge_armed = False
        self._pending_edge_source: NodeItem | None = None
        self.level_ys = set(INITIAL_LEVEL_YS)
        for level_y in self.level_ys:
            self._draw_level_line(level_y)

    def _draw_level_line(self, level_y: float):
        x_min, x_max = -2000, 2000
        line = QGraphicsLineItem(x_min, level_y, x_max, level_y)
        line.setPen(LEVEL_PEN)
        line.setZValue(-1)  # behind everything
        self.addItem(line)

    def nearest_level_y(self, y: float) -> float:
        return min(self.level_ys, key=lambda level_y: abs(level_y - y))

    def levels_are_neighbours(self, level_y_a: float, level_y_b: float) -> bool:
        sorted_levels = sorted(self.level_ys)
        index_a = sorted_levels.index(level_y_a)
        index_b = sorted_levels.index(level_y_b)
        return abs(index_a - index_b) == 1

    def add_level(self, position: str):
        if position == "top":
            new_y = min(self.level_ys) - LEVEL_SPACING
        else:
            new_y = max(self.level_ys) + LEVEL_SPACING
        self.level_ys.add(new_y)
        self.model.levels[new_y]=set()
        self._draw_level_line(new_y)
        print(f"Added level at y={new_y:.0f} ({position}). Levels now: {sorted(self.level_ys)}")

    def node_at(self, scene_pos):
        item = self.itemAt(scene_pos, self.views()[0].transform())
        return item if isinstance(item, NodeItem) else None

    def mousePressEvent(self, event):
        pos = event.scenePos()

        if self.node_armed:
            level_y = self.nearest_level_y(pos.y())
            node_id = self.model.add_node(level_y)
            item = NodeItem(node_id, pos.x(), level_y)
            self.addItem(item)
            self.node_armed = False
            print(f"Placed node {node_id} at ({pos.x():.0f}, {level_y:.0f})")
            return

        if self.edge_armed:
            clicked_node = self.node_at(pos)
            if clicked_node is None:
                print("Edge mode: click on a node (missed)")
                return
            if self._pending_edge_source is None:
                self._pending_edge_source = clicked_node
                clicked_node.set_pending(True)
                print(f"Edge start: node {clicked_node.node_id}. Now click the target node.")
            else:
                source = self._pending_edge_source
                if clicked_node is source:
                    print("Can't connect a node to itself, pick a different node")
                    return
                if not self.levels_are_neighbours(source.level_y, clicked_node.level_y):
                    print("Edges can only connect neighbouring levels, pick a different node")
                    return
                if self.model.add_edge(source.node_id, clicked_node.node_id):
                    edge = EdgeItem(source, clicked_node)
                    self.addItem(edge)
                    print(f"Added edge {source.node_id} - {clicked_node.node_id}")
                else:
                    print("Edge already exists")
                source.set_pending(False)
                self._pending_edge_source = None
                self.edge_armed = False
            return

        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Drawer")
        self.resize(1000, 700)

        self.model = GraphModel()

        self.scene = GraphScene(self.model)
        self.scene.setSceneRect(-2000, -2000, 4000, 4000)

        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)

        self.setCentralWidget(self.view)

        toolbar = QToolBar("Tools")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        add_node_button = QPushButton("Add Node")
        add_node_button.clicked.connect(self.on_add_node_clicked)
        toolbar.addWidget(add_node_button)

        add_edge_button = QPushButton("Add Edge")
        add_edge_button.clicked.connect(self.on_add_edge_clicked)
        toolbar.addWidget(add_edge_button)

        add_level_top_button = QPushButton("Add Level (Top)")
        add_level_top_button.clicked.connect(lambda: self.scene.add_level("top"))
        toolbar.addWidget(add_level_top_button)

        add_level_bottom_button = QPushButton("Add Level (Bottom)")
        add_level_bottom_button.clicked.connect(lambda: self.scene.add_level("bottom"))
        toolbar.addWidget(add_level_bottom_button)

        planarize_button = QPushButton("Planarize")
        planarize_button.clicked.connect(self.on_planarize_clicked)
        toolbar.addWidget(planarize_button)

        self.planar_window: PlanarDrawingWindow | None = None

    def on_add_node_clicked(self):
        self.scene.node_armed = True
        if self.scene._pending_edge_source is not None:
            self.scene._pending_edge_source.set_pending(False)
        self.scene._pending_edge_source = None
        print("Armed: click the canvas to place a node")

    def on_add_edge_clicked(self):
        self.scene.edge_armed = True
        print("Armed: click a node, then click another node to connect them")

    def on_planarize_clicked(self):
        levels = self.model.planarize()

        if levels is None:
            print("The graph is not level planar :(")
            return

        level_ys_sorted = sorted(self.scene.level_ys)
        positions = parse_planar_output(levels, level_ys_sorted)

        if self.planar_window is not None:
            self.planar_window.close()
 
        self.planar_window = PlanarDrawingWindow(positions, self.model.edges)
        self.planar_window.show()



def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()