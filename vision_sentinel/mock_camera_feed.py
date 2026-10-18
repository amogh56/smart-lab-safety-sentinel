"""
Smart Lab Safety Sentinel - Mock Camera & Scenario Generator
Generates synthetic video frames and simulated person trajectories
for headless testing and verification when physical camera is unavailable.
"""

import time
import math
from typing import List, Dict, Any, Tuple

class MockCameraSimulator:
    def __init__(self, width: int = 1280, height: int = 720, fps: int = 30):
        self.width = width
        self.height = height
        self.fps = fps
        self.frame_index = 0
        self.start_time = time.time()

        # Simulated actors with trajectory state
        # Actor 1: Traverses from safe area (top-left) into restricted zone, lingers, then exits
        self.actors = [
            {
                "id": 101,
                "confidence": 0.91,
                "w": 140,
                "h": 280,
                "speed_x": 4.5,
                "speed_y": 3.0,
                "curr_x": 100.0,
                "curr_y": 120.0,
                "state": "APPROACHING"
            }
        ]

    def read_synthetic_detections(self) -> Tuple[bool, List[Dict[str, Any]], Dict[str, Any]]:
        """
        Advances the simulation by 1 frame and returns detected persons [x, y, w, h, conf, track_id].
        """
        self.frame_index += 1
        elapsed = self.frame_index / float(self.fps)

        detections = []
        for actor in self.actors:
            # Trajectory phase based on time
            # Phase 1: 0 - 3s: Walking outside zone (Safe)
            # Phase 2: 3 - 8s: Enters Restricted Zone (Intrusion!)
            # Phase 3: 8 - 12s: Exits Restricted Zone back to Safe area
            # Phase 4: 12 - 16s: Remains outside zone (Clear duration elapses)
            t_cycle = elapsed % 16.0

            if t_cycle < 3.0:
                # Outside zone (x: 100 to 280, y: 150)
                pos_x = 100.0 + (t_cycle / 3.0) * 180.0
                pos_y = 150.0
                actor["state"] = "SAFE_OUTSIDE"
            elif t_cycle < 8.0:
                # Inside restricted zone (x: 450 to 650, y: 350 to 450 -> bottom center anchor at y=630~730 in zone)
                progress = (t_cycle - 3.0) / 5.0
                pos_x = 350.0 + math.sin(progress * math.pi) * 200.0
                pos_y = 320.0 + progress * 50.0 # anchor at 320 + 280 = 600 (deep in zone [0.45..0.95])
                actor["state"] = "INTRUDING"
            elif t_cycle < 12.0:
                # Exiting zone (moves left towards x=120, y=140)
                progress = (t_cycle - 8.0) / 4.0
                pos_x = 550.0 - progress * 430.0
                pos_y = 350.0 - progress * 200.0 # anchor moves to 150 + 280 = 430 (< 0.45 threshold)
                actor["state"] = "EXITING"
            else:
                # Lingering outside (Safe)
                pos_x = 120.0 + math.sin(t_cycle) * 20.0
                pos_y = 140.0
                actor["state"] = "SAFE_OUTSIDE"

            bbox = (int(pos_x), int(pos_y), actor["w"], actor["h"])
            detections.append({
                "track_id": actor["id"],
                "confidence": actor["confidence"],
                "bbox": bbox,
                "sim_state": actor["state"]
            })

        meta = {
            "frame_index": self.frame_index,
            "sim_time": elapsed,
            "width": self.width,
            "height": self.height
        }
        return True, detections, meta
