"""Aggregate GPU evidence for isolated benchmarks; never a production profiler."""
from __future__ import annotations

import hashlib
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class GpuSample:
    timestamp_seconds: float
    memory_used_mb: int
    utilization_percent: int
    temperature_c: int


def query_gpu_sample(gpu_uuid: str, *, run=subprocess.run,
                     clock=time.monotonic) -> GpuSample:
    """Read one whole-device sample and select by immutable UUID, never index."""
    result = run([
        "nvidia-smi",
        "--query-gpu=uuid,memory.used,utilization.gpu,temperature.gpu",
        "--format=csv,noheader,nounits",
    ], capture_output=True, text=True, timeout=10, check=False)
    if result.returncode != 0:
        raise RuntimeError("nvidia-smi query failed")
    for raw_line in result.stdout.splitlines():
        parts = [part.strip() for part in raw_line.split(",")]
        if len(parts) != 4 or parts[0] != gpu_uuid:
            continue
        try:
            return GpuSample(clock(), int(float(parts[1])), int(float(parts[2])),
                             int(float(parts[3])))
        except ValueError as exc:
            raise RuntimeError("nvidia-smi returned non-numeric metrics") from exc
    raise RuntimeError("assigned GPU UUID not found")


class GpuEvidenceSampler:
    """Sample aggregate GPU state in a background thread during one benchmark.

    `memory.used` is the whole-device allocation reported by nvidia-smi. The
    delta from an idle baseline is useful only when the benchmark owns an idle
    GPU; the caller must enforce that precondition and preserve this scope in
    the evidence instead of calling it per-process memory.
    """

    def __init__(self, gpu_uuid: str, *, interval_seconds: float = 0.2,
                 run=subprocess.run, clock=time.monotonic):
        if not gpu_uuid:
            raise ValueError("gpu_uuid is required")
        if not 0.05 <= interval_seconds <= 5.0:
            raise ValueError("interval_seconds must be between 0.05 and 5")
        self.gpu_uuid = gpu_uuid
        self.interval_seconds = float(interval_seconds)
        self._run = run
        self._clock = clock
        self._samples: list[GpuSample] = []
        self._errors = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def baseline(self) -> GpuSample:
        if not self._samples:
            raise RuntimeError("sampler has not started")
        return self._samples[0]

    def _capture(self) -> None:
        try:
            sample = query_gpu_sample(self.gpu_uuid, run=self._run,
                                      clock=self._clock)
        except (OSError, subprocess.SubprocessError, RuntimeError):
            self._errors += 1
            return
        self._samples.append(sample)

    def start(self) -> "GpuEvidenceSampler":
        if self._thread is not None:
            raise RuntimeError("sampler already started")
        self._capture()
        if not self._samples:
            raise RuntimeError("cannot capture GPU baseline")
        self._thread = threading.Thread(target=self._loop,
                                        name="qualitylab-gpu-sampler", daemon=True)
        self._thread.start()
        return self

    def _loop(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self._capture()

    def stop(self) -> dict:
        if self._thread is None:
            raise RuntimeError("sampler has not started")
        self._stop.set()
        self._thread.join(timeout=max(2.0, self.interval_seconds * 3))
        self._capture()
        self._thread = None
        return self.summary()

    def summary(self) -> dict:
        if not self._samples:
            raise RuntimeError("sampler has no evidence")
        baseline = self._samples[0]
        peak_memory = max(item.memory_used_mb for item in self._samples)
        duration = max(0.0, self._samples[-1].timestamp_seconds -
                       baseline.timestamp_seconds)
        return {
            "schema_version": 1,
            "gpu_id_sha256": hashlib.sha256(
                self.gpu_uuid.encode("utf-8")).hexdigest(),
            "scope": "whole_device_delta_from_idle_baseline",
            "sampling_interval_ms": round(self.interval_seconds * 1000),
            "sample_count": len(self._samples),
            "sampling_errors": self._errors,
            "duration_seconds": round(duration, 3),
            "baseline_memory_used_mb": baseline.memory_used_mb,
            "peak_memory_used_mb": peak_memory,
            "peak_delta_memory_mb": max(0, peak_memory - baseline.memory_used_mb),
            "baseline_utilization_percent": baseline.utilization_percent,
            "peak_utilization_percent": max(
                item.utilization_percent for item in self._samples),
            "peak_temperature_c": max(item.temperature_c for item in self._samples),
            "qualified": self._errors == 0 and len(self._samples) >= 2,
            "qualification_note": (
                "Valid only for an otherwise idle, exclusively assigned GPU; "
                "memory is whole-device allocation, not per-process memory."
            ),
        }

    def __enter__(self) -> "GpuEvidenceSampler":
        return self.start()

    def __exit__(self, _exc_type, _exc, _traceback) -> None:
        self.stop()
