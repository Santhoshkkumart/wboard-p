"""Index fingertip (MediaPipe landmark 8) accessors."""

INDEX_TIP = 8


def fingertip(landmarks):
    if landmarks is None or len(landmarks) <= INDEX_TIP:
        return None
    x, y = landmarks[INDEX_TIP][:2]
    return float(x), float(y)
