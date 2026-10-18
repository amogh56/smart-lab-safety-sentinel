# Smart Lab Safety Sentinel — PipeGen Pipeline Architecture

**Document Version:** 2.0.0 (PipeGen Track A Submission)  
**Track:** Track A — PipeGen (Perception)  
**Frameworks:** NVIDIA DeepStream 6.4/7.0 + TensorRT 8.6/10.x (CraftifAI PipeGen v0.5.1)  
**Target Hardware:** NVIDIA Jetson Orin Nano (8GB) / Tensor Core Edge GPU  

---

## 1. End-to-End PipeGen Pipeline Architecture

The **Smart Lab Safety Sentinel** is an industrial edge vision pipeline generated and validated using **CraftifAI PipeGen v0.5.1**. The system is constructed as a low-latency, zero-memory-copy hardware pipeline running atop NVIDIA GStreamer and DeepStream plugins in unified GPU memory (`NVMM`).

```
+---------------------------------------------------------------------------------------------------+
|                            CRAFTIFAI PIPEGEN v0.5.1 PIPELINE GRAPH (9 NODES)                      |
|                                                                                                   |
|  [ Physical USB Camera ]                                                                          |
|            |                                                                                      |
|            v (V4L2 / AVFoundation 1920x1080 @ 30 FPS)                                             |
|  +--------------------+                                                                           |
|  |  nvv4l2camerasrc   | --> Hardware capture driver (DMA buffer allocation)                       |
|  +--------------------+                                                                           |
|            |                                                                                      |
|            v (Raw YUYV video)                                                                     |
|  +--------------------+                                                                           |
|  |  nvvideoconvert    | --> Hardware Colorspace Conversion: YUYV -> RGBA (Zero-Copy NVMM)         |
|  +--------------------+                                                                           |
|            |                                                                                      |
|            v (NVMM Buffer)                                                                        |
|  +--------------------+                                                                           |
|  |    nvstreammux     | --> Batch Formation & Normalization (Batch=1, 640x640, 30 FPS Lock)       |
|  +--------------------+                                                                           |
|            |                                                                                      |
|            v                                                                                      |
|  +--------------------+                                                                           |
|  |      nvinfer       | --> TensorRT 8.6/10.x YOLOv8 Engine (FP16/INT8 Quantized)                 |
|  | (Primary Detector) |     Human / Person Detection (Conf >= 0.65, IOU >= 0.45)                  |
|  +--------------------+                                                                           |
|            |                                                                                      |
|            v (Bounding Box Tensor Metadata)                                                       |
|  +--------------------+                                                                           |
|  |      nvtracker     | --> NvDCF Multi-Object Visual Tracker (Persistent Track IDs)              |
|  +--------------------+                                                                           |
|            |                                                                                      |
|            v (Tracked Objects: ID, Box, Trajectory)                                               |
|  +--------------------+                                                                           |
|  |   nvdsanalytics    | --> Geometric Ray-Casting & Bottom-Center Foot Contact Anchor              |
|  |   (Spatial ROI)    |     Zone Status: OCCUPIED / CLEAR, 3-Frame Temporal Debounce              |
|  +--------------------+                                                                           |
|            |                                                                                      |
|            +-------------------------+-------------------------+                                  |
|            v                         v                         v                                  |
|  +--------------------+    +--------------------+    +--------------------+                       |
|  |      nvdsosd       |    |    nvmsgconv       |    |   Health Watchdog  |                       |
|  | (Hardware Overlay) |    |  (JSON Serializer) |    |  (Heartbeat Ping)  |                       |
|  +--------------------+    +--------------------+    +--------------------+                       |
|            |                         |                         |                                  |
|            v (HDMI / Live UI)        v                         v                                  |
|  [ Screen / Web Stream ]   +--------------------+    +--------------------+                       |
|                            |    nvmsgbroker     |    | PipeGen Audit File |                       |
|                            | (MQTT /dev/ttyUSB) |    | (telemetry.jsonl)  |                       |
|                            +--------------------+    +--------------------+                       |
+--------------------------------------|------------------------------------------------------------+
                                       |
                                       v Actionable Alert Stream (REQ-03, REQ-04)
                     +---------------------------------------+
                     |  EDGE ALARM ANNUNCIATOR SINK          |
                     |  - Red Warning Strobe (5 Hz)          |
                     |  - High-Decibel Siren (2.4 kHz)       |
                     |  - Fail-Safe Watchdog (5000 ms)       |
                     +---------------------------------------+
```

