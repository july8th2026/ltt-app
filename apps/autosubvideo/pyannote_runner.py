"""Small isolated CLI executed by the WhisperX/Pyannote sidecar Python."""
from __future__ import annotations

import argparse
import json
import os


def main() -> int:
    parser=argparse.ArgumentParser();parser.add_argument("--input",required=True)
    parser.add_argument("--output",required=True);parser.add_argument("--min-speakers",type=int,default=0)
    parser.add_argument("--max-speakers",type=int,default=0);args=parser.parse_args()
    token=os.environ.get("LTT_HF_TOKEN","").strip()
    if not token: raise RuntimeError("LTT_HF_TOKEN is not configured")
    os.environ.setdefault("PYANNOTE_METRICS_ENABLED", "0")
    import torch
    import whisperx
    from pyannote.audio import Pipeline
    pipeline=Pipeline.from_pretrained("pyannote/speaker-diarization-community-1",token=token)
    if torch.cuda.is_available():pipeline.to(torch.device("cuda"))
    kwargs={}
    if args.min_speakers:kwargs["min_speakers"]=args.min_speakers
    if args.max_speakers:kwargs["max_speakers"]=args.max_speakers
    # Preload with WhisperX/FFmpeg. This deliberately bypasses TorchCodec: the
    # isolated Torch 2.8 CUDA stack can diarize correctly even when TorchCodec's
    # optional DLL build does not match the host FFmpeg runtime.
    audio=whisperx.load_audio(args.input)
    output=pipeline({"waveform":torch.from_numpy(audio).unsqueeze(0),
                     "sample_rate":16000},**kwargs)
    annotation=getattr(output,"exclusive_speaker_diarization",None) or output.speaker_diarization
    turns=[{"start":float(turn.start),"end":float(turn.end),"speaker":str(speaker)}
           for turn,speaker in annotation]
    with open(args.output,"w",encoding="utf-8") as handle:
        json.dump({"schema_version":1,"turns":turns},handle,ensure_ascii=False,allow_nan=False)
    return 0


if __name__=="__main__":raise SystemExit(main())
