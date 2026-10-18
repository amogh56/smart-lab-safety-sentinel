# Smart Lab Safety Sentinel — PipeGen Edge AI Vision PRD & Traceability

**Track:** Track A — PipeGen (Perception)  
**Challenge:** Embedded SF: CraftifAI Physical  
**Target Platform:** NVIDIA Jetson Orin Nano (8GB) / Tensor Core Edge GPU (PipeGen v0.5.1 / DeepStream / TensorRT)  
**Sensors:** Live Physical Camera (V4L2 `/dev/video0` or macOS AVFoundation HD Cam)  
**Output Sinks:** Hardware Alarm Annunciator Sink (5Hz Strobe LED, 2.4kHz Buzzer), MQTT Broker (`lab/safety/sentinel/alerts`), and JSONL Audit Log  

---

## 1. Executive Summary & Purpose

The **Smart Lab Safety Sentinel** is an edge AI-powered active physical safety monitoring system built using **CraftifAI PipeGen v0.5.1**. It turns human-specified natural language safety policies into a hardware-accelerated, real-time computer vision pipeline executed on NVIDIA Jetson / TensorRT.

The system processes live camera feeds in real time, tracks humans within the scene using spatial bounding boxes and bottom-center foot contact points, evaluates geometric entry into a configurable Restricted Hazard Zone (Region of Interest - ROI), and broadcasts debounced, structured intrusion telemetry to an edge annunciator and central safety broker.

---

## 2. PipeGen Pipeline Architecture Diagram

```
+-----------------------------------------------------------------------------------------+
|                                PIPEGEN v0.5.1 EDGE VISION PIPELINE                      |
|                                                                                         |
|  [ Physical USB Camera ]                                                                |
|            |                                                                            |
|            v  V4L2 / AVFoundation (1920x1080 @ 30 FPS, YUYV)                            |
|  +--------------------+                                                                 |
|  |  nvv4l2camerasrc   |                                                                 |
|  +--------------------+                                                                 |
|            |                                                                            |
|            v  Raw Video Stream                                                          |
|  +--------------------+                                                                 |
|  |  nvvideoconvert    | --> Hardware Colorspace Conversion: YUYV -> RGBA (NVMM Buffer)  |
|  +--------------------+                                                                 |
|            |                                                                            |
|            v  Hardware Unified GPU Memory (NVMM)                                        |
|  +--------------------+                                                                 |
|  |  nvstreammux       | --> Batch Formation (Batch=1, 640x640, 30 FPS Lock)             |
|  +--------------------+                                                                 |
|            |                                                                            |
|            v                                                                            |
|  +--------------------+                                                                 |
|  |      nvinfer       | --> TensorRT 8.6/10.x YOLOv8 Engine (FP16/INT8 Quantized)       |
|  | (Primary Detector) |     Human / Person Detection (Conf >= 0.65, IOU >= 0.45)        |
|  +--------------------+                                                                 |
|            |                                                                            |
|            v  Tensor Bounding Box Metadata                                              |
|  +--------------------+                                                                 |
|  |      nvtracker     | --> NvDCF Multi-Object Visual Tracker (Persistent Object IDs)    |
|  +--------------------+                                                                 |
|            |                                                                            |
|            v  Tracked Objects (ID, Box, Velocity)                                       |
|  +--------------------+                                                                 |
|  |   nvdsanalytics    | --> Geometric Ray-Casting & Bottom-Center Foot Contact Anchor    |
|  |   (Spatial ROI)    |     Zone Status: OCCUPIED / CLEAR, 3-Frame Temporal Debounce    |
|  +--------------------+                                                                 |
|            |                                                                            |
|            +-------------------------+-------------------------+                        |
|            v                         v                         v                        |
|  +--------------------+    +--------------------+    +--------------------+             |
|  |      nvdsosd       |    |    nvmsgconv       |    |   Health Watchdog  |             |
|  | (Hardware Overlay) |    |  (JSON Serializer) |    |  (Heartbeat Ping)  |             |
|  +--------------------+    +--------------------+    +--------------------+             |
|            |                         |                         |                        |
|            v (HDMI / Live UI)        v                         v                        |
|  [ Screen / Web Stream ]   +--------------------+    +--------------------+             |
|                            |    nvmsgbroker     |    | PipeGen Audit File |             |
|                            | (MQTT /dev/ttyUSB) |    | (telemetry.jsonl)  |             |
|                            +--------------------+    +--------------------+             |
+--------------------------------------|--------------------------------------------------+
                                       |
                                       v Actionable Output Stream (REQ-03, REQ-04)
                     +-----------------------------------+
                     |  EDGE ALARM ANNUNCIATOR SINK      |
                     |  - Red Strobe Visual Warning      |
                     |  - 2.4 kHz Audible Siren          |
                     |  - Fail-Safe Watchdog (5000 ms)   |
                     +-----------------------------------+
```

