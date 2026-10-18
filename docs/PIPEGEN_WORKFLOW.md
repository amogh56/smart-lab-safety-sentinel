# PipeGen v0.5.1 Edge AI Vision Workflow Specification

**Pipeline Identifier:** `smart-lab-safety-sentinel-v1`  
**Target Hardware:** NVIDIA Jetson Orin Nano / AGX Orin / Discrete NVIDIA Tensor Core GPU  
**Runtime Engine:** NVIDIA DeepStream SDK 6.4 / 7.0 + TensorRT 8.6 / 10.x + GStreamer 1.20+  
**Execution Orchestrator:** CraftifAI PipeGen v0.5.1  

---

## The 5-Step PipeGen Lifecycle

PipeGen automates the transition from high-level computer vision requirements to low-level, hardware-accelerated C++/GStreamer/DeepStream pipelines without manual buffer plumbing.

```
+-----------------------------------------------------------------------------------------+
|                                PIPEGEN COMPILATION FLOW                                 |
|                                                                                         |
|  [01 REQUIREMENT] --> [02 PIPELINE IR] --> [03 MODEL OPSET] --> [04 COMPILER / TRT]    |
|   - Person Detect      - Directed Graph     - PeopleNet/YOLO     - FP16/INT8 Fusion     |
|   - Zone ROI Logic     - Node Signatures    - 640x640x3 NCHW     - Engine Synthesis     |
|   - Latency < 35ms     - Buffer Types       - Multi-class post   - Latency Profiling    |
|                                                                                         |
|                                         |                                               |
|                                         v                                               |
|                                  [05 RUN & DEPLOY]                                      |
|                                   - Live USB / V4L2                                     |
|                                   - DeepStream App                                      |
|                                   - MQTT / Serial Sink                                  |
|                                   - OSD Overlay                                         |
+-----------------------------------------------------------------------------------------+
```

---

### Step 01: Requirement Definition
- **Vision Target:** Real-time multi-person detection and localization in indoor laboratory environments.
- **Input Stream:** V4L2 USB Camera (`/dev/video0`), resolution 1920x1080 / 1280x720 @ 30 FPS.
- **ROI Geometry:** User-defined polygon bounding restricted lab zone (e.g. Chemical Fume Hood / High Voltage Area).
- **Intrusion Ground Contact Rule:** Evaluation of person anchor point defined at bottom-center $(x_{\text{center}}, y_{\text{bottom}} = y_{\max})$ to represent feet on the ground plane, preventing false alarms from upper-body shadows or head movement outside the zone.
- **Latency Budget:** Inference latency $\le 8\text{ ms}$, pipeline end-to-end latency $\le 30\text{ ms}$.

---

### Step 02: Pipeline Intermediate Representation (Pipeline IR)
PipeGen traces the functional steps into a hardware-agnostic declarative graph (`pipeline_ir.json`).

Key IR Nodes:
1. `V4L2CameraSourceNode`: Decodes USB camera stream into `video/x-raw(memory:NVMM)` hardware memory buffers.
2. `NvVideoConverterNode`: Rescales and normalizes incoming frames to `640x640` RGB planar format.
3. `TensorRTInferenceNode` (`nvinfer`): Executes primary detection engine.
4. `NvTrackerNode` (`nvtracker`): Tracks object centroids with persistent track IDs across frames using NvDCF.
5. `RestrictedZoneClassifierNode`: Evaluates polygon containment of each track's bottom-center anchor against the active zone.
6. `SentinelEventGeneratorNode`: Implements 3-frame debounce and generates structured JSON alerts (`INTRUSION_ALERT`, `ZONE_CLEARED`, `HEARTBEAT`).
7. `MultiBridgeSinkNode`: Dispatches JSON events to MQTT broker (`lab/safety/sentinel/alerts`) and USB-UART serial port, while simultaneously rendering OSD bounding boxes to the monitor.

---

### Step 03: Model Selection & Opset Validation
- **Architecture Selected:** NVIDIA PeopleNet (TAO Toolkit / Pruned ResNet-34) / YOLOv8n-Person.
- **Input Dimensions:** `1 x 3 x 640 x 640` (NCHW, Float32).
- **Output Tensors:**
  - `num_detections`: Shape `[1, 1]`
  - `detection_boxes`: Shape `[1, 100, 4]` (normalized `[ymin, xmin, ymax, xmax]`)
  - `detection_scores`: Shape `[1, 100]` (confidence score for class `Person`)
  - `detection_classes`: Shape `[1, 100]` (class index)
- **Opset Version:** ONNX Opset 17, verified free of unsupported custom GStreamer layers.

---

### Step 04: TensorRT Engine Compilation & Performance Optimization
The PipeGen compiler executes hardware profiling and graph optimization:
1. **Precision Calibration:** FP16 mixed precision enabled on Tensor Cores (`--fp16`).
2. **Layer Fusion:** Vertical fusion of Conv + BatchNorm + SiLU / ReLU activation layers into single fused kernels.
3. **Workspace Allocation:** Set to 2048 MB (`--memPoolSize=workspace:2048`) for kernel auto-tuning.
4. **Engine Generation:** Creates `model_peoplenet_fp16.engine`.

---

### Step 05: Run, Deploy & Monitor
- **Execution Script:** `pipegen run --camera 0` or `deepstream-app -c pipegen/deepstream_app_config.txt` or `python3 vision_sentinel/sentinel_vision.py`.
- **Telemetry Sinks:**
  - MQTT Broker: `localhost:1883` or configurable cloud broker.
  - Serial Bridge: `/dev/ttyUSB0` or virtual serial loopback.
  - OSD Visualizer: Real-time window displaying green/red zones, track labels, and FPS counters.

---

## PipeGen CLI Commands Reference

PipeGen includes an executable command-line interface installed in the project environment (`.venv/bin/pipegen`):

```bash
# Check installed version
pipegen --version
# Output: CraftifAI PipeGen v0.5.1-orbit

# Check system and edge hardware status
pipegen status

# Validate Pipeline IR intermediate representation (DAG node verification)
pipegen ir validate

# Display Pipeline IR graph topology
pipegen ir show

# View NVIDIA TensorRT latency benchmark suite & breakdown
pipegen trt benchmark

# Run the real-time live vision perception sentinel
pipegen run --camera 0
```
