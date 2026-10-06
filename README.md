# Camera Based Interactive Whiteboard

A native Python desktop prototype that uses a webcam and MediaPipe Hands to track the index fingertip and draw on a digital board. It is a first-stage prototype; it does not yet detect or calibrate a physical whiteboard.

## Features

- PySide6 desktop interface with live, mirrored camera preview and digital canvas.
- MediaPipe Hands 21 landmark tracking; landmark 8 is highlighted and used as the pointer.
- Joint-angle based WRITE (index only), ERASE (index and middle), and IDLE gestures with temporal smoothing.
- Continuous stroke drawing, stroke-level undo, clear, and PNG save.
- Face-only pixelation by default with a live Show Face toggle.
- Camera and missing dependency errors are shown without terminating the UI.
- Calibration module scaffold and an honest placeholder dialog.

## Technologies

Python 3.10–3.12, PySide6, OpenCV, MediaPipe Hands, and NumPy. NumPy is included as a direct runtime dependency of the vision libraries.

## Installation

On Windows, from this project directory:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Python 3.10–3.12 is recommended because MediaPipe wheel availability varies by Python version and platform.

## Run

```powershell
python app.py
```

Connect a webcam and allow camera access. If no camera is available the app remains open and shows the camera error. Install the requirements to enable hand tracking and the camera preview.

## Controls

- **Show Face: OFF/ON** — face regions are pixelated by default; ON reveals the unmodified face image.
- **Clear** — clear the whole board.
- **Undo** — remove the most recent stroke.
- **Save PNG** — choose a path and save the visible board.
- **Calibrate** — displays the current calibration status; calibration is not implemented yet.
- **Write** — extend only the index finger. Moving it draws.
- **Erase** — extend index and middle fingers while folding ring and pinky. Strokes touched by the eraser are removed.
- **Idle** — other/no hand poses do not draw.

Finger extension is estimated from joint angles in camera pixel space, so the rule does not require the fingers to point upward. The detector requires three consistent frames (within a five-frame window) before switching into or between WRITE and ERASE. Missing hand detection resets immediately to IDLE. The two-finger erase pose has priority over writing.

## Current limitations

- Face masking relies on OpenCV's frontal-face Haar cascade. It can miss faces at unusual angles, under occlusion, or in poor lighting; verify the preview before use where privacy is important.
- Gestures use simple landmark height comparisons and can misclassify rotated hands.
- Erasing removes a complete stroke when the eraser touches it.
- There is no physical board detection, four-point UI, homography, or physical-to-digital coordinate mapping. Drawing currently maps the fingertip's camera-frame normalized position across the entire digital canvas.
- The camera uses device index 0. There is no camera selector or reconnect control.
- No automated training or custom ML classifier is included.

## Future work

See [HANDOFF.md](HANDOFF.md) for architecture, verification status, and an ordered continuation plan.
