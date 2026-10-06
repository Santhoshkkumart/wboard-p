"""Normalized stroke model, independent of canvas pixel dimensions."""


class Stroke:
    def __init__(self, points=None, color="#182230", width=0.006):
        self.points = list(points or [])
        self.color = color
        self.width = width

    def add(self, point):
        self.points.append((float(point[0]), float(point[1])))
