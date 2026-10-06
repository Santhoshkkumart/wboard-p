"""Small OpenCV webcam wrapper with explicit error reporting."""

try:
    import cv2
except ImportError:
    cv2 = None


class Camera:
    def __init__(self, index=0):
        self.index = index
        self.capture = None
        self.error = None

    def open(self):
        if cv2 is None:
            self.error = "OpenCV is not installed. Install dependencies from requirements.txt."
            return False
        self.capture = cv2.VideoCapture(self.index)
        if not self.capture.isOpened():
            self.error = f"Could not open camera {self.index}. Check the webcam connection and permissions."
            self.capture.release()
            self.capture = None
            return False
        self.error = None
        return True

    def read(self):
        if self.capture is None:
            return False, None
        ok, frame = self.capture.read()
        return (ok and frame is not None), frame

    def close(self):
        if self.capture is not None:
            self.capture.release()
            self.capture = None
