# Handoff for next developer

## Project status

The prototype has been extended with **whiteboard detection**, **interactive four-point calibration**, **homography-based coordinate mapping**, **physical-board → digital-canvas drawing**, and a first temporal/orientation improvement to the rule-based gesture detector. Python syntax compilation and four camera-independent gesture tests pass. Runtime hardware testing still requires a Windows laptop with a webcam and the packages listed in `requirements.txt`.

## What was implemented (AI #1 — preserved)

- [x] PySide6 desktop window with side-by-side camera and digital board panels.
- [x] OpenCV webcam wrapper with a visible error state when unavailable.
- [x] MediaPipe Hands adapter returning 21 normalized landmarks when a hand is detected.
- [x] Index landmark 8 fingertip extraction and a visible preview marker.
- [x] Continuous normalized stroke drawing on a resizable white canvas.
- [x] Rule-based WRITE, ERASE, and IDLE gesture module.
- [x] Gesture rules use finger-joint angles in pixel space rather than image-up/down comparisons.
- [x] Temporal smoothing requires three matching frames within a five-frame window before entering/changing active modes; missing-hand state resets to IDLE immediately.
- [x] Erase gesture removes strokes touched by the fingertip eraser; undo removes the latest remaining stroke; clear clears all.
- [x] Save board to PNG via file dialog.
- [x] Face pixelation by default using OpenCV's bundled Haar cascade; Show Face toggle bypasses masking immediately.

## What was implemented (AI #2 — new)

- [x] **Automatic whiteboard detection** — classical CV pipeline: grayscale → Gaussian blur → Canny (multiple thresholds) → morphological closing → contour detection → polygon approximation → area/aspect ratio validation → corner ordering (TL, TR, BR, BL). See `calibration/board_detector.py`.
- [x] **Interactive four-point calibration dialog** — modal PySide6 dialog showing a frozen camera frame where the user clicks or drags four whiteboard corners. Visual polygon overlay, labeled markers, Auto Detect / Redo / Confirm / Cancel buttons. See `calibration/calibration_dialog.py`.
- [x] **Homography computation** — `cv2.getPerspectiveTransform()` maps four normalized camera-space whiteboard corners to the [0,0]–[1,1] canvas rectangle. See `calibration/calibration.py`.
- [x] **Physical-board → digital-canvas coordinate mapping** — fingertip coordinates pass through `cv2.perspectiveTransform()` before drawing. Points outside the whiteboard polygon are rejected (no accidental drawing). Fallback: when not calibrated, the original full-frame mapping is preserved. See `ui/main_window.py`.
- [x] **Point-in-quad rejection** — `cv2.pointPolygonTest()` filters fingertip positions that are outside the calibrated whiteboard region.
- [x] **Whiteboard outline overlay** — when calibrated, the green whiteboard boundary is drawn on the camera preview.
- [x] **Calibration persistence** — corners are saved to `calibration.json` and auto-loaded on startup so recalibration is not needed after restart.
- [x] **Calibration status indicator** — status bar shows `Calibration: ✓` / `Calibration: ✗`.

## What is not yet implemented

- [x] Initial gesture improvement (temporal smoothing, finger-orientation tolerance); test/tune on camera still needed.
- [ ] Custom ML gesture classifier (LSTM / GRU / 1D CNN with trajectory data).
- [ ] PPT / presentation integration.
- [ ] Performance instrumentation (FPS counter, latency metrics).
- [ ] Camera selector / reconnect UI.
- [ ] Segment-level erasing (currently removes entire stroke on contact).
- [ ] Runtime/hardware test on Windows.

## Files created (AI #2)

- `calibration/board_detector.py` — automatic whiteboard detection using classical CV.
- `calibration/calibration_dialog.py` — interactive calibration dialog with corner selection.

## Files modified (AI #2)

- `calibration/calibration.py` — extended with homography computation, point transformation, point-in-quad test, JSON persistence. Legacy `add_correspondence` API preserved.
- `ui/main_window.py` — integrated calibration flow (pause timer → dialog → compute homography → persist), coordinate mapping through homography, whiteboard outline overlay, calibration status indicator.
- `HANDOFF.md` — this file, updated for continuation.

## Current architecture

```text
app.py                          Entry point (QApplication)
├── ui/main_window.py           MainWindow (layout, timer, data flow, calibration integration)
│   ├── ui/widgets.py           CameraView (QLabel + frame display)
│   ├── camera/camera.py        Camera (OpenCV VideoCapture wrapper)
│   ├── camera/processor.py     FrameProcessor (hand + face pipeline)
│   │   ├── hand_tracking/hand_detector.py   HandDetector (MediaPipe Hands)
│   │   ├── hand_tracking/fingertip.py       fingertip() — landmark 8
│   │   └── privacy/face_mask.py             FaceMask (Haar pixelation)
│   ├── gestures/gesture_detector.py         GestureDetector (rule-based)
│   ├── drawing/canvas.py                    DrawingCanvas (QWidget + strokes)
│   │   └── drawing/stroke.py               Stroke (normalized point list)
│   ├── calibration/calibration.py           Calibration (homography + persistence)
│   ├── calibration/board_detector.py        BoardDetector (auto-detect whiteboard)
│   └── calibration/calibration_dialog.py    CalibrationDialog (interactive UI)
```

