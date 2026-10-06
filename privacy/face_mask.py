"""Face-only masking using OpenCV's bundled Haar cascade."""

try:
    import cv2
except ImportError:
    cv2 = None


class FaceMask:
    def __init__(self):
        self.detector = None
        if cv2 is not None:
            path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self.detector = cv2.CascadeClassifier(path)

    def apply(self, frame, show_face=False):
        if show_face or cv2 is None or self.detector is None or self.detector.empty():
            return frame
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5,
                                                minSize=(40, 40))
        result = frame.copy()
        for x, y, w, h in faces:
            roi = result[y:y+h, x:x+w]
            if roi.size:
                small = cv2.resize(roi, (max(1, w // 14), max(1, h // 14)), interpolation=cv2.INTER_LINEAR)
                result[y:y+h, x:x+w] = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
        return result
