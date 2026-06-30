import os
import time
import queue
import requests
import threading
from config.secret import rpi_IP, PORT

SERVER_URL = os.getenv("CC_SERVER_URL", f"{rpi_IP}:{PORT}")

_session = requests.Session()
_send_queue = queue.Queue(maxsize=32)


def _worker():
    while True:
        item = _send_queue.get()
        if item is None:
            break
        url, payload = item
        try:
            _session.post(url, json=payload, timeout=1.0)
        except Exception:
            pass


_thread = threading.Thread(target=_worker, daemon=True).start()


def _enqueue(url:str, payload:dict):
    try:
        _send_queue.put_nowait((url, payload))
    except queue.Full:
        pass


_last_metrics_post = 0
_last_live_sent: dict[str, float] = {}  # track_id -> ts
live_throttle_sec = 1.0  # avoid spamming the server


def post_telemetry(workers_active: int, lpr_queue_size: int, active_tracks: int, camera_id="cam_01"):
    """Live health and performance stats"""
    global _last_metrics_post

    now = time.time()
    if now - _last_metrics_post < 0.8:
        return
    _last_metrics_post = now
    _enqueue(f"{SERVER_URL}/api/ingest/telemetry", {
        "camera_id": camera_id,
        "workers_active": workers_active,
        "lpr_queue_size": lpr_queue_size,
        "active_tracks": active_tracks
    })



def post_live(track_id: str, label: str, confidence: float, license_plate: str | None = None, camera_id="cam_01"):
    """Live feed from camera"""
    global _last_live_sent

    now = time.time()
    last = _last_live_sent.get(track_id, 0)
    if now - last < live_throttle_sec and license_plate is None:
        return
    _last_live_sent[track_id] = now
    _enqueue(f"{SERVER_URL}/api/ingest/live", {
        "camera_id": camera_id,
        "track_id": str(track_id),
        "label": label,
        "confidence": float(confidence),
        "license_plate": license_plate
    })