### Data flow per frame (30 ms QTimer)

```text
Camera.read()
  → cv2.flip(,1) (mirror)
  → store _last_frame
  → FrameProcessor.process()
     → HandDetector → 21 landmarks → fingertip()
     → FaceMask.apply()
  → GestureDetector.detect()
  → draw fingertip marker + whiteboard outline on display
  → CameraView.set_frame(display)
  → if calibrated:
       is_inside_board(tip)?
         → transform_point(tip) via homography → canvas_pt
       else: reject (no drawing outside board)
    else:
       canvas_pt = tip (full-frame fallback)
  → WRITE: canvas.begin_stroke / add_point(canvas_pt)
     ERASE: canvas.erase_at(canvas_pt)
     IDLE:  canvas.end_stroke()
```

### Calibration flow

```text
User clicks "Calibrate"
  → timer.stop()
  → freeze _last_frame
  → CalibrationDialog(frame, board_detector)
     → user clicks 4 corners / Auto Detect
     → Confirm
  → Calibration.calibrate(corners)
     → cv2.getPerspectiveTransform(src, dst)
  → Calibration.save("calibration.json")
  → timer.start(30)
```

## Known bugs and unverified behavior

All items from AI #1 remain. Additionally:
- Auto-detection depends on the whiteboard having clear, high-contrast edges. It may fail in low-contrast scenes; the manual fallback handles this.
- The Haar face masking limitation persists (may miss faces at unusual angles).
- Erase still removes the entire stroke on contact, not individual segments.
- Joint-angle classification handles in-plane finger rotation better, but unusual camera angles, finger overlap, low landmark quality, and hand rotations toward/away from the camera can still misclassify poses.
- Gesture debounce uses frame counts (3 of 5), not elapsed time; effective transition delay varies with camera FPS.
- The default 145-degree finger extension threshold and smoothing settings have only synthetic tests so far and need webcam tuning.
- Calibration uses the mirrored frame; if mirroring is disabled the corners would shift.

## How to run

On Windows PowerShell, from the project directory:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

## NEXT TASK FOR AI #3

1. Install requirements on Windows and launch `python app.py` with a webcam. Fix any compatibility issues.
2. Test the calibration workflow end-to-end: click Calibrate → select corners → confirm → verify drawing maps correctly.
3. Test Auto Detect with a visible whiteboard and verify corner accuracy.
4. Test the improved gestures on webcam using upright and rotated hands, multiple users, distances, lighting, and slow/fast motion. Tune the 145-degree threshold and 3-of-5 debounce as needed while retaining the rule-based fallback.
5. Implement a custom ML gesture classifier (LSTM/GRU/1D-CNN) only after trajectory data (timestamp, x, y, z, velocity) can be collected reproducibly. Keep the rule-based system as fallback and report proper evaluation metrics.
6. Add performance instrumentation (FPS, latency counters).
7. Investigate PPT / presentation overlay integration (only after calibration is stable).
8. Polish UI feedback: camera selector, reconnect, calibration reset button.
9. Update README.md with evaluation methodology and actual measured results after testing.
10. Test under varying lighting, distances, and hand speeds. Record results.

## Phase 6 changes made by this developer

- `gestures/gesture_detector.py` now measures the MCP–PIP–tip joint angle for index, middle, ring, and pinky. Inputs are converted from normalized landmark coordinates to image pixels using the frame `(width, height)`, reducing orientation bias and aspect-ratio distortion.
- WRITE remains index-only; ERASE remains index + middle only; other poses map to IDLE.
- Active pose changes require a 3-vote majority in a 5-frame rolling history. No-hand detection clears history and returns IDLE immediately. Camera read failures also reset gesture state and end any active stroke.
- `ui/main_window.py` passes the camera frame dimensions into gesture detection.
- `tests/test_gesture_detector.py` covers the 3-frame debounce, WRITE→ERASE→IDLE transitions, immediate missing-hand reset, and an in-plane rotated finger pose.
- README gesture documentation was updated.

Verification performed: `python -m unittest discover -v` (4 tests passed) and `python -m compileall -q .` (passed). No webcam, PySide6, OpenCV, or MediaPipe runtime test was possible in this environment, so real pose accuracy and UI integration remain unverified.
