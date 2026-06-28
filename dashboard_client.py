import os
import time
import requests
from config.secret import rpi_IP, PORT

SERVER_URL = os.getenv("CC_SERVER_URL", f"{rpi_IP}:{PORT}")

_last_metrics_post = 0
_last_live_sent = {}  # track_id -> ts
live_throttle_sec = 1.0  # avoid spamming the server


def post_telemetry(workers_active: int, lpr_queue_size: int, active_tracks: int, camera_id="cam_01"):
    """Live health and performance stats"""
    global _last_metrics_post

    now = time.time()
    if now - _last_metrics_post < 0.8:
        return
    _last_metrics_post = now
    try:
        requests.post(f"{SERVER_URL}/api/ingest/telemetry", json={
            "camera_id": camera_id,
            "workers_active": workers_active,
            "lpr_queue_size": lpr_queue_size,
            "active_tracks": active_tracks
        }, timeout=0.4)
    except Exception:
        pass


def post_live(track_id: str, label: str, confidence: float, license_plate: str | None = None, camera_id="cam_01"):
    """Live feed from camera"""
    global _last_live_sent

    now = time.time()
    last = _last_live_sent.get(track_id, 0)
    if now - last < live_throttle_sec and license_plate is None:
        return
    _last_live_sent[track_id] = now
    try:
        requests.post(f"{SERVER_URL}/api/ingest/live", json={
            "camera_id": camera_id,
            "track_id": str(track_id),
            "label": label,
            "confidence": float(confidence),
            "license_plate": license_plate
        }, timeout=0.4)
    except Exception:
        pass
