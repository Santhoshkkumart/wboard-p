"""Four-point whiteboard calibration with perspective homography.

Stores four whiteboard corners in normalized camera coordinates (0..1),
computes a homography mapping those corners to normalized canvas
coordinates, and transforms individual points through the mapping.

Calibration can be persisted to / loaded from a JSON file so the user
does not need to recalibrate after restarting the application.
"""

import json
import os

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = np = None


class Calibration:
    """Four-point calibration mapping camera coordinates to digital canvas.

    Coordinate convention
    ---------------------
    All points are **normalised** to [0, 1]:

    * ``source_points`` — whiteboard corners in the camera frame
      (after mirroring), ordered TL → TR → BR → BL.
    * ``canvas_corners`` — destination rectangle, hard-coded to
      [(0, 0), (1, 0), (1, 1), (0, 1)].

    The homography is computed in this normalised space so it is
    independent of the camera resolution.
    """

    _DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..",
                                 "calibration.json")

    def __init__(self):
        self.source_points = []      # 4 × (x, y) normalised camera coords
        self.canvas_corners = [
            (0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        self._matrix = None          # 3×3 perspective transform
        self._inverse_matrix = None  # inverse for canvas→camera mapping

        # Legacy attribute aliases kept so that nothing that reads them
        # outside this module breaks.
        self.image_points = self.source_points
        self.board_points = self.canvas_corners

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_calibrated(self):
        """True when the homography matrix has been computed."""
        return self._matrix is not None

    @property
    def matrix(self):
        """The 3×3 homography matrix (camera → canvas), or *None*."""
        return self._matrix

    # ------------------------------------------------------------------
    # Core calibration
    # ------------------------------------------------------------------

    def calibrate(self, corners_normalized):
        """Set four whiteboard corners and compute the homography.

        Parameters
        ----------
        corners_normalized : list of 4 (x, y) tuples
            Whiteboard corners in normalised camera coordinates,
            ordered TL → TR → BR → BL.

        Returns
        -------
        bool
            True on success, False if the input is invalid or OpenCV is
            unavailable.
        """
        if cv2 is None or np is None:
            return False
        if len(corners_normalized) != 4:
            return False

        self.source_points = [(float(x), float(y))
                              for x, y in corners_normalized]
        self.image_points = self.source_points   # legacy alias

        src = np.array(self.source_points, dtype=np.float32)
        dst = np.array(self.canvas_corners, dtype=np.float32)

        self._matrix = cv2.getPerspectiveTransform(src, dst)
        self._inverse_matrix = cv2.getPerspectiveTransform(dst, src)
        return True

    def reset(self):
        """Discard current calibration."""
        self.source_points.clear()
        self._matrix = None
        self._inverse_matrix = None

    # ------------------------------------------------------------------
    # Point mapping
    # ------------------------------------------------------------------

    def transform_point(self, normalized_camera_point):
        """Map a normalised camera coordinate to a canvas coordinate.

        Returns (x, y) in canvas space or *None* if not calibrated.
        """
        if self._matrix is None or cv2 is None or np is None:
            return None
        x = float(normalized_camera_point[0])
        y = float(normalized_camera_point[1])
        pt = np.array([[[x, y]]], dtype=np.float32)
        result = cv2.perspectiveTransform(pt, self._matrix)
        cx = float(result[0][0][0])
        cy = float(result[0][0][1])
        return cx, cy

    def is_inside_board(self, normalized_camera_point):
        """Return True if the point lies inside the whiteboard quad.

        When not calibrated the method returns True so that drawing
        falls back to the full-frame behaviour.
        """
        if not self.source_points or len(self.source_points) != 4:
            return True
        if cv2 is None or np is None:
            return True
        contour = np.array(self.source_points, dtype=np.float32)
        pt = (float(normalized_camera_point[0]),
              float(normalized_camera_point[1]))
        return cv2.pointPolygonTest(contour, pt, False) >= 0

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path=None):
        """Persist calibration corners to a JSON file."""
        path = path or self._DEFAULT_PATH
        data = {"source_points": self.source_points}
        with open(path, "w") as fh:
            json.dump(data, fh, indent=2)

    def load(self, path=None):
        """Load calibration from a JSON file and recompute homography.

        Returns True on success, False on any error.
        """
        path = path or self._DEFAULT_PATH
        if not os.path.isfile(path):
            return False
        try:
            with open(path, "r") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            return False
        corners = data.get("source_points", [])
        if len(corners) != 4:
            return False
        return self.calibrate(corners)

    # ------------------------------------------------------------------
    # Legacy API compatibility
    # ------------------------------------------------------------------

    def add_correspondence(self, image_point, board_point):
        """Legacy method from the scaffold. Prefer :meth:`calibrate`."""
        if len(self.source_points) >= 4:
            raise ValueError(
                "Calibration accepts exactly four point pairs; reset first.")
        self.source_points.append(tuple(image_point))