---

## 3. Functional Requirements & Acceptance Criteria

| Requirement ID | Requirement Description | Verification Method | Traced Implementation | Traced Test |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-01** | The vision pipeline must detect people in the live camera feed with confidence $\ge 0.65$ within $35\text{ ms}$ latency budget. | Live camera inference benchmark against ground truth person frames. | `vision_sentinel/detector.py`<br>`pipegen/pipeline_ir.json` | `tests/test_e2e_traceability.py::test_req01_person_detection_live_feed` |
| **REQ-02** | The pipeline must generate a structured event when a person is classified as entering the designated restricted zone using bottom-center foot contact anchor and 3-frame debounce. | Geometric ray-casting unit tests with inside/outside coordinate sets. | `vision_sentinel/zone_classifier.py`<br>`vision_sentinel/sentinel_vision.py` | `tests/test_e2e_traceability.py::test_req02_structured_intrusion_event` |
| **REQ-03** | The pipeline must serialize and dispatch structured intrusion events over standard industrial edge interfaces (MQTT on `lab/safety/sentinel/alerts` and serial stream). | Mock subscriber and socket validation verifying payload schema, timestamp, and metadata. | `vision_sentinel/event_publisher.py` | `tests/test_e2e_traceability.py::test_req03_event_dispatch_mqtt_serial` |
| **REQ-04** | On detecting an intrusion event, the system must trigger immediate physical warning indicators (5 Hz red strobe alert and 2.4 kHz audible siren alarm). | Actuator state verification in hardware telemetry loop. | `vision_sentinel/sentinel_vision.py` | `tests/test_e2e_traceability.py::test_req04_hazard_warning_actuation` |
| **REQ-05** | When the restricted zone has remained clear of people for the configured period ($T_{\text{clear}} = 3000\text{ ms}$), the system must automatically return to the safe normal state and emit `ZONE_CLEARED`. | Timeout countdown test and state transition sequence validation. | `vision_sentinel/sentinel_vision.py` | `tests/test_e2e_traceability.py::test_req05_automatic_area_clear_restoration` |
| **REQ-06** | The pipeline must stream telemetry, FPS throughput, and watchdog health status continuously through serial and MQTT interfaces at $\ge 1\text{ Hz}$. | Watchdog heartbeat inspection verifying continuous health telemetry. | `vision_sentinel/event_publisher.py` | `tests/test_e2e_traceability.py::test_req06_telemetry_and_watchdog_stream` |
| **REQ-07** | The requirements must be linked to corresponding code implementations and tests in the formal PipeGen Verification Report. | Traceability matrix generation verifying 100% bidirectional coverage. | `docs/PIPEGEN_VERIFICATION_REPORT.md`<br>`docs/PIPEGEN_SUBMISSION_DOSSIER.md` | `tests/test_e2e_traceability.py::test_req07_pipegen_traceability_report` |

---

## 4. Acceptance Test Summary Table

