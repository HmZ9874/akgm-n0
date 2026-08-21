"""Sealed Windows audio apparatus for anonymous V40 physical experiments."""
from __future__ import annotations

import array
import ctypes
import hashlib
import json
import math
import os
import statistics
import sys
import time
from ctypes import wintypes

SAMPLE_RATE = 16_000
AMPLITUDE = 0.06
BASELINE_SECONDS = 0.06
TONE_SECONDS = 0.14
TAIL_SECONDS = 0.05
LEVEL_TO_HZ = {0: 360, 1: 500, 2: 690, 3: 940, 4: 1280, 5: 1740, 6: 2360, 7: 3160}


class WAVEFORMATEX(ctypes.Structure):
    _fields_ = [
        ("wFormatTag", wintypes.WORD), ("nChannels", wintypes.WORD),
        ("nSamplesPerSec", wintypes.DWORD), ("nAvgBytesPerSec", wintypes.DWORD),
        ("nBlockAlign", wintypes.WORD), ("wBitsPerSample", wintypes.WORD),
        ("cbSize", wintypes.WORD),
    ]


class WAVEHDR(ctypes.Structure):
    _fields_ = [
        ("lpData", ctypes.c_void_p), ("dwBufferLength", wintypes.DWORD),
        ("dwBytesRecorded", wintypes.DWORD), ("dwUser", ctypes.c_size_t),
        ("dwFlags", wintypes.DWORD), ("dwLoops", wintypes.DWORD),
        ("lpNext", ctypes.c_void_p), ("reserved", ctypes.c_size_t),
    ]


class WAVEOUTCAPSW(ctypes.Structure):
    _fields_ = [
        ("wMid", wintypes.WORD), ("wPid", wintypes.WORD),
        ("vDriverVersion", wintypes.DWORD), ("szPname", wintypes.WCHAR * 32),
        ("dwFormats", wintypes.DWORD), ("wChannels", wintypes.WORD),
        ("wReserved1", wintypes.WORD), ("dwSupport", wintypes.DWORD),
    ]


class WAVEINCAPSW(ctypes.Structure):
    _fields_ = [
        ("wMid", wintypes.WORD), ("wPid", wintypes.WORD),
        ("vDriverVersion", wintypes.DWORD), ("szPname", wintypes.WCHAR * 32),
        ("dwFormats", wintypes.DWORD), ("wChannels", wintypes.WORD),
        ("wReserved1", wintypes.WORD),
    ]


WINMM = ctypes.WinDLL("winmm")
WAVE_MAPPER = 0xFFFFFFFF


def _device_names(kind: str):
    if kind == "input":
        count = int(WINMM.waveInGetNumDevs())
        caps_type = WAVEINCAPSW
        getter = WINMM.waveInGetDevCapsW
    else:
        count = int(WINMM.waveOutGetNumDevs())
        caps_type = WAVEOUTCAPSW
        getter = WINMM.waveOutGetDevCapsW
    names = []
    for index in range(count):
        caps = caps_type()
        result = getter(index, ctypes.byref(caps), ctypes.sizeof(caps))
        names.append(caps.szPname if result == 0 else f"unavailable-{index}")
    return names


def _check(result: int, operation: str):
    if result != 0:
        raise RuntimeError(f"{operation}_failed_mmresult_{result}")


def _tone_wav(frequency_hz: int) -> bytes:
    frames = int(SAMPLE_RATE * TONE_SECONDS)
    ramp = max(1, int(SAMPLE_RATE * 0.01))
    samples = array.array("h")
    for index in range(frames):
        envelope = min(1.0, index / ramp, (frames - 1 - index) / ramp)
        value = AMPLITUDE * envelope * math.sin(2 * math.pi * frequency_hz * index / SAMPLE_RATE)
        samples.append(int(32767 * value))
    return samples.tobytes()


def _play_tone(frequency_hz: int, output_device_id: int):
    raw = _tone_wav(frequency_hz)
    buffer = ctypes.create_string_buffer(raw)
    fmt = WAVEFORMATEX(1, 1, SAMPLE_RATE, SAMPLE_RATE * 2, 2, 16, 0)
    header = WAVEHDR(ctypes.cast(buffer, ctypes.c_void_p), len(raw), 0, 0, 0, 0, None, 0)
    handle = ctypes.c_void_p()
    _check(WINMM.waveOutOpen(ctypes.byref(handle), output_device_id, ctypes.byref(fmt), 0, 0, 0), "waveOutOpen")
    try:
        _check(WINMM.waveOutPrepareHeader(handle, ctypes.byref(header), ctypes.sizeof(header)), "waveOutPrepareHeader")
        _check(WINMM.waveOutWrite(handle, ctypes.byref(header), ctypes.sizeof(header)), "waveOutWrite")
        deadline = time.monotonic() + 2
        while not header.dwFlags & 0x00000001:
            if time.monotonic() > deadline:
                raise RuntimeError("waveOutWrite_timeout")
            time.sleep(0.005)
        WINMM.waveOutUnprepareHeader(handle, ctypes.byref(header), ctypes.sizeof(header))
    finally:
        WINMM.waveOutClose(handle)


