"""Small reusable UI widgets."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel


class CameraView(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(360, 300)
        self.setStyleSheet("background:#101820; color:#dbe5ed; border-radius:10px;")
        self.setText("Waiting for camera…")
        self._image = None

    def set_frame(self, frame):
        import cv2
        h, w, channels = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = QImage(rgb.data, w, h, channels * w, QImage.Format.Format_RGB888).copy()
        self._image = QPixmap.fromImage(image)
        self._refresh()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self):
        if self._image:
            self.setPixmap(self._image.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                                Qt.TransformationMode.SmoothTransformation))
