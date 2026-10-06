"""MediaPipe Hands adapter. Coordinates are normalized to [0, 1]."""

try:
    import cv2
    import mediapipe as mp
except ImportError:
    cv2 = mp = None


class HandDetector:
    def __init__(self, max_hands=1, detection_confidence=0.6, tracking_confidence=0.5):
        self.hands = None
        self.error = None
        if mp is None:
            self.error = "MediaPipe is not installed. Install dependencies from requirements.txt."
            return
        self._mp = mp
        self.hands = mp.solutions.hands.Hands(
            static_image_mode=False, max_num_hands=max_hands,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence)

    def process(self, frame):
        if self.hands is None:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.hands.process(rgb)
        if not result.multi_hand_landmarks:
            return None
        points = result.multi_hand_landmarks[0].landmark
        return [(p.x, p.y, p.z) for p in points]

    def draw_landmarks(self, frame, landmarks):
        if landmarks is None or self.hands is None:
            return
        h, w = frame.shape[:2]
        converted = self._mp.framework.formats.landmark_pb2.NormalizedLandmarkList(
            landmark=[self._mp.framework.formats.landmark_pb2.NormalizedLandmark(x=x, y=y, z=z)
                      for x, y, z in landmarks])
        self._mp.solutions.drawing_utils.draw_landmarks(
            frame, converted, self._mp.solutions.hands.HAND_CONNECTIONS)

    def close(self):
        if self.hands is not None:
            self.hands.close()
