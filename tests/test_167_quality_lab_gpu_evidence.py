"""H31.3c2 — peak VRAM evidence must be sampled, UUID-bound and honest."""
from __future__ import annotations

import subprocess
import time


class FakeNvidiaSmi:
    def __init__(self, rows: list[tuple[int, int, int]]):
        self.rows = list(rows)
        self.index = 0

    def __call__(self, command, **_kwargs):
        assert "--query-gpu=uuid,memory.used,utilization.gpu,temperature.gpu" in command
        memory, utilization, temperature = self.rows[
            min(self.index, len(self.rows) - 1)]
        self.index += 1
        output = (
            "GPU-other, 900, 10, 50\n"
            f"GPU-target, {memory}, {utilization}, {temperature}\n"
        )
        return subprocess.CompletedProcess(command, 0, output, "")


def test_query_gpu_sample_selects_immutable_uuid_not_first_row():
    from apps.qualitylab.services.gpu_evidence import query_gpu_sample

    sample = query_gpu_sample("GPU-target", run=FakeNvidiaSmi([(4, 0, 38)]),
                              clock=lambda: 12.5)
    assert sample.timestamp_seconds == 12.5
    assert sample.memory_used_mb == 4
    assert sample.utilization_percent == 0


def test_sampler_reports_peak_delta_and_whole_device_scope():
    from apps.qualitylab.services.gpu_evidence import GpuEvidenceSampler

    fake = FakeNvidiaSmi([(4, 0, 38), (1200, 88, 55), (800, 25, 48)])
    sampler = GpuEvidenceSampler("GPU-target", interval_seconds=0.05, run=fake)
    sampler.start()
    time.sleep(0.12)
    evidence = sampler.stop()
    assert evidence["baseline_memory_used_mb"] == 4
    assert evidence["peak_memory_used_mb"] == 1200
    assert evidence["peak_delta_memory_mb"] == 1196
    assert evidence["peak_utilization_percent"] == 88
    assert evidence["scope"] == "whole_device_delta_from_idle_baseline"
    assert len(evidence["gpu_id_sha256"]) == 64
    assert "GPU-target" not in str(evidence)
    assert evidence["sample_count"] >= 3
    assert evidence["qualified"] is True
    assert "not per-process" in evidence["qualification_note"]


def test_smoke_tool_refuses_busy_gpu_by_default_and_hashes_source():
    from pathlib import Path

    source = Path("tools/upscale_gpu_smoke.py").read_text(encoding="utf-8")
    assert "--allow-busy-gpu" in source
    assert "Assigned GPU is not idle enough" in source
    assert '"source_artifact": {"sha256": _sha256(args.source)' in source
    assert '"gpu_memory_evidence": gpu_evidence' in source
    assert '"runtime_fingerprint": _runtime_fingerprint()' in source
