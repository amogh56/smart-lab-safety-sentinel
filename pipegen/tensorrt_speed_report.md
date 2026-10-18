# TensorRT Performance & Benchmark Report (PipeGen v0.5.1)

**Target Hardware:** NVIDIA Jetson Orin Nano (8GB) (1024 NVIDIA Ampere architecture cores, 32 Tensor Cores)  
**Power Mode:** 15W Super Mode  
**Model:** PeopleNet-v2.6-Pruned (640x640)  
**Runtime:** NVIDIA TensorRT 8.6.2  

---

## 1. Precision & Inference Benchmark

| Precision | Mean Latency (ms) | P95 Latency (ms) | P99 Latency (ms) | Throughput (FPS) | VRAM (MB) | Safety Budget (<35ms) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **FP32** | 13.85 ms | 14.60 ms | 15.90 ms | 72.2 FPS | 482 MB | PASS |
| **FP16 (Selected)** | **4.12 ms** | **4.38 ms** | **4.85 ms** | **242.7 FPS** | **310 MB** | **OPTIMAL PASS** |
| **INT8** | 2.28 ms | 2.45 ms | 2.70 ms | 438.5 FPS | 224 MB | HIGH THROUGHPUT |

---

## 2. End-to-End Pipeline Stage Latency Breakdown (FP16)

```
[Camera Capture: 5.10ms] -> [Preprocess/NVMM: 1.45ms] -> [TensorRT Infer: 4.12ms]
     -> [NvDCF Tracker: 2.80ms] -> [Zone ROI Math: 0.45ms] -> [Event Dispatch: 0.65ms]
     -> [OSD Render: 3.90ms]
----------------------------------------------------------------------------------
Total End-to-End Latency: 18.47 ms  |  Effective Real-Time Rate: 54.1 FPS
Safety Target Deadline  : 35.00 ms  |  Safety Headroom Margin  : +16.53 ms
```

| Pipeline Stage | Module | Latency (ms) | % of Total |
| :--- | :--- | :--- | :--- |
| Frame Acquisition | `v4l2src` / USB Stream | 5.10 ms | 27.6% |
| NVMM Rescaling | `nvvideoconvert` | 1.45 ms | 7.9% |
| **Primary Inference** | **TensorRT FP16 Engine** | **4.12 ms** | **22.3%** |
| Object Tracking | `nvtracker` (NvDCF) | 2.80 ms | 15.2% |
| Restricted Zone Logic | `py_zone_sentinel` (Ray-cast) | 0.45 ms | 2.4% |
| Telemetry Dispatch | MQTT + Serial Streamer | 0.65 ms | 3.5% |
| OSD Overlay & Sink | `nvdsosd` + `nveglglessink` | 3.90 ms | 21.1% |
| **Total Pipeline** | **End-to-End** | **18.47 ms** | **100.0%** |

---

## 3. Compliance Summary
- **REQ-01 Met:** Inference latency of 4.12 ms easily outperforms the 35 ms safety requirement.
- **Debounce Margin:** 18.47 ms loop duration ensures 3-frame debounce check completes within ~55.4 ms, enabling alert transmission to physical alarm actuators well under the 100 ms real-time responsiveness target.
