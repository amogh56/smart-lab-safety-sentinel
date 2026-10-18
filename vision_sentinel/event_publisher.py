"""
Smart Lab Safety Sentinel - Event Publisher Module
Implements REQ-02, REQ-03: Structured JSON event generation and multi-channel
dispatch over MQTT and USB-UART Serial.
"""

import os
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

class SentinelEventPublisher:
    def __init__(
        self,
        mqtt_broker: str = "127.0.0.1",
        mqtt_port: int = 1883,
        topic_alerts: str = "lab/safety/sentinel/alerts",
        topic_heartbeat: str = "lab/safety/sentinel/heartbeat",
        serial_port: Optional[str] = None,
        serial_baudrate: int = 115200,
        log_file: str = "logs/sentinel_events.jsonl",
        enable_mqtt: bool = True,
        enable_serial: bool = True
    ):
        self.topic_alerts = topic_alerts
        self.topic_heartbeat = topic_heartbeat
        self.log_file = log_file
        self.event_counter = 0

        # Create log directory if needed
        os.makedirs(os.path.dirname(self.log_file) if os.path.dirname(self.log_file) else ".", exist_ok=True)

        # Initialize MQTT if library available
        self.mqtt_client = None
        self.mqtt_connected = False
        if enable_mqtt:
            try:
                import paho.mqtt.client as mqtt
                self.mqtt_client = mqtt.Client(client_id="pipegen_safety_sentinel")
                self.mqtt_client.connect_async(mqtt_broker, mqtt_port, 60)
                self.mqtt_client.loop_start()
                self.mqtt_connected = True
                print(f"[+] EventPublisher: Connected asynchronously to MQTT {mqtt_broker}:{mqtt_port}")
            except Exception as e:
                print(f"[-] EventPublisher: MQTT client unavailable ({e}); running in simulated/loopback mode.")

        # Initialize Serial if available
        self.serial_handle = None
        if enable_serial and serial_port:
            try:
                import serial
                self.serial_handle = serial.Serial(serial_port, serial_baudrate, timeout=0.1)
                print(f"[+] EventPublisher: Connected to USB Serial port {serial_port} @ {serial_baudrate} baud")
            except Exception as e:
                print(f"[-] EventPublisher: Physical serial {serial_port} unavailable ({e}); logging to stdout/file.")

    def _get_timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def build_intrusion_event(
        self,
        zone_id: str,
        track_id: int,
        confidence: float,
        bbox: Any,
        anchor_point: Any,
        active_intruders_count: int = 1,
        fps: float = 30.0,
        inference_ms: float = 4.2
    ) -> Dict[str, Any]:
        """Creates the canonical REQ-02 intrusion event."""
        self.event_counter += 1
        return {
            "version": "1.0",
            "event_id": f"evt-{int(time.time())}-{self.event_counter:04d}",
            "timestamp": self._get_timestamp(),
            "event_type": "INTRUSION_ALERT",
            "zone_id": zone_id,
            "zone_status": "OCCUPIED",
            "intruder": {
                "track_id": int(track_id),
                "confidence": round(float(confidence), 3),
                "bbox": [int(v) for v in bbox],
                "anchor_point": [int(v) for v in anchor_point]
            },
            "active_intruders_count": active_intruders_count,
            "metrics": {
                "fps": round(float(fps), 1),
                "inference_ms": round(float(inference_ms), 2)
            }
        }

    def build_clear_event(self, zone_id: str, clear_duration_ms: int = 3000) -> Dict[str, Any]:
        """Creates the canonical REQ-05 zone cleared event."""
        self.event_counter += 1
        return {
            "version": "1.0",
            "event_id": f"evt-{int(time.time())}-{self.event_counter:04d}",
            "timestamp": self._get_timestamp(),
            "event_type": "ZONE_CLEARED",
            "zone_id": zone_id,
            "zone_status": "CLEAR",
            "clear_duration_ms": clear_duration_ms
        }

    def build_heartbeat_event(self, pipeline_health: str = "OK", zone_status: str = "CLEAR") -> Dict[str, Any]:
        """Creates a heartbeat ping for the edge watchdog (REQ-06, Test 4)."""
        return {
            "version": "1.0",
            "event_type": "HEARTBEAT",
            "timestamp": self._get_timestamp(),
            "zone_status": zone_status,
            "pipeline_health": pipeline_health
        }

    def publish_event(self, event_data: Dict[str, Any]) -> str:
        """
        Dispatches structured JSON event across all configured bridges:
        MQTT, USB-UART Serial, and persistent JSONL audit log.
        """
        payload_json = json.dumps(event_data, separators=(',', ':'))
        
        # 1. Dispatch over MQTT
        if self.mqtt_client and self.mqtt_connected:
            topic = self.topic_heartbeat if event_data.get("event_type") == "HEARTBEAT" else self.topic_alerts
            try:
                self.mqtt_client.publish(topic, payload_json, qos=1)
            except Exception as e:
                print(f"[-] MQTT publish error: {e}")

        # 2. Dispatch over Serial UART
        if self.serial_handle and self.serial_handle.is_open:
            try:
                # Delimited by newline for deterministic Arduino streaming parsing
                self.serial_handle.write((payload_json + "\n").encode('utf-8'))
                self.serial_handle.flush()
            except Exception as e:
                print(f"[-] Serial write error: {e}")

        # 3. Append to JSONL audit file
        try:
            with open(self.log_file, "a") as f:
                f.write(payload_json + "\n")
        except Exception:
            pass

        return payload_json

    def close(self):
        if self.mqtt_client:
            try:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            except Exception:
                pass
        if self.serial_handle:
            try:
                self.serial_handle.close()
            except Exception:
                pass
