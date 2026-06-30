import os
import time
import requests
from config.secret import dev_key, rpi_IP, PORT

SERVER_URL = os.getenv("CC_SERVER_URL", f"{rpi_IP}:{PORT}")
API_KEY = os.getenv("CC_API_KEY", dev_key)

event_buffer = {}
_session = requests.Session()


def emit(payload: dict):
    tid = payload.get("track_id")
    ptype = payload.get("type")

    if ptype == "event_opened":
        event_buffer[tid] = {
            "camera_id": payload["camera_id"],
            "threat_score": 0,
            "image_path": None,
            "objects": {}
        }

    elif ptype == "vehicle_update":
        if tid in event_buffer:
            event_buffer[tid]["objects"][tid] = {
                "object_type": payload["vehicle_type"],
                "behavior": "unknown",
                "recognition": "unknown",
                "confidence": 1.0,
                "vehicle": {
                    "license_plate": "",
                    "primary_color": payload.get("primary_color", ""),
                    "vehicle_type": payload["vehicle_type"],
                    "vehicle_function": "unknown"
                }
            }

    elif ptype == "plate_detected":
        if tid in event_buffer and tid in event_buffer[tid]["objects"]:
            obj = event_buffer[tid]["objects"][tid]
            if obj.get("vehicle"):
                obj["vehicle"]["license_plate"] = payload["plate_text"]

    elif ptype == "person_update":
        if tid in event_buffer:
            event_buffer[tid]["objects"][tid] = {
                "object_type": "person",
                "behavior": payload.get("behavior", "unknown"),
                "recognition": "unknown",
                "confidence": payload.get("confidence", 1.0),
                "vehicle": None
            }

    elif ptype == "event_closed":
        if tid not in event_buffer:
            return
        buf = event_buffer.pop(tid)
        objects = list(buf["objects"].values())
        if not objects:
            return

        event_payload = {
            "camera_id": buf["camera_id"],
            "threat_score": buf["threat_score"],
            "image_path": buf["image_path"],
            "objects": objects
        }

        try:
            r = _session.post(
                f"{SERVER_URL}/api/events",
                json=event_payload,
                headers={"x-api-key": API_KEY},
                timeout=5
            )
            r.raise_for_status()
            print(f"[emit] Event for track {tid} posted: {r.json()}")
        except requests.RequestException as e:
            print(f"[emit] Failed to post event for track {tid}: {e}")
