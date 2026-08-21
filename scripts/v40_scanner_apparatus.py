"""Sealed WIA scanner apparatus for V40 anonymous physical interventions."""
from __future__ import annotations

import hashlib
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "scripts/v40_wia_capture.ps1"
LEVEL_TO_CONTROL = {0: 200, 1: 425, 2: 650, 3: 875, 4: 1125, 5: 1350, 6: 1575, 7: 1800}


def _commitment(batch_id, order, seed_commitment):
    payload = {"batch_id": batch_id, "order": order, "seed_commitment": seed_commitment}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _capture(level: int):
    temporary = tempfile.NamedTemporaryFile(prefix="akgm-v40-", suffix=".bmp", delete=False)
    path = Path(temporary.name)
    temporary.close()
    path.unlink()
    try:
        receipt = None
        for attempt in range(3):
            if path.exists():
                path.unlink()
            time.sleep(2.0)
            completed = subprocess.run(
                [
                    "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", str(CAPTURE), "-OutputPath", str(path),
                    "-Brightness", str(LEVEL_TO_CONTROL[level]), "-Contrast", "1000",
                    "-Resolution", "75", "-Extent", "96",
                ],
                check=True, capture_output=True, text=True, encoding="utf-8", timeout=90,
            )
            lines = completed.stdout.strip().splitlines()
            if not lines:
                continue
            receipt = json.loads(lines[-1])
            deadline = time.monotonic() + 2
            while (not path.exists() or path.stat().st_size == 0) and time.monotonic() < deadline:
                time.sleep(0.05)
            if path.exists() and path.stat().st_size > 0 and receipt.get("bytes", 0) > 0:
                receipt["adapter_attempt_count"] = attempt + 1
                break
        else:
            raise RuntimeError(f"WIA failed to produce a nonempty scan after cooldown retries: {receipt}")
        raw = path.read_bytes()
        with Image.open(path) as image:
            grayscale = image.convert("L")
            stats = ImageStat.Stat(grayscale)
            histogram = grayscale.histogram()
            pixels = grayscale.width * grayscale.height
            response = stats.mean[0] / 255
            dispersion = stats.stddev[0] / 255
            dark_fraction = sum(histogram[:16]) / pixels
            bright_fraction = sum(histogram[240:]) / pixels
            dimensions = [grayscale.width, grayscale.height]
        return {
            "anonymous_level": level,
            "response": response,
            "dispersion": dispersion,
            "dark_fraction": dark_fraction,
            "bright_fraction": bright_fraction,
            "pixel_dimensions": dimensions,
            "raw_digest": hashlib.sha256(raw).hexdigest(),
            "raw_bytes": len(raw),
            "device_receipt": receipt,
            "measured_at_unix_ns": time.time_ns(),
            "raw_image_retained": False,
        }
    finally:
        if path.exists():
            path.unlink()


def main():
    pending = None
    measured = set()
    prediction_commitments = []
    event_index = 0
    for line in sys.stdin:
        request = json.loads(line)
        operation = request.get("op")
        if operation == "metadata":
            response = {
                "ok": True,
                "broker_pid": os.getpid(),
                "apparatus": "anonymous_external_wia_optical_sensor_v40",
                "available_anonymous_levels": list(LEVEL_TO_CONTROL),
                "safe_control_min": min(LEVEL_TO_CONTROL),
                "safe_control_max": max(LEVEL_TO_CONTROL),
                "human_quantity_names_exposed_to_learner": False,
                "measurement_exists_before_request": False,
                "raw_images_retained": False,
            }
        elif operation == "commit_prediction":
            digest = str(request.get("commitment", ""))
            if len(digest) != 64:
                response = {"ok": False, "error": "invalid_prediction_commitment"}
            else:
                response = {"ok": True, "event_index": event_index, "commitment": digest, "committed_at_unix_ns": time.time_ns()}
                prediction_commitments.append(response)
                event_index += 1
        elif operation == "commit_batch":
            order = [int(value) for value in request["order"]]
            expected = _commitment(request["batch_id"], order, request["seed_commitment"])
            valid = expected == request["commitment"] and len(order) == len(set(order)) and all(value in LEVEL_TO_CONTROL and value not in measured for value in order)
            requires_prediction = bool(request.get("requires_prediction", False))
            if pending is not None or not valid or (requires_prediction and not prediction_commitments):
                response = {"ok": False, "error": "invalid_or_overlapping_batch_commitment"}
            else:
                pending = dict(request)
                response = {"ok": True, "event_index": event_index, "commitment": expected}
                event_index += 1
        elif operation == "run_batch":
            if pending is None:
                response = {"ok": False, "error": "batch_commitment_required"}
            else:
                started = time.time_ns()
                results = [_capture(level) for level in pending["order"]]
                measured.update(pending["order"])
                response = {
                    "ok": True, "event_index": event_index,
                    "batch_id": pending["batch_id"], "commitment": pending["commitment"],
                    "started_at_unix_ns": started, "ended_at_unix_ns": time.time_ns(),
                    "results": results,
                }
                event_index += 1
                pending = None
        elif operation == "shutdown":
            print(json.dumps({"ok": True}), flush=True)
            return 0
        else:
            response = {"ok": False, "error": "unsupported_operation"}
        print(json.dumps(response, separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
