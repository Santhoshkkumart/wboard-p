"""Coordinates camera frame processing while keeping each stage modular."""

from hand_tracking.fingertip import fingertip


class FrameProcessor:
    def __init__(self, hand_detector, face_mask):
        self.hand_detector = hand_detector
        self.face_mask = face_mask

    def process(self, frame, show_face=False):
        landmarks = self.hand_detector.process(frame) if self.hand_detector else None
        tip = fingertip(landmarks)
        display = self.face_mask.apply(frame, show_face) if self.face_mask else frame
        return display, landmarks, tip