---

## 2. Geometric Spatial ROI & Ground-Plane Anchor

Intrusions into the restricted chemical / machinery hazard zone are evaluated using a bottom-center foot contact anchor $(x_{\text{anchor}}, y_{\text{anchor}})$ rather than an arbitrary bounding box centroid:

$$x_{\text{anchor}} = x_{\min} + \frac{w}{2}$$
$$y_{\text{anchor}} = y_{\min} + h$$

Point containment within the arbitrary $N$-vertex polygon is computed using the Jordan curve theorem ray-casting algorithm:

```
(0,0) +---------------------------------------------------+ (W,0)
      |                                                   |
      |          Safe Lab Area                            |
      |                                                   |
      |          +-------------------+                    |
      |          | Restricted Zone   |                    |
      |          | (Chemical Hazard) |                    |
      |          |                   |                    |
      |          |         * [Anchor]|                    |
      |          +---------|---------+                    |
      |                    |                              |
      |             +------v------+                       |
      |             | Detected    |                       |
      |             | Person Box  |                       |
      |             +-------------+                       |
(0,H) +---------------------------------------------------+ (W,H)
```

### Debouncing & Clearing State Logic
1. **Intrusion Trigger ($T_{\text{in}} = 3\text{ frames}$):** The anchor must reside inside the ROI polygon for 3 consecutive frames before an `INTRUSION_ALERT` is published, eliminating single-frame false alarms.
2. **Clear Restoration ($T_{\text{clear}} = 3000\text{ ms}$):** When all detected persons leave the ROI polygon, the system waits for 3000 ms of continuous clear frames before resetting the state to `NORMAL` and issuing a `ZONE_CLEARED` event.

---

## 3. Communication & Edge Broker Integration

### 3.1 Network Edge Broker (MQTT)
- **Protocol:** MQTT v3.1.1
- **Port:** 1883
- **Topic Alerts:** `lab/safety/sentinel/alerts`
- **Topic Heartbeat:** `lab/safety/sentinel/heartbeat`
- **QoS Level:** QoS 1 (Guaranteed at least once delivery)

### 3.2 Hardware Bridge (USB-UART Serial)
- **Baud Rate:** 115,200 baud
- **Format:** 8 Data bits, 1 Stop bit, No Parity (8N1)
- **Framing:** Line-delimited JSON (`\n` newline terminated)

---

## 4. Edge Alarm Annunciator & Physical Actuation Sink

The PipeGen vision pipeline interfaces directly with physical edge annunciator hardware to translate perception into physical action:

| Component | Physical Interface | Operational Mode | Functional Purpose |
| :--- | :--- | :--- | :--- |
| **Red Warning Strobe** | GPIO 2 / Relay Sink | 5 Hz pulse (100ms ON / 100ms OFF) | High-visibility optical warning on intrusion (REQ-04) |
| **Green Safe Status** | GPIO 4 / Relay Sink | Steady state ON | Visual confirmation that area is safe and clear (REQ-05) |
| **Audible Siren** | GPIO 18 / PWM Sink | 2.4 kHz audible siren (50% duty) | High-decibel immediate audible warning on intrusion (REQ-04) |
| **Telemetry Link** | GPIO 22 / UART | 120ms pulse on packet reception | Health heartbeat and communication link activity (REQ-06) |

---

## 5. Fail-Safe Behavior & Watchdog Architecture

1. **Heartbeat Protocol:** The vision pipeline dispatches a `HEARTBEAT` packet every 2000 ms with pipeline health metrics and current FPS.
2. **Watchdog Window:** If no packet arrives at the annunciator sink within 5000 ms, the system automatically enters `STATE_FAULT`.
3. **Safe Degraded Mode (`STATE_FAULT`):**
   - The loud continuous 2.4 kHz siren is silenced to prevent nuisance alarms during edge compute maintenance.
   - The red and green indicators alternate in an amber caution cadence.
   - The telemetry link logs communication failure warnings for industrial safety technicians.
   - Upon heartbeat restoration, the system automatically transitions back to `STATE_NORMAL`.