| Test ID | Test Name | Stimulus / Precondition | Expected Result | Pass Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **AT-01.1** | Human Detection Precision | Synthetic and live test frames with person bounding box ($x=400, y=400, w=160, h=300$). | Bounding box detected with $\text{confidence} \ge 0.65$; inference latency $\le 35\text{ ms}$. | REQ-01 |
| **AT-01.2** | Spatial ROI Intrusion Logic | Person moves bottom-center foot coordinate $(480, 700)$ into polygon $((350, 400), (850, 400), (850, 800), (350, 800))$. | Pipeline generates `INTRUSION_ALERT` with `zone_status="OCCUPIED"` after 3-frame debounce. | REQ-02 |
| **AT-02.1** | Edge Output Dispatch | Intrusion detected by vision pipeline. | Valid JSON packet dispatched to MQTT topic `lab/safety/sentinel/alerts` and appended to local telemetry log. | REQ-03 |
| **AT-02.2** | Warning Actuation | System transitions to alert state. | Red alert indicator active, buzzer state active, latency from frame capture to alert dispatch $\le 50\text{ ms}$. | REQ-04 |
| **AT-03** | Auto Clear Recovery | Person exits ROI; zero detections inside ROI for $t \ge 3000\text{ ms}$. | System emits `ZONE_CLEARED` event; alert state deactivated; clear duration recorded. | REQ-05 |
| **AT-04** | Telemetry & Heartbeat | System operates continuously in normal or alert state. | Heartbeat frames emitted with `pipeline_health="OK"`, uptime, and FPS metrics. | REQ-06 |
| **AT-05** | PipeGen Verification | Execute full automated test suite (`tests/test_e2e_traceability.py`). | 100% (7/7) tests pass; `PIPEGEN_VERIFICATION_REPORT.md` generated. | REQ-07 |

---

## 5. Event Schema (PipeGen Industrial Telemetry)

### Intrusion Event Payload (`INTRUSION_ALERT`)
```json
{
  "event_id": "evt_1729227600_001",
  "event_type": "INTRUSION_ALERT",
  "timestamp": 1729227600.412,
  "source_node": "pipegen_sentinel_edge01",
  "target_device": "edge_alarm_annunciator",
  "zone_id": "ZONE_DANGER_ALPHA",
  "zone_status": "OCCUPIED",
  "intrusion_count": 1,
  "confidence": 0.88,
  "anchor_point": {
    "x": 480,
    "y": 700,
    "method": "bottom_center_foot_contact"
  },
  "bounding_box": {
    "x": 400,
    "y": 400,
    "w": 160,
    "h": 300
  },
  "debounce_frames": 3,
  "pipeline_fps": 31.4,
  "inference_latency_ms": 18.47,
  "alert_state": {
    "red_warning_led": "ACTIVE_5HZ_STROBE",
    "buzzer_siren": "ACTIVE_2400HZ"
  }
}
```

### Zone Cleared Event Payload (`ZONE_CLEARED`)
```json
{
  "event_id": "evt_1729227604_089",
  "event_type": "ZONE_CLEARED",
  "timestamp": 1729227604.120,
  "source_node": "pipegen_sentinel_edge01",
  "target_device": "edge_alarm_annunciator",
  "zone_id": "ZONE_DANGER_ALPHA",
  "zone_status": "CLEAR",
  "intrusion_count": 0,
  "clear_duration_ms": 3000,
  "alert_state": {
    "red_warning_led": "DEACTIVATED",
    "buzzer_siren": "DEACTIVATED"
  }
}
```

### Telemetry Heartbeat Payload (`HEARTBEAT`)
```json
{
  "event_id": "hb_1729227610_015",
  "event_type": "HEARTBEAT",
  "timestamp": 1729227610.000,
  "source_node": "pipegen_sentinel_edge01",
  "uptime_seconds": 3600,
  "pipeline_health": "OK",
  "current_fps": 31.2,
  "total_frames_processed": 112320,
  "current_state": "NORMAL",
  "active_intrusions": 0
}
```
