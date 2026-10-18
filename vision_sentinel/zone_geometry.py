"""
Smart Lab Safety Sentinel - Zone Geometry Module
Implements robust point-in-polygon ray-casting and foot-anchor calculation
for restricted area boundary enforcement.
"""

from typing import List, Tuple, Dict, Any

class ZoneGeometry:
    def __init__(self, normalized_polygon: List[List[float]], zone_id: str = "RESTRICTED_ZONE_A"):
        """
        :param normalized_polygon: List of [x, y] vertices in 0.0 to 1.0 normalized frame space.
        :param zone_id: Identifier of the restricted perimeter.
        """
        self.zone_id = zone_id
        self.normalized_polygon = [list(pt) for pt in normalized_polygon]
        if len(self.normalized_polygon) < 3:
            raise ValueError("Restricted zone polygon must have at least 3 vertices")

    def get_pixel_polygon(self, frame_width: int, frame_height: int) -> List[Tuple[int, int]]:
        """Converts normalized polygon to absolute pixel coordinates."""
        return [
            (int(pt[0] * frame_width), int(pt[1] * frame_height))
            for pt in self.normalized_polygon
        ]

    @staticmethod
    def calculate_anchor_point(bbox: Tuple[int, int, int, int], mode: str = "BOTTOM_CENTER") -> Tuple[int, int]:
        """
        Computes anchor point for a bounding box [x, y, w, h].
        For safety zone monitoring, BOTTOM_CENTER corresponds to the subject's feet
        on the laboratory floor plane, preventing false positives from head/arm movements.
        """
        x, y, w, h = bbox
        if mode == "BOTTOM_CENTER":
            return (int(x + w / 2.0), int(y + h))
        elif mode == "CENTROID":
            return (int(x + w / 2.0), int(y + h / 2.0))
        elif mode == "TOP_CENTER":
            return (int(x + w / 2.0), int(y))
        else:
            return (int(x + w / 2.0), int(y + h))

    def is_point_inside(self, point: Tuple[float, float], frame_width: int = 1, frame_height: int = 1) -> bool:
        """
        Ray-casting algorithm to determine if a point is inside the arbitrary polygon.
        Can evaluate either normalized coordinates (frame_w=1, frame_h=1) or pixel space.
        """
        px, py = point
        # Normalize if needed
        if frame_width > 1 or frame_height > 1:
            px = px / float(frame_width)
            py = py / float(frame_height)

        n = len(self.normalized_polygon)
        inside = False
        p1x, p1y = self.normalized_polygon[0]

        for i in range(1, n + 1):
            p2x, p2y = self.normalized_polygon[i % n]
            if py > min(p1y, p2y):
                if py <= max(p1y, p2y):
                    if px <= max(p1x, p2x):
                        if p1y != p2y:
                            x_inters = (py - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                            if p1x == p2x or px <= x_inters:
                                inside = not inside
            p1x, p1y = p2x, p2y

        return inside

    def evaluate_person_intrusion(
        self,
        person_bbox: Tuple[int, int, int, int],
        frame_width: int,
        frame_height: int,
        confidence: float
    ) -> Dict[str, Any]:
        """
        Evaluates whether a detected person's foot-anchor penetrates the restricted zone.
        """
        anchor_pixel = self.calculate_anchor_point(person_bbox, mode="BOTTOM_CENTER")
        inside = self.is_point_inside(anchor_pixel, frame_width=frame_width, frame_height=frame_height)

        return {
            "zone_id": self.zone_id,
            "is_inside": inside,
            "anchor_pixel": anchor_pixel,
            "anchor_normalized": (anchor_pixel[0] / frame_width, anchor_pixel[1] / frame_height),
            "bbox": person_bbox,
            "confidence": confidence
        }
