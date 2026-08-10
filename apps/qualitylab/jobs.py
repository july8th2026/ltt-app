"""Worker handler cho evaluation foundation."""
from __future__ import annotations

import hashlib
import platform
import shutil
import tempfile
import time
from pathlib import Path

from apps.qualitylab.contracts import build_report
from apps.qualitylab.registry import enabled_pack, pack_evaluators
from apps.qualitylab.services.media import inspect_media, kind_for_name
from apps.qualitylab.services.subtitle import inspect_subtitle
from apps.qualitylab.services.upscale import inspect_upscale_pair
from apps.qualitylab.services.upscale_video import inspect_upscale_video_pair
from platform_core.i18n import N_
from platform_core.storage import get_storage

MAX_TEXT_BYTES = 4 * 1024 * 1024


def _copy_from_storage(key: str, target: Path) -> str:
    digest = hashlib.sha256()
    with get_storage().open(key) as source, target.open("wb") as output:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
            output.write(chunk)
    return digest.hexdigest()


def _environment() -> dict[str, str]:
    """Không lưu hostname/user/path; chỉ fingerprint tái lập không định danh."""
    return {
        "device": "cpu",
        "os": platform.system(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "gpu_driver": "NOT_APPLICABLE",
    }


def _read_truth(params: dict) -> str:
    key = str(params.get("expected_text_key") or "").strip()
    if not key:
        # Chỉ giữ tương thích cho job test/legacy; UI không ghi transcript vào DB.
        return str(params.get("expected_text") or "")[:100_000]
    with get_storage().open(key) as stream:
        payload = stream.read(100_001)
    if len(payload) > 100_000:
        raise ValueError(N_("Transcript chuẩn vượt 100 KB."))
    return payload.decode("utf-8-sig")


def handle(params: dict, ctx=None) -> dict:
    pack_key = str(params.get("pack") or "")
    pack = enabled_pack(pack_key)
    source_key = str(params.get("source_key") or "").strip()
    source_name = Path(str(params.get("source_name") or source_key)).name
    if not source_key:
        raise ValueError(N_("Thiếu source artifact key."))
    source_kind = kind_for_name(source_name)
    if source_kind not in pack["accepts"]:
        raise ValueError(N_(f"Pack {pack_key} không nhận loại {source_kind}."))

    started = time.perf_counter()
    ephemeral = [str(value) for value in params.get("ephemeral_keys", []) if value]
    work = Path(tempfile.mkdtemp(prefix="ltt_qualitylab_"))
    try:
        if ctx is not None:
            ctx.stage("input_copy", N_("Đang đọc artifact để đánh giá."),
                      details={"pack": pack_key, "source_kind": source_kind})
            ctx.progress(10, N_("Đang đọc artifact"))
        local = work / (source_name or f"source{Path(source_key).suffix}")
        source_sha256 = _copy_from_storage(source_key, local)
        if ctx is not None:
            ctx.progress(35, N_("Đang kiểm tra contract"))

        extra_artifacts: dict[str, object] = {}
        if pack_key in {"upscale_paired_diagnostic", "upscale_video_diagnostic"}:
            reference_key = str(params.get("reference_key") or "").strip()
            if not reference_key:
                raise ValueError(N_("Pack paired thiếu ảnh HR reference."))
            reference = work / ("reference" + (Path(reference_key).suffix or ".bin"))
            reference_sha256 = _copy_from_storage(reference_key, reference)
            low_key = str(params.get("low_input_key") or "").strip()
            low_path = None
            low_sha256 = ""
            if low_key:
                low_path = work / ("low-input" + (Path(low_key).suffix or ".bin"))
                low_sha256 = _copy_from_storage(low_key, low_path)
            if pack_key == "upscale_video_diagnostic":
                dimensions, summary = inspect_upscale_video_pair(
                    local, reference, low_path, work,
                    dict(params.get("source_job_performance") or {}))
            else:
                dimensions, summary = inspect_upscale_pair(local, reference, low_path)
            extra_artifacts = {
                "reference_sha256": reference_sha256,
                "low_input_sha256": low_sha256 or None,
            }
        elif source_kind == "subtitle":
            if local.stat().st_size > MAX_TEXT_BYTES:
                raise ValueError(N_("File subtitle vượt 4 MB."))
            raw = local.read_text(encoding="utf-8-sig")
            dimensions, summary = inspect_subtitle(
                raw, _read_truth(params))
        else:
            source_kind, dimensions, summary = inspect_media(
                local, dict(params.get("expectations") or {}))

        if ctx is not None:
            ctx.progress(85, N_("Đang tổng hợp bằng chứng"))
        report = build_report(
            evaluation_id=getattr(ctx, "job_id", "adhoc"), pack=pack_key,
            source_kind=source_kind, evaluator_version="qualitylab-foundation-1.0.0",
            dimensions=dimensions,
            runtime={"seconds": round(time.perf_counter() - started, 4),
                     "source_bytes": local.stat().st_size,
                     "summary": summary},
            source_artifact={"sha256": source_sha256,
                             "bytes": local.stat().st_size,
                             "kind": source_kind, **extra_artifacts},
            evaluators=pack_evaluators(pack_key),
            environment=_environment(),
        )
        if ctx is not None:
            ctx.stage("evaluation_complete", N_("Đã tạo report chất lượng."),
                      details={"pack": pack_key,
                               "verdict": report["overall_verdict"]})
            ctx.progress(100, N_("Đã đánh giá xong"))
        return {"report": report, "overall_verdict": report["overall_verdict"],
                "pack": pack_key, "source_kind": source_kind}
    finally:
        shutil.rmtree(work, ignore_errors=True)
        storage = get_storage()
        for key in ephemeral:
            try:
                storage.delete(key)
            except Exception:
                # Cleanup failure phải làm job fail để operator thấy và xử lý,
                # không lặng lẽ giữ raw upload ngoài retention contract.
                raise RuntimeError(N_("Không xóa được input tạm của Quality Lab."))
