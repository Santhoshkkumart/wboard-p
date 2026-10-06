"""Automatic whiteboard detection using classical computer vision.

Pipeline:
    Camera frame → grayscale → Gaussian blur → Canny → morphological closing
    → contour detection → polygon approximation → area/aspect ratio filtering
    → corner ordering → candidate whiteboard
"""

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = np = None


def _order_corners(pts):
    """Order four points as: top-left, top-right, bottom-right, bottom-left.

    Uses the sum and difference heuristic:
        TL has the smallest x+y, BR the largest.
        TR has the smallest y-x, BL the largest.
    """
    pts = pts.reshape(4, 2).astype(np.float32)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).flatten()
    ordered = np.zeros((4, 2), dtype=np.float32)
    ordered[0] = pts[np.argmin(s)]   # top-left
    ordered[2] = pts[np.argmax(s)]   # bottom-right
    ordered[1] = pts[np.argmin(d)]   # top-right
    ordered[3] = pts[np.argmax(d)]   # bottom-left
    return ordered


class BoardDetector:
    """Detects a rectangular whiteboard in a camera frame.

    The detector tries multiple Canny threshold pairs to handle
    different lighting conditions.  The largest convex quadrilateral
    that passes area and aspect-ratio checks is selected.
    """

    def __init__(self, min_area_ratio=0.05, max_aspect_ratio=5.0,
                 approx_epsilon=0.02):
        self.min_area_ratio = min_area_ratio
        self.max_aspect_ratio = max_aspect_ratio
        self.approx_epsilon = approx_epsilon
        # Canny threshold pairs to try (low, high) — wider first.
        self._canny_pairs = [(30, 100), (50, 150), (80, 200)]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, frame):
        """Detect a whiteboard and return its four corner points in **pixel
        coordinates** as a ``(4, 2)`` float32 ndarray ordered
        [TL, TR, BR, BL], or *None* if detection fails."""
        if cv2 is None or np is None or frame is None:
            return None

        h, w = frame.shape[:2]
        frame_area = h * w
        min_area = frame_area * self.min_area_ratio

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        best = None  # (area, corners)

        for canny_lo, canny_hi in self._canny_pairs:
            edges = cv2.Canny(blurred, canny_lo, canny_hi)

            # Morphological closing to bridge small gaps in edges.
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            edges = cv2.dilate(edges, kernel, iterations=2)
            edges = cv2.erode(edges, kernel, iterations=1)

            contours, _ = cv2.findContours(
                edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                quad = self._validate_quad(contour, min_area)
                if quad is None:
                    continue
                area = cv2.contourArea(contour)
                if best is None or area > best[0]:
                    best = (area, quad)

        return best[1] if best is not None else None

    def detect_candidates(self, frame, max_candidates=5):
        """Return up to *max_candidates* ordered by area descending.

        Each item is a ``(4, 2)`` float32 ndarray of corners.
        """
        if cv2 is None or np is None or frame is None:
            return []

        h, w = frame.shape[:2]
        min_area = h * w * self.min_area_ratio

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        seen = []  # (area, corners)

        for canny_lo, canny_hi in self._canny_pairs:
            edges = cv2.Canny(blurred, canny_lo, canny_hi)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            edges = cv2.dilate(edges, kernel, iterations=2)
            edges = cv2.erode(edges, kernel, iterations=1)
            contours, _ = cv2.findContours(
                edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                quad = self._validate_quad(contour, min_area)
                if quad is None:
                    continue
                area = cv2.contourArea(contour)
                # Skip near-duplicates (centroid within 20 px of existing).
                cx, cy = quad.mean(axis=0)
                dup = False
                for _, prev in seen:
                    px, py = prev.mean(axis=0)
                    if abs(cx - px) < 20 and abs(cy - py) < 20:
                        dup = True
                        break
                if not dup:
                    seen.append((area, quad))

        seen.sort(key=lambda t: t[0], reverse=True)
        return [corners for _, corners in seen[:max_candidates]]

    # ------------------------------------------------------------------
    # Visualisation helper
    # ------------------------------------------------------------------

    def draw_detection(self, frame, corners):
        """Return a copy of *frame* with the detected quadrilateral and
        labelled corner markers drawn on it."""
        if cv2 is None or corners is None:
            return frame
        vis = frame.copy()
        pts = corners.astype(np.int32).reshape((-1, 1, 2))
        cv2.polylines(vis, [pts], True, (0, 255, 0), 2)
        labels = ["TL", "TR", "BR", "BL"]
        for label, pt in zip(labels, corners):
            center = (int(pt[0]), int(pt[1]))
            cv2.circle(vis, center, 8, (0, 0, 255), -1)
            cv2.putText(vis, label, (center[0] + 12, center[1] - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
        return vis

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_quad(self, contour, min_area):
        """If *contour* is a valid quadrilateral, return ordered corners;
        otherwise return *None*."""
        area = cv2.contourArea(contour)
        if area < min_area:
            return None

        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, self.approx_epsilon * peri, True)

        if len(approx) != 4:
            return None
        if not cv2.isContourConvex(approx):
            return None

        corners = _order_corners(approx)

        # Aspect-ratio sanity check.
        w_top = np.linalg.norm(corners[1] - corners[0])
        w_bot = np.linalg.norm(corners[2] - corners[3])
        h_left = np.linalg.norm(corners[3] - corners[0])
        h_right = np.linalg.norm(corners[2] - corners[1])
        avg_w = (w_top + w_bot) / 2
        avg_h = (h_left + h_right) / 2
        if min(avg_w, avg_h) < 1:
            return None
        aspect = max(avg_w, avg_h) / min(avg_w, avg_h)
        if aspect > self.max_aspect_ratio:
            return None

        return corners
