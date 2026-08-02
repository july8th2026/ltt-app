"""Deterministic large-project benchmark for Studio validation/export."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))


def main()->int:
    parser=argparse.ArgumentParser();parser.add_argument("--cues",type=int,default=3000)
    parser.add_argument("--output",type=Path,required=True);args=parser.parse_args()
    if args.cues<1 or args.cues>10000:raise SystemExit("cues must be 1..10000")
    from apps.autosubvideo.project_render import build_project_artifacts
    from apps.autosubvideo.schemas import StudioProjectV1
    cues=[{"id":f"cue-{i:05d}","start":i*1.05,"end":i*1.05+1,
           "text":f"Phụ đề kiểm thử tải số {i}","speaker":"","words":[]}
          for i in range(args.cues)]
    raw={"schema_version":1,"active_step":"render","source":{"key":"autosubvideo/u/input.mp4",
        "filename":"long.mp4","duration_s":args.cues*1.05,"width":1920,"height":1080},
        "tracks":[{"id":"source","kind":"source","language":"vi","name":"Vietnamese",
            "visible":True,"z_index":0,"style_id":"default","cues":cues}],"speakers":{},
        "style":{"preset":"default"},"output":{"resolution":"1080p","format":"mp4",
            "quality":"standard","track_ids":["source"],"export_srt":True,"export_vtt":True,
            "export_json":True,"export_ass":True,"bundle_zip":True}}
    work=Path(tempfile.mkdtemp(prefix="ltt_autosub_load_"));tracemalloc.start();started=time.perf_counter()
    try:
        payload=StudioProjectV1.model_validate(raw).model_dump(mode="json")
        artifacts=build_project_artifacts(payload,str(work),width=1920,height=1080)
        elapsed=time.perf_counter()-started;_current,peak=tracemalloc.get_traced_memory()
        sizes={Path(path).suffix:Path(path).stat().st_size for path in [artifacts["ass_path"],
            *artifacts["srt_paths"].values(),*artifacts["vtt_paths"].values(),
            *artifacts["json_paths"].values(),artifacts["bundle_path"]]}
        passed=elapsed<5 and peak<256*1024*1024 and all(value>0 for value in sizes.values())
        evidence={"passed":passed,"cue_count":args.cues,"duration_seconds":args.cues*1.05,
            "elapsed_seconds":round(elapsed,3),"peak_memory_mb":round(peak/1024/1024,2),
            "artifact_sizes":sizes}
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(evidence,ensure_ascii=True));return 0 if passed else 1
    finally:
        tracemalloc.stop();shutil.rmtree(work,ignore_errors=True)


if __name__=="__main__":raise SystemExit(main())
