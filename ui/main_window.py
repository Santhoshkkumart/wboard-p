"""Main PySide6 application window."""

try:
    import cv2
except ImportError:
    cv2 = None

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QMainWindow,
                               QMessageBox, QPushButton, QVBoxLayout, QWidget)
from camera.camera import Camera
from camera.processor import FrameProcessor
from calibration.board_detector import BoardDetector
from calibration.calibration import Calibration
from calibration.calibration_dialog import CalibrationDialog
from drawing.canvas import DrawingCanvas
from gestures.gesture_detector import GestureDetector
from hand_tracking.hand_detector import HandDetector
from privacy.face_mask import FaceMask
from ui.widgets import CameraView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Interactive Whiteboard")
        self.resize(1180, 760)
        self.camera = Camera()
        self.hand_detector = HandDetector()
        self.processor = FrameProcessor(self.hand_detector, FaceMask())
        self.gestures = GestureDetector()
        self.calibration = Calibration()
        self.board_detector = BoardDetector()
        self.calibration.load()  # restore previous calibration if available
        self.show_face = False
        self.previous_tip = None
        self.last_mode = "IDLE"
        self._last_frame = None  # most recent mirrored frame for calibration
        self._build_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)
        self.timer.start(30)
        self.camera_ok = self.camera.open()
        if not self.camera_ok:
            self.camera_view.setText(self.camera.error or "Camera unavailable")
        if self.hand_detector.error:
            self.hand_status.setText("Hand: unavailable (install MediaPipe)")

    def _build_ui(self):
        root = QWidget()
        root.setStyleSheet("QWidget { background:#f2f5f8; color:#17212b; font-family:'Segoe UI',sans-serif; }"
                           "QPushButton { background:#ffffff; border:1px solid #cbd5df; border-radius:7px; padding:9px 16px; font-weight:600; }"
                           "QPushButton:hover { background:#e9f1f8; }"
                           "QPushButton:checked { background:#dceeff; border-color:#5796d1; }")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(20, 16, 20, 16)
        title = QLabel("INTERACTIVE WHITEBOARD")
        title.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        subtitle = QLabel("Camera based hand tracking and digital drawing prototype")
        subtitle.setStyleSheet("color:#5d6a77")
        outer.addWidget(title)
        outer.addWidget(subtitle)
        panels = QHBoxLayout()
        panels.setSpacing(14)
        camera_col = QVBoxLayout()
        camera_col.addWidget(QLabel("CAMERA VIEW"))
        self.camera_view = CameraView()
        camera_col.addWidget(self.camera_view, 1)
        board_col = QVBoxLayout()
        board_col.addWidget(QLabel("DIGITAL BOARD"))
        self.canvas = DrawingCanvas()
        self.canvas.setStyleSheet("border:1px solid #cbd5df; border-radius:10px")
        board_col.addWidget(self.canvas, 1)
        panels.addLayout(camera_col, 1)
        panels.addLayout(board_col, 1)
        outer.addLayout(panels, 1)
        controls = QHBoxLayout()
        self.face_button = QPushButton("Show Face: OFF")
        self.face_button.setCheckable(True)
        self.face_button.toggled.connect(self._toggle_face)
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.canvas.clear)
        undo_button = QPushButton("Undo")
        undo_button.clicked.connect(self.canvas.undo)
        save_button = QPushButton("Save PNG")
        save_button.clicked.connect(self._save)
        calibrate_button = QPushButton("Calibrate")
        calibrate_button.clicked.connect(self._calibrate)
        for button in (self.face_button, clear_button, undo_button, save_button, calibrate_button):
            controls.addWidget(button)
        controls.addStretch(1)
        outer.addLayout(controls)
        status = QHBoxLayout()
        self.camera_status = QLabel("Camera: starting…")
        self.hand_status = QLabel("Hand: waiting")
        self.cal_status = QLabel("Calibration: ✗")
        self.mode_status = QLabel("Mode: IDLE")
        for label in (self.camera_status, self.hand_status, self.cal_status, self.mode_status):
            label.setStyleSheet("color:#455565; padding:4px")
            status.addWidget(label)
        status.addStretch(1)
        outer.addLayout(status)
        self.setCentralWidget(root)
        self._refresh_cal_status()

    def _toggle_face(self, enabled):
        self.show_face = enabled
        self.face_button.setText("Show Face: ON" if enabled else "Show Face: OFF")

    def _update_frame(self):
        if not self.camera_ok:
            self.camera_status.setText("Camera: unavailable")
            self.gestures.reset()
            self.canvas.end_stroke()
            self.previous_tip = None
            self.last_mode = "IDLE"
            return
        ok, frame = self.camera.read()
        if not ok:
            self.camera_status.setText("Camera: frame read failed")
            self.previous_tip = None
            self.canvas.end_stroke()
            self.gestures.reset()
            self.last_mode = "IDLE"
            return
        # Mirroring makes movement in the preview feel natural.
        frame = cv2.flip(frame, 1)
        self._last_frame = frame.copy()
        display, landmarks, tip = self.processor.process(frame, self.show_face)
        mode = self.gestures.detect(landmarks, image_size=(frame.shape[1], frame.shape[0]))

        # Draw fingertip marker on camera preview.
        if tip is not None:
            ih, iw = display.shape[:2]
            px, py = int(tip[0] * iw), int(tip[1] * ih)
            cv2.circle(display, (px, py), 11, (25, 110, 245), 2)
            cv2.circle(display, (px, py), 3, (25, 110, 245), -1)

        # Draw whiteboard outline on camera preview when calibrated.
        if self.calibration.is_calibrated and cv2 is not None:
            ih, iw = display.shape[:2]
            src = self.calibration.source_points
            pts = [(int(x * iw), int(y * ih)) for x, y in src]
            for i in range(4):
                cv2.line(display, pts[i], pts[(i + 1) % 4],
                         (0, 255, 0), 2)

        self.camera_view.set_frame(display)
        self.camera_status.setText("Camera: ready")
        self.hand_status.setText("Hand: detected" if tip else "Hand: not detected")
        self.mode_status.setText(f"Mode: {mode}")

        # ---- Coordinate mapping: physical board → digital canvas ----
        # Determine the canvas-space point for the current fingertip.
        canvas_pt = None
        if tip is not None:
            if self.calibration.is_calibrated:
                if self.calibration.is_inside_board(tip):
                    mapped = self.calibration.transform_point(tip)
                    if mapped is not None:
                        canvas_pt = (min(1.0, max(0.0, mapped[0])),
                                     min(1.0, max(0.0, mapped[1])))
                # Finger is outside the whiteboard — treat as no-target.
            else:
                # Fallback: direct full-frame-to-canvas mapping.
                canvas_pt = (min(1.0, max(0.0, tip[0])),
                             min(1.0, max(0.0, tip[1])))

        # ---- Apply gesture actions using the resolved canvas point ---
        if canvas_pt is None or mode == "IDLE":
            self.canvas.end_stroke()
            self.previous_tip = None
        elif mode == "WRITE":
            if self.last_mode != "WRITE" or self.previous_tip is None:
                self.canvas.begin_stroke(canvas_pt)
            else:
                self.canvas.add_point(canvas_pt)
            self.previous_tip = canvas_pt
        if mode == "ERASE" and canvas_pt is not None:
            self.canvas.end_stroke()
            self.canvas.erase_at(canvas_pt)
            self.previous_tip = None
        self.last_mode = mode

    def _save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save whiteboard", "whiteboard.png", "PNG image (*.png)")
        if path:
            if not path.lower().endswith(".png"):
                path += ".png"
            if not self.canvas.save_png(path):
                QMessageBox.warning(self, "Save failed", "Could not save the whiteboard image.")

    def _calibrate(self):
        """Open the interactive calibration dialog."""
        # Pause camera while calibrating.
        self.timer.stop()

        # Use the most recent frame, or capture one now.
        frame = self._last_frame
        if frame is None:
            ok, raw = self.camera.read()
            if ok and raw is not None:
                frame = cv2.flip(raw, 1)
        if frame is None:
            QMessageBox.warning(
                self, "Calibration",
                "No camera frame available for calibration.")
            self.timer.start(30)
            return

        # Pre-populate with existing corners if previously calibrated.
        existing = (self.calibration.source_points
                    if self.calibration.is_calibrated else None)

        dialog = CalibrationDialog(
            frame, board_detector=self.board_detector,
            existing_corners=existing, parent=self)
        result = dialog.exec()

        if result == CalibrationDialog.DialogCode.Accepted:
            corners = dialog.get_corners()
            if corners and len(corners) == 4:
                ok = self.calibration.calibrate(corners)
                if ok:
                    self.calibration.save()
                    QMessageBox.information(
                        self, "Calibration",
                        "Calibration successful. The whiteboard region "
                        "is now mapped to the digital canvas.")
                else:
                    QMessageBox.warning(
                        self, "Calibration",
                        "Homography computation failed. Please try again.")

        self._refresh_cal_status()
        self.timer.start(30)

    def _reset_calibration(self):
        """Discard calibration and revert to full-frame drawing."""
        self.calibration.reset()
        self._refresh_cal_status()

    def _refresh_cal_status(self):
        """Update the calibration status label."""
        if self.calibration.is_calibrated:
            self.cal_status.setText("Calibration: ✓")
            self.cal_status.setStyleSheet("color:#27ae60; padding:4px; font-weight:bold;")
        else:
            self.cal_status.setText("Calibration: ✗")
            self.cal_status.setStyleSheet("color:#455565; padding:4px")

    def closeEvent(self, event):
        self.timer.stop()
        self.camera.close()
        self.hand_detector.close()
        super().closeEvent(event)
