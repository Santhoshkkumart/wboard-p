"""Interactive calibration dialog for selecting whiteboard corners.

Provides a frozen camera-frame view where the user can:
  * Click four corners manually (TL → TR → BR → BL).
  * Use *Auto Detect* to pre-populate corners from BoardDetector.
  * Drag any marker to adjust its position.
  * Confirm, Redo, or Cancel.
"""

try:
    import cv2
except ImportError:
    cv2 = None

from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QPushButton,
                               QVBoxLayout, QWidget)


# ======================================================================
# Corner-selection widget
# ======================================================================

_CORNER_LABELS = ["TL", "TR", "BR", "BL"]
_CORNER_COLORS = [
    QColor(231, 76, 60),   # red
    QColor(46, 204, 113),  # green
    QColor(52, 152, 219),  # blue
    QColor(241, 196, 15),  # yellow
]
_MARKER_RADIUS = 10
_GRAB_RADIUS = 18  # pixels — max distance for click-to-drag


class _CalibrationView(QWidget):
    """Displays a frozen camera frame with interactive corner markers."""

    corners_changed = Signal()

    def __init__(self, frame_bgr, parent=None):
        super().__init__(parent)
        self._frame_bgr = frame_bgr
        self._frame_h, self._frame_w = frame_bgr.shape[:2]
        self.corners = []       # up to 4 × (nx, ny) normalised coords
        self._dragging = -1     # index of corner being dragged, or -1
        self._build_pixmap()
        self.setMinimumSize(640, 400)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)

    # ---- pixmap conversion -------------------------------------------

    def _build_pixmap(self):
        rgb = cv2.cvtColor(self._frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qi = QImage(rgb.data, w, h, ch * w,
                    QImage.Format.Format_RGB888).copy()
        self._source_pixmap = QPixmap.fromImage(qi)

    # ---- coordinate helpers ------------------------------------------

    def _display_rect(self):
        """Return the QRectF where the image is drawn (aspect-fit)."""
        pw = self._source_pixmap.width()
        ph = self._source_pixmap.height()
        ww = self.width()
        wh = self.height()
        scale = min(ww / pw, wh / ph)
        dw = pw * scale
        dh = ph * scale
        x0 = (ww - dw) / 2
        y0 = (wh - dh) / 2
        return QRectF(x0, y0, dw, dh)

    def _norm_to_widget(self, nx, ny):
        r = self._display_rect()
        return r.x() + nx * r.width(), r.y() + ny * r.height()

    def _widget_to_norm(self, wx, wy):
        r = self._display_rect()
        if r.width() < 1 or r.height() < 1:
            return None
        nx = (wx - r.x()) / r.width()
        ny = (wy - r.y()) / r.height()
        if not (0.0 <= nx <= 1.0 and 0.0 <= ny <= 1.0):
            return None
        return nx, ny

    # ---- painting ----------------------------------------------------

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#1a1f25"))

        # Draw the camera frame.
        r = self._display_rect()
        p.drawPixmap(r.toRect(), self._source_pixmap)

        if not self.corners:
            p.end()
            return

        # Semi-transparent fill inside the polygon.
        if len(self.corners) >= 3:
            from PySide6.QtGui import QPolygonF
            poly = QPolygonF()
            for nx, ny in self.corners:
                wx, wy = self._norm_to_widget(nx, ny)
                poly.append(QPointF(wx, wy))
            fill = QColor(52, 152, 219, 40)
            p.setBrush(fill)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPolygon(poly)

        # Draw edges between consecutive corners.
        edge_pen = QPen(QColor(255, 255, 255, 180), 2, Qt.PenStyle.DashLine)
        p.setPen(edge_pen)
        for i in range(len(self.corners)):
            j = (i + 1) % len(self.corners)
            if j >= len(self.corners):
                break
            ax, ay = self._norm_to_widget(*self.corners[i])
            bx, by = self._norm_to_widget(*self.corners[j])
            p.drawLine(QPointF(ax, ay), QPointF(bx, by))
        # Close the polygon if 4 corners.
        if len(self.corners) == 4:
            ax, ay = self._norm_to_widget(*self.corners[3])
            bx, by = self._norm_to_widget(*self.corners[0])
            p.drawLine(QPointF(ax, ay), QPointF(bx, by))

        # Draw corner markers and labels.
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        p.setFont(font)
        for i, (nx, ny) in enumerate(self.corners):
            wx, wy = self._norm_to_widget(nx, ny)
            color = _CORNER_COLORS[i % 4]
            p.setPen(QPen(color, 2))
            p.setBrush(color)
            p.drawEllipse(QPointF(wx, wy), _MARKER_RADIUS, _MARKER_RADIUS)
            # White label text.
            p.setPen(QPen(Qt.GlobalColor.white))
            p.drawText(int(wx + _MARKER_RADIUS + 4), int(wy - 4),
                       _CORNER_LABELS[i % 4])

        p.end()

    # ---- mouse interaction -------------------------------------------

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        wx, wy = event.position().x(), event.position().y()

        # Check if near an existing corner → start drag.
        for i, (nx, ny) in enumerate(self.corners):
            mx, my = self._norm_to_widget(nx, ny)
            if (wx - mx) ** 2 + (wy - my) ** 2 <= _GRAB_RADIUS ** 2:
                self._dragging = i
                return

        # Otherwise, add a new corner if < 4.
        if len(self.corners) < 4:
            norm = self._widget_to_norm(wx, wy)
            if norm is not None:
                self.corners.append(norm)
                self.corners_changed.emit()
                self.update()

    def mouseMoveEvent(self, event):
        if self._dragging < 0:
            return
        wx, wy = event.position().x(), event.position().y()
        norm = self._widget_to_norm(wx, wy)
        if norm is not None:
            self.corners[self._dragging] = norm
            self.corners_changed.emit()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = -1

    # ---- public helpers ----------------------------------------------

    def set_corners(self, corners_normalized):
        """Replace current corners (e.g. from auto-detection)."""
        self.corners = [(float(x), float(y)) for x, y in corners_normalized]
        self.corners_changed.emit()
        self.update()

    def clear_corners(self):
        self.corners.clear()
        self._dragging = -1
        self.corners_changed.emit()
        self.update()


# ======================================================================
# Main calibration dialog
# ======================================================================

class CalibrationDialog(QDialog):
    """Modal dialog for selecting / adjusting the four whiteboard corners.

    Parameters
    ----------
    frame_bgr : ndarray
        The frozen camera frame (BGR, uint8).
    board_detector : BoardDetector or None
        If provided, the *Auto Detect* button is enabled.
    existing_corners : list or None
        Previously calibrated normalised corners to pre-populate.
    """

    def __init__(self, frame_bgr, board_detector=None,
                 existing_corners=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Whiteboard Calibration")
        self.setMinimumSize(860, 620)
        self._frame = frame_bgr
        self._board_detector = board_detector
        self._result_corners = None
        self._build_ui()

        # Pre-populate if previous calibration exists.
        if existing_corners and len(existing_corners) == 4:
            self._view.set_corners(existing_corners)

    # ---- UI construction ---------------------------------------------

    def _build_ui(self):
        self.setStyleSheet(
            "QDialog { background:#f2f5f8; }"
            "QLabel { color:#17212b; font-family:'Segoe UI',sans-serif; }"
            "QPushButton { background:#ffffff; border:1px solid #cbd5df;"
            "  border-radius:7px; padding:8px 18px; font-weight:600;"
            "  font-family:'Segoe UI',sans-serif; }"
            "QPushButton:hover { background:#e9f1f8; }"
            "QPushButton:disabled { color:#999; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Instructions.
        instructions = QLabel(
            "Click the four whiteboard corners in order: "
            "<b>Top-Left → Top-Right → Bottom-Right → Bottom-Left</b>. "
            "Drag markers to adjust. Use <i>Auto Detect</i> to try "
            "automatic detection.")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Image view.
        self._view = _CalibrationView(self._frame, self)
        self._view.corners_changed.connect(self._on_corners_changed)
        layout.addWidget(self._view, 1)

        # Buttons row.
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._auto_btn = QPushButton("Auto Detect")
        self._auto_btn.clicked.connect(self._auto_detect)
        self._auto_btn.setEnabled(self._board_detector is not None)

        self._redo_btn = QPushButton("Redo")
        self._redo_btn.clicked.connect(self._redo)

        self._confirm_btn = QPushButton("✓  Confirm")
        self._confirm_btn.setStyleSheet(
            self._confirm_btn.styleSheet() +
            "QPushButton { background:#27ae60; color:white; }"
            "QPushButton:hover { background:#2ecc71; }"
            "QPushButton:disabled { background:#bdc3c7; color:#eee; }")
        self._confirm_btn.clicked.connect(self._confirm)
        self._confirm_btn.setEnabled(False)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self.reject)

        for btn in (self._auto_btn, self._redo_btn,
                    self._confirm_btn, self._cancel_btn):
            btn_row.addWidget(btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        # Status line.
        self._status = QLabel("Select corner 1 of 4 — Top-Left")
        self._status.setStyleSheet("color:#455565; padding:2px;")
        layout.addWidget(self._status)

    # ---- slots -------------------------------------------------------

    def _auto_detect(self):
        if self._board_detector is None:
            return
        corners_px = self._board_detector.detect(self._frame)
        if corners_px is None:
            self._status.setText(
                "⚠  Auto-detection failed. Select corners manually.")
            return
        h, w = self._frame.shape[:2]
        corners_norm = [(float(x) / w, float(y) / h)
                        for x, y in corners_px]
        self._view.set_corners(corners_norm)
        self._status.setText(
            "Auto-detected 4 corners. Adjust if needed, then Confirm.")

    def _redo(self):
        self._view.clear_corners()
        self._status.setText("Cleared. Select corner 1 of 4 — Top-Left")

    def _confirm(self):
        if len(self._view.corners) == 4:
            self._result_corners = list(self._view.corners)
            self.accept()

    def _on_corners_changed(self):
        n = len(self._view.corners)
        self._confirm_btn.setEnabled(n == 4)
        if n < 4:
            next_labels = ["Top-Left", "Top-Right", "Bottom-Right",
                           "Bottom-Left"]
            self._status.setText(
                f"Select corner {n + 1} of 4 — {next_labels[n]}")
        else:
            self._status.setText(
                "4 corners selected. Drag to adjust, then Confirm.")

    # ---- result accessor ---------------------------------------------

    def get_corners(self):
        """Return the confirmed corners, or *None* if cancelled."""
        return self._result_corners
