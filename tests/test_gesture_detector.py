"""Focused, camera-independent tests for the rule-based gesture adapter."""

import unittest

from gestures.gesture_detector import GestureDetector


def pose_for(index=True, middle=False, ring=False, pinky=False):
    """Build landmarks with straight or visibly flexed finger joints."""
    points = [[0.5, 0.5, 0.0] for _ in range(21)]
    states = {"index": index, "middle": middle, "ring": ring, "pinky": pinky}
    joints = GestureDetector.FINGER_JOINTS
    for name, (mcp, pip, tip) in joints.items():
        if states[name]:
            points[mcp] = [0.30, 0.60, 0.0]
            points[pip] = [0.40, 0.50, 0.0]
            points[tip] = [0.50, 0.40, 0.0]
        else:
            points[mcp] = [0.30, 0.60, 0.0]
            points[pip] = [0.40, 0.50, 0.0]
            points[tip] = [0.35, 0.60, 0.0]
    return points


class GestureDetectorTests(unittest.TestCase):
    def test_write_requires_three_stable_frames(self):
        detector = GestureDetector()
        pose = pose_for(index=True)
        self.assertEqual(detector.detect(pose, (640, 480)), "IDLE")
        self.assertEqual(detector.detect(pose, (640, 480)), "IDLE")
        self.assertEqual(detector.detect(pose, (640, 480)), "WRITE")

    def test_two_fingers_select_erase_and_idle_cancels(self):
        detector = GestureDetector()
        write = pose_for(index=True)
        erase = pose_for(index=True, middle=True)
        for _ in range(3):
            mode = detector.detect(write, (640, 480))
        self.assertEqual(mode, "WRITE")
        for _ in range(3):
            mode = detector.detect(erase, (640, 480))
        self.assertEqual(mode, "ERASE")
        for _ in range(3):
            mode = detector.detect(pose_for(index=False), (640, 480))
        self.assertEqual(mode, "IDLE")

    def test_missing_hand_resets_history_immediately(self):
        detector = GestureDetector()
        pose = pose_for(index=True)
        for _ in range(3):
            detector.detect(pose, (640, 480))
        self.assertEqual(detector.detect(None), "IDLE")
        self.assertEqual(len(detector.history), 0)

    def test_angle_rule_is_rotation_tolerant(self):
        detector = GestureDetector(history_size=1, min_votes=1)
        points = pose_for(index=True)
        # Rotate the extended index finger pose 90 degrees around its center.
        for index in (5, 6, 8):
            x, y, z = points[index]
            points[index] = [1.0 - y, x, z]
        self.assertEqual(detector.detect(points, (480, 640)), "WRITE")


if __name__ == "__main__":
    unittest.main()
