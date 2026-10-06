"""Interactive white drawing canvas with stroke-level undo and erasing."""

from math import hypot
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import QWidget
from drawing.stroke import Stroke


class DrawingCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.strokes = []
        self.active = None
        self.setMinimumSize(360, 300)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)

    def begin_stroke(self, point):
        self.active = Stroke([point])
        self.strokes.append(self.active)
        self.update()

    def add_point(self, point):
        if self.active is not None:
            self.active.add(point)
            self.update()

    def end_stroke(self):
        self.active = None

    def clear(self):
        self.strokes.clear()
        self.active = None
        self.update()

    def undo(self):
        if self.strokes:
            self.strokes.pop()
            self.active = None
            self.update()

    def erase_at(self, point, radius=0.035):
        x, y = point
        kept = []
        for stroke in self.strokes:
            pts = stroke.points
            hit = any(hypot(px - x, py - y) <= radius for px, py in pts)
            for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                dx, dy = bx - ax, by - ay
                length2 = dx * dx + dy * dy
                t = 0 if length2 == 0 else max(0, min(1, ((x-ax)*dx + (y-ay)*dy) / length2))
                if hypot(ax + t*dx - x, ay + t*dy - y) <= radius:
                    hit = True
                    break
            if not hit:
                kept.append(stroke)
        if len(kept) != len(self.strokes):
            self.strokes = kept
            self.active = None
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("white"))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = max(1, self.width()), max(1, self.height())
        for stroke in self.strokes:
            if not stroke.points:
                continue
            pen = QPen(QColor(stroke.color), max(2, stroke.width * min(w, h)))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            points = [QPointF(x * w, y * h) for x, y in stroke.points]
            if len(points) == 1:
                painter.drawPoint(points[0])
            else:
                for a, b in zip(points, points[1:]):
                    painter.drawLine(a, b)

    def save_png(self, path):
        image = QImage(self.size(), QImage.Format.Format_ARGB32)
        image.fill(QColor("white"))
        self.render(image)
        return image.save(path, "PNG")
