"""Bounded auxiliary AI workflows for Auto Sub Studio.

No function logs source transcript or credentials. Diarization runs in the
isolated WhisperX sidecar; translation uses the shared Gemini API-key pool.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

_TRANSLATE_MODEL = "gemini-2.5-flash"
_MAX_CUES = 10_000
_CHUNK_CUES = 60
_CHUNK_CHARS = 12_000


class AuxiliaryAIError(RuntimeError):
    pass


def diarization_available() -> bool:
    from apps.autosubvideo.transcription import whisperx_available
    return whisperx_available() and bool(os.environ.get("LTT_HF_TOKEN", "").strip())


def gemini_available(db) -> bool:
    if os.environ.get("GEMINI_API_KEY", "").strip():
        return True
    try:
        from platform_core.models import APIKEY_CAT_CHAT, ApiKey
        rows = db.query(ApiKey).filter_by(provider="gemini", enabled=True).all()
        return any(not row.categories or APIKEY_CAT_CHAT in row.categories for row in rows)
    except Exception:
        return False


def diarize_file(media_path: str, *, min_speakers: int = 0, max_speakers: int = 0,
                  on_progress=None, is_cancelled=None,
                  gpu_uuid: str = "") -> list[dict]:
    """Phan vai nguoi noi. `gpu_uuid` GHIM tien trinh con vao mot card.

    🔴 **Truoc tham so nay, `pyannote_runner.py:20` tu chon card**:
       `if torch.cuda.is_available(): pipeline.to(torch.device("cuda"))` — tuc
       no lay card dau tien torch thay, bat ke `platform_core.gpu_lease` da cap
       card nao cho ai. Hai job song song thi hoac dam nhau tren mot card, hoac
       mot card nam khong trong khi card kia OOM.

    ⭐ Sua bang cach **dung lai** dung khuon cua `transcription._env_ghim_gpu`
       (-> `platform_core.gpu.env_for`), khong dung mot co che dieu phoi thu
       hai: ta chi TON TRONG cai lease da co, khong tu quyet dinh gi.

    ⚠️ Mac dinh `""` = giu nguyen hanh vi cu, nen moi nguoi goi hien tai cua
       `autosubvideo` chay khong doi mot dong.
    """
    if not diarization_available():
        raise AuxiliaryAIError("Pyannote chưa được cấu hình (thiếu LTT_HF_TOKEN/sidecar).")
    from apps.autosubvideo.transcription import _sidecar_python
    output = tempfile.NamedTemporaryFile(delete=False, suffix=".json"); output.close()
    args = [_sidecar_python(), str(Path(__file__).with_name("pyannote_runner.py")),
            "--input", media_path, "--output", output.name]
    if min_speakers: args += ["--min-speakers", str(min_speakers)]
    if max_speakers: args += ["--max-speakers", str(max_speakers)]
    try:
        if on_progress: on_progress(10, "Pyannote đang phân vai")
        from apps.autosubvideo.transcription import _env_ghim_gpu
        proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
            env=_env_ghim_gpu(gpu_uuid),
            creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0))
        while proc.poll() is None:
            if is_cancelled and is_cancelled():
                proc.terminate(); raise AuxiliaryAIError("Tác vụ đã bị hủy.")
            try: proc.wait(timeout=.5)
            except subprocess.TimeoutExpired: continue
        if proc.returncode:
            message=(proc.stderr.read() if proc.stderr else "")[-1000:]
            raise AuxiliaryAIError(f"Pyannote lỗi: {message or 'không rõ nguyên nhân'}")
        with open(output.name,encoding="utf-8") as handle: payload=json.load(handle)
        turns=payload.get("turns") or []
        clean=[]
        for item in turns:
            start=float(item.get("start",0));end=float(item.get("end",0));speaker=str(item.get("speaker", ""))[:80]
            if start>=0 and end>start and speaker: clean.append({"start":start,"end":end,"speaker":speaker})
        if not clean: raise AuxiliaryAIError("Pyannote không tìm thấy lượt nói.")
        if on_progress: on_progress(88,"đang gán speaker vào cue")
        return clean
    finally:
        try: os.unlink(output.name)
        except OSError: pass


def assign_speakers(cues: list[dict], turns: list[dict]) -> tuple[list[dict], dict[str,str]]:
    """Assign each cue to the turn with greatest temporal overlap."""
    updated=[]; speakers={}
    for cue in cues:
        item=dict(cue); start=float(item.get("start",0)); end=float(item.get("end",0))
        best=""; best_overlap=0.0
        for turn in turns:
            overlap=max(0.0,min(end,float(turn["end"]))-max(start,float(turn["start"])))
            if overlap>best_overlap: best_overlap=overlap;best=str(turn["speaker"])
        if best:
            item["speaker"]=best; speakers.setdefault(best, f"Người nói {len(speakers)+1}")
        updated.append(item)
    return updated,speakers


def _chunks(cues:list[dict]):
    chunk=[];chars=0
    for cue in cues:
        size=len(str(cue.get("text","")))
        if chunk and (len(chunk)>=_CHUNK_CUES or chars+size>_CHUNK_CHARS):
            yield chunk;chunk=[];chars=0
        chunk.append({"id":str(cue.get("id","")),"text":str(cue.get("text",""))});chars+=size
    if chunk: yield chunk


def _gemini_chunk(db, items:list[dict], target_language:str) -> list[dict]:
    import httpx
    from platform_core import api_keys, api_pool, providers as _prov
    from platform_core.models import APIKEY_CAT_CHAT
    _prov.chan_neu_da_ngung("gemini")       # ⛔ fail-closed (AI CLEAN REBUILD V2)
    key=None; credential=""
    try:
        key=api_pool.chon_key(db,category=APIKEY_CAT_CHAT,model=_TRANSLATE_MODEL,
                              thu_tu_provider=["gemini"])
        credential=api_keys.lay_credential(db,key)
    except Exception:
        credential=os.environ.get("GEMINI_API_KEY","").strip()
    if not credential: raise AuxiliaryAIError("Chưa có API key Gemini cho bản dịch.")
    schema={"type":"ARRAY","items":{"type":"OBJECT","properties":{
        "id":{"type":"STRING"},"text":{"type":"STRING"}},"required":["id","text"]}}
    prompt=("Translate each subtitle to " + target_language +
            ". Preserve ids, meaning, tone, line breaks and placeholders. "
            "Return exactly one item per input, in the same order. Input JSON:\n"+
            json.dumps(items,ensure_ascii=False,separators=(",",":")))
    try:
        response=httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{_TRANSLATE_MODEL}:generateContent",
            headers={"x-goog-api-key":credential},json={"contents":[{"parts":[{"text":prompt}]}],
            "generationConfig":{"responseMimeType":"application/json","responseSchema":schema,
                                "temperature":0.1}},timeout=90)
        if response.status_code!=200:
            if key is not None: api_pool.danh_dau_loi(db,key,http_status=response.status_code)
            raise AuxiliaryAIError(f"Gemini translation HTTP {response.status_code}.")
        parts=(response.json().get("candidates") or [{}])[0].get("content",{}).get("parts",[])
        text=next((part.get("text") for part in parts if part.get("text")),"")
        result=json.loads(text)
        if key is not None:
            usage=response.json().get("usageMetadata") or {}
            api_pool.danh_dau_thanh_cong(db,key,tokens=int(usage.get("totalTokenCount",0) or 0))
        return result
    except (httpx.HTTPError,json.JSONDecodeError) as exc:
        if key is not None: api_pool.danh_dau_loi(db,key,message=type(exc).__name__)
        raise AuxiliaryAIError(f"Gemini translation lỗi {type(exc).__name__}.") from None
    finally: credential=""


def translate_cues(db, cues:list[dict], target_language:str, *, call=None,
                   on_progress=None, is_cancelled=None) -> list[dict]:
    if not cues or len(cues)>_MAX_CUES: raise AuxiliaryAIError("Số cue dịch không hợp lệ.")
    target=(target_language or "").strip()[:64]
    if not target: raise AuxiliaryAIError("Thiếu ngôn ngữ đích.")
    translated={}; chunks=list(_chunks(cues)); invoke=call or (lambda batch:_gemini_chunk(db,batch,target))
    for index,batch in enumerate(chunks):
        if is_cancelled and is_cancelled(): raise AuxiliaryAIError("Tác vụ đã bị hủy.")
        result=invoke(batch)
        expected=[item["id"] for item in batch]
        if not isinstance(result,list) or [str(item.get("id","")) for item in result]!=expected:
            raise AuxiliaryAIError("Gemini trả thiếu/thừa hoặc sai thứ tự cue.")
        for item in result:
            text=str(item.get("text","")).strip()
            if not text: raise AuxiliaryAIError("Gemini trả cue rỗng.")
            translated[str(item["id"])]=text[:4000]
        if on_progress:on_progress(10+int(80*(index+1)/len(chunks)),"đang dịch transcript")
    return [{**cue,"text":translated[str(cue["id"])],"words":[]} for cue in cues]