def _capture_once(frequency_hz: int, output_device_id: int | None = None):
    total_seconds = BASELINE_SECONDS + TONE_SECONDS + TAIL_SECONDS
    frames = int(SAMPLE_RATE * total_seconds)
    byte_count = frames * 2
    buffer = ctypes.create_string_buffer(byte_count)
    fmt = WAVEFORMATEX(1, 1, SAMPLE_RATE, SAMPLE_RATE * 2, 2, 16, 0)
    header = WAVEHDR(ctypes.cast(buffer, ctypes.c_void_p), byte_count, 0, 0, 0, 0, None, 0)
    handle = ctypes.c_void_p()
    _check(WINMM.waveInOpen(ctypes.byref(handle), WAVE_MAPPER, ctypes.byref(fmt), 0, 0, 0), "waveInOpen")
    try:
        _check(WINMM.waveInPrepareHeader(handle, ctypes.byref(header), ctypes.sizeof(header)), "waveInPrepareHeader")
        _check(WINMM.waveInAddBuffer(handle, ctypes.byref(header), ctypes.sizeof(header)), "waveInAddBuffer")
        _check(WINMM.waveInStart(handle), "waveInStart")
        time.sleep(BASELINE_SECONDS)
        if output_device_id is None:
            output_device_id = int(os.environ.get("AKGM_V40_OUTPUT_DEVICE", "1" if WINMM.waveOutGetNumDevs() > 1 else str(WAVE_MAPPER)))
        _play_tone(frequency_hz, output_device_id)
        time.sleep(TAIL_SECONDS)
        WINMM.waveInStop(handle)
        WINMM.waveInReset(handle)
        raw = bytes(buffer.raw[: header.dwBytesRecorded])
        WINMM.waveInUnprepareHeader(handle, ctypes.byref(header), ctypes.sizeof(header))
    finally:
        WINMM.waveInClose(handle)
    samples = array.array("h")
    samples.frombytes(raw[: len(raw) - len(raw) % 2])
    peak_fraction = max((abs(value) for value in samples), default=0) / 32768
    rms_fraction = math.sqrt(sum(value * value for value in samples) / max(len(samples), 1)) / 32768
    baseline_end = min(len(samples), int(SAMPLE_RATE * BASELINE_SECONDS))
    tone_start = min(len(samples), baseline_end + int(SAMPLE_RATE * 0.015))
    tone_end = min(len(samples), baseline_end + int(SAMPLE_RATE * (TONE_SECONDS - 0.01)))

    def amplitude(segment, start_index):
        if not segment:
            return 0.0
        sine = cosine = 0.0
        for offset, value in enumerate(segment):
            phase = 2 * math.pi * frequency_hz * (start_index + offset) / SAMPLE_RATE
            sine += value * math.sin(phase)
            cosine += value * math.cos(phase)
        return 2 * math.hypot(sine, cosine) / (len(segment) * 32768)

    baseline = amplitude(samples[:baseline_end], 0)
    signal = amplitude(samples[tone_start:tone_end], tone_start)
    response = max(signal - baseline, 1e-9)
    return {
        "response": response,
        "baseline": baseline,
        "signal": signal,
        "snr": signal / max(baseline, 1e-9),
        "sample_count": len(samples),
        "peak_fraction": peak_fraction,
        "rms_fraction": rms_fraction,
        "raw_digest": hashlib.sha256(raw).hexdigest(),
    }


def _measure(level: int):
    trials = [_capture_once(LEVEL_TO_HZ[level]) for _ in range(3)]
    responses = [item["response"] for item in trials]
    median = statistics.median(responses)
    mad = statistics.median(abs(value - median) for value in responses)
    return {
        "anonymous_level": level,
        "response": median,
        "mad": mad,
        "trial_responses": responses,
        "median_snr": statistics.median(item["snr"] for item in trials),
        "sample_count": sum(item["sample_count"] for item in trials),
        "raw_digests": [item["raw_digest"] for item in trials],
        "measured_at_unix_ns": time.time_ns(),
    }


def _commitment(batch_id, order, seed_commitment):
    payload = {"batch_id": batch_id, "order": order, "seed_commitment": seed_commitment}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


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
                "apparatus": "anonymous_external_audio_path_v40",
                "available_anonymous_levels": list(LEVEL_TO_HZ),
                "input_device_count": int(WINMM.waveInGetNumDevs()),
                "output_device_count": int(WINMM.waveOutGetNumDevs()),
                "input_device_names_for_human_audit": _device_names("input"),
                "output_device_names_for_human_audit": _device_names("output"),
                "selected_output_device_id": int(os.environ.get("AKGM_V40_OUTPUT_DEVICE", "1" if WINMM.waveOutGetNumDevs() > 1 else str(WAVE_MAPPER))),
                "sample_rate": SAMPLE_RATE,
                "safe_peak_amplitude": AMPLITUDE,
                "human_quantity_names_exposed_to_learner": False,
                "measurement_exists_before_request": False,
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
            valid = expected == request["commitment"] and len(order) == len(set(order)) and all(value in LEVEL_TO_HZ and value not in measured for value in order)
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
                results = [_measure(level) for level in pending["order"]]
                measured.update(pending["order"])
                response = {
                    "ok": True,
                    "event_index": event_index,
                    "batch_id": pending["batch_id"],
                    "commitment": pending["commitment"],
                    "started_at_unix_ns": started,
                    "ended_at_unix_ns": time.time_ns(),
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
