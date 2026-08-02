"""Guarded end-to-end Auto Sub render smoke on an isolated DB/storage root."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resolution", choices=("source", "720p", "1080p", "4k"),
                        default="1080p")
    args = parser.parse_args()
    if not args.source.is_file():
        raise SystemExit("Source video does not exist.")

    work = Path(tempfile.mkdtemp(prefix="ltt_autosub_gpu_smoke_"))
    os.environ["LTT_DATABASE_URL"] = f"sqlite:///{(work / 'smoke.db').as_posix()}"
    os.environ["LTT_DATA_DIR"] = str(work / "data")
    from platform_core import credit, jobs
    from platform_core.db import Base, get_engine, get_session, reset_engine
    import platform_core.models  # noqa: F401
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.job_runner import JobContext, _quyet_toan_credit
    from platform_core.models import Job
    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung
    from platform_core import media
    from apps.autosubvideo.jobs import handle
    from apps.autosubvideo.schemas import StudioProjectV1

    reset_engine(); Base.metadata.create_all(get_engine())
    storage = LocalStorage(str(work / "storage")); set_storage(storage)
    try:
        db = next(get_session())
        user = tao_nguoi_dung(db, email="autosub-smoke@example.com",
                              password="Smoke-only-123", is_verified=True)
        credit.cap_tay(db, user.id, 100, by="autosub-gpu-smoke")
        source_key = f"autosubvideo/{user.id}/uploads/source{args.source.suffix.lower()}"
        with args.source.open("rb") as stream:
            storage.put(source_key, stream, "video/mp4")
        source_meta = media.probe(str(args.source))
        duration = float(source_meta.get("duration") or 0)
        payload = StudioProjectV1.model_validate({"schema_version": 1,
            "active_step": "render", "source": {"key": source_key,
            "filename": args.source.name, "duration_s": duration,
            "width": int(source_meta.get("width") or 0),
            "height": int(source_meta.get("height") or 0)},
            "tracks": [{"id":"source","kind":"source","language":"vi",
                "name":"Tiếng Việt","visible":True,"z_index":0,"style_id":"default",
                "cues":[{"id":"cue-1","start":0,"end":min(3.5,duration),
                    "text":"LTT Studios kiểm tra phụ đề tiếng Việt.","speaker":"","words":[]}]},
                {"id":"english","kind":"translation","language":"en",
                "name":"English","visible":True,"z_index":1,"style_id":"default",
                "cues":[{"id":"cue-2","start":0,"end":min(3.5,duration),
                    "text":"LTT Studios subtitle render test.","speaker":"","words":[]}]}],
            "speakers":{},"style":{"preset":"tiktok_bold","animation":"fade",
                "highlight_mode":"keyword","keyword_highlights":["LTT"]},
            "output":{"resolution":args.resolution,"format":"mp4","quality":"standard",
                "track_ids":["source","english"],"export_srt":True,"export_vtt":True,
                "export_json":True,"export_ass":True,"bundle_zip":True}
        }).model_dump(mode="json")
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False,
            separators=(",", ":"), allow_nan=False).encode("utf-8")
        params = {"operation":"render_project","owner_id":user.id,"project_id":"smoke",
            "project_revision":1,"project_snapshot":payload,
            "snapshot_sha256":hashlib.sha256(canonical).hexdigest(),
            "video_key":source_key,"duration_s":duration,"quality":"standard"}
        job = submit_with_credit(db,user_id=user.id,app_slug="autosubvideo",
            job_type="autosubvideo.render",params=params,
            dedupe_key=dedupe_key_for("autosubvideo.render",params),max_attempts=1)
        job_id=job.id; user_id=user.id
        claimed=jobs.claim(db,worker_id="autosub-smoke-worker")
        if claimed is None or claimed.id != job_id:
            raise RuntimeError("Isolated worker did not claim the render job.")
        db.commit(); db.close()

        started=time.perf_counter();result=handle(params,JobContext(job_id));elapsed=time.perf_counter()-started
        db=next(get_session());job=db.get(Job,job_id)
        jobs.complete(db,job,result);_quyet_toan_credit(db,job,result);balance=credit.so_du(db,user_id);db.commit();db.close()
        output_local=work/"output.mp4"
        with storage.open(result["video_key"]) as src,output_local.open("wb") as dst:
            shutil.copyfileobj(src,dst)
        output_meta=media.probe(str(output_local))
        expected_height={"720p":720,"1080p":1080,"4k":2160}.get(args.resolution,
            int(source_meta.get("height") or 0))
        passed=(int(output_meta.get("height") or 0)==expected_height and
            abs(float(output_meta.get("fps") or 0)-float(source_meta.get("fps") or 0))<0.05 and
            bool(output_meta.get("audio_codec"))==bool(source_meta.get("audio_codec")) and
            balance==100-int(result["credit_cost"]) and storage.exists(result["bundle_key"]))
        evidence={"passed":passed,"source_name":args.source.name,"source":source_meta,
            "output":output_meta,"elapsed_seconds":round(elapsed,3),"encoder":media.detect_gpu_encoder(),
            "credit_cost":result["credit_cost"],"balance_after":balance,
            "artifact_types":sorted(key for key in result if key.endswith("_key") or key.endswith("_keys"))}
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(evidence,ensure_ascii=True))
        return 0 if passed else 1
    finally:
        set_storage(None);reset_engine();shutil.rmtree(work,ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
