"""Orientation-tolerant, temporally smoothed gesture rules.

The output interface remains WRITE / ERASE / IDLE so the drawing pipeline can
later swap this implementation for a learned classifier.
"""

from collections import Counter, deque
from math import acos, degrees, hypot


def _joint_angle(a, vertex, b):
    """Return the angle in degrees at ``vertex`` for 2D points."""
    ax, ay = a[0] - vertex[0], a[1] - vertex[1]
    bx, by = b[0] - vertex[0], b[1] - vertex[1]
    denom = hypot(ax, ay) * hypot(bx, by)
    if denom < 1e-8:
        return 0.0
    cosine = max(-1.0, min(1.0, (ax * bx + ay * by) / denom))
    return degrees(acos(cosine))


class GestureDetector:
    """Classify finger poses and require a short stable run before switching.

    ``image_size`` is supplied as ``(width, height)`` so joint angles are
    calculated in pixel space and are not skewed by normalized image axes.
    """

    FINGER_JOINTS = {
        "index": (5, 6, 8),
        "middle": (9, 10, 12),
        "ring": (13, 14, 16),
        "pinky": (17, 18, 20),
    }

    def __init__(self, history_size=5, min_votes=3, extended_angle=145.0):
        if history_size < 1 or not 1 <= min_votes <= history_size:
            raise ValueError("min_votes must be between 1 and history_size")
        self.history = deque(maxlen=history_size)
        self.min_votes = min_votes
        self.extended_angle = extended_angle
        self.mode = "IDLE"

    def _classify_pose(self, landmarks, image_size):
        if landmarks is None or len(landmarks) < 21:
            return "IDLE"
        width, height = image_size or (1.0, 1.0)

        # MediaPipe x/y coordinates are normalized independently. Convert to
        # pixels first so joint angles remain useful for a landscape webcam.
        points = [(float(p[0]) * width, float(p[1]) * height) for p in landmarks]
        extended = {}
        for name, (mcp, pip, tip) in self.FINGER_JOINTS.items():
            angle = _joint_angle(points[mcp], points[pip], points[tip])
            extended[name] = angle >= self.extended_angle

        index = extended["index"]
        middle = extended["middle"]
        ring = extended["ring"]
        pinky = extended["pinky"]
        if index and middle and not ring and not pinky:
            return "ERASE"
        if index and not middle and not ring and not pinky:
            return "WRITE"
        return "IDLE"

    def detect(self, landmarks, image_size=None):
        """Return a smoothed gesture. Missing hand immediately clears state."""
        if landmarks is None or len(landmarks) < 21:
            self.reset()
            return "IDLE"

        raw = self._classify_pose(landmarks, image_size)
        self.history.append(raw)
        counts = Counter(self.history)

        # Non-idle actions must win a majority before they can cause drawing
        # or erasing. If evidence is inconclusive, fail closed to IDLE.
        action = max(("WRITE", "ERASE"), key=lambda item: counts[item])
        if counts[action] >= self.min_votes:
            self.mode = action
        elif counts["IDLE"] >= self.min_votes:
            self.mode = "IDLE"
        elif self.mode not in ("WRITE", "ERASE"):
            self.mode = "IDLE"
        return self.mode

    def reset(self):
        self.history.clear()
        self.mode = "IDLE"
