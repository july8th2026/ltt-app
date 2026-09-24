"""Bounded auxiliary AI workflows for Auto Sub Studio.

No function logs source transcript or credentials. Diarization runs in the
isolated WhisperX sidecar; translation runs on **LTT_LLM** (model nhà).

🔴 DI TRÚ 08/09/2026 — AI CLEAN REBUILD V2 pha 05.6.

## ⚠️ BẢO ĐẢM BỊ HẠ CẤP, và ở đây nó MẠNH hơn hai app trước

Bản cũ gửi `responseSchema` — Gemini cưỡng chế **đúng hình dạng**
`[{id: str, text: str}]` ở tầng giao thức, không chỉ "là JSON".

⭐ Nhưng phần lớn bảo đảm ấy **đã có bản sao ở hạ nguồn**: `translate_cues`
   vốn kiểm `isinstance(result, list)`, đối chiếu **đúng thứ tự id**, chặn
   `text` rỗng và cắt 4000 ký tự. Nên mất `responseSchema` không mở ra một lỗ
   lớn — nó chỉ để hở **một** kẽ: nếu model trả `["a", "b"]` thì `item.get(...)`
   ném `AttributeError`, tức một lỗi **không có tên** thay vì `AuxiliaryAIError`.

⇒ Kẽ đó được bịt ngay tại chỗ phân tích (xem `_dich_mot_lo`), chứ không để hạ
  nguồn đoán. **Gỡ một bảo đảm ở tầng giao thức thì phải thêm đúng phép kiểm mà
  nó đang làm** — nếu không, ta đổi một lỗi rõ ràng lấy một lỗi mơ hồ.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import uuid as _uuid
from pathlib import Path

from platform_core.i18n import _ as _t
from platform_core.llm import canonical as _C

_MAX_CUES = 10_000
_CHUNK_CUES = 60
_CHUNK_CHARS = 12_000


class AuxiliaryAIError(RuntimeError):
    pass


def diarization_available() -> bool:
    from apps.autosubvideo.transcription import whisperx_available
    return whisperx_available() and bool(os.environ.get("LTT_HF_TOKEN", "").strip())


def dich_kha_dung(db) -> bool:
    """Có dịch được không — cờ năng lực cho giao diện.

    🔴 Đổi tên từ `gemini_available` ở pha 05.6. Tên cũ **khai một nhà cung cấp
       cụ thể**, nên nó buộc mọi người đọc phải biết app này chạy trên gì. Câu
       hỏi thật của giao diện là *"dịch được không"*, không phải *"có khoá
       Gemini không"*.

    ⛔ Không còn đọc `GEMINI_API_KEY`. Một biến môi trường ở tầng app là đường
       vòng qua kho khoá — đúng thứ pha 05 gỡ.

    ⛔ **Khong bat ngoai le o day.** Co nay chi co hai gia tri, nen no khong
       dien dat duoc "chua biet". Bat `Exception` roi tra `False` nghia la mot
       CSDL hong lam tinh nang dich BIEN MAT khoi giao dien — khach thay mot
       tinh nang da tra tien tu nhien khong con, `routes.py` tra "chua bat
       dich", va khong mot dong nao noi ly do that. Mot loi 500 o day thi ro:
       no chi vao CSDL, tuc vao dung cho phai sua.
    """
    from platform_core.models import APIKEY_CAT_CHAT, ApiKey

    rows = db.query(ApiKey).filter_by(
        provider=_C.THU_TU_PROVIDER[0], enabled=True).all()
    return any(not row.categories or APIKEY_CAT_CHAT in row.categories
               for row in rows)


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


def _dich_mot_lo(db, items: list[dict], target_language: str) -> list[dict]:
    """Dịch một lô cue qua LTT_LLM. Ném `AuxiliaryAIError` khi không dùng được.

    🔴 Giành **suất admission** trước khi chạm máy B — máy B chỉ có một suất
       đồng thời, và một đường quên bước này làm chính cơ chế đếm suất sai.
    """
    from platform_core.llm import admission, dieu_phoi
    from platform_core.models import APIKEY_CAT_CHAT

    loi_nhac = ("Translate each subtitle to " + target_language +
                ". Preserve ids, meaning, tone, line breaks and placeholders. "
                "Return exactly one item per input, in the same order.\n"
                "Return ONLY a JSON array of objects with keys \"id\" and "
                "\"text\". No markdown fence, no commentary.\nInput JSON:\n" +
                json.dumps(items, ensure_ascii=False, separators=(",", ":")))

    # D09: model cho việc nội bộ đọc từ **bản khai của app này**, không phải
    # `MODEL_MAC_DINH` (tên đó trả lời câu "khách không nói model thì dùng gì").
    model = _C.model_noi_bo_cua("autosubvideo")
    suc = _C.tai_nguyen_nha(model)
    ve = None
    try:
        ve = admission.acquire(
            db, resource=suc.resource, slots=suc.slots, user_id="he-thong:autosubvideo",
            mode="sync", holder_id="asv-dich:" + _uuid.uuid4().hex[:12])
        if ve is None:
            raise AuxiliaryAIError(_t("Model đang bận, thử lại sau ít phút."))
        try:
            kq = dieu_phoi.goi(
                db,
                messages=[{"role": "user", "content": loi_nhac}],
                category=APIKEY_CAT_CHAT,
                thu_tu_provider=_C.THU_TU_PROVIDER,
                model_theo_provider=_C.ban_do_model(model),
                temperature=0.1,
                timeout_s=90.0,
            )
        except dieu_phoi.KhongCoProviderNao:
            # `dieu_phoi` đã đánh dấu lỗi lên khoá cho đúng trường hợp rồi —
            # KHÔNG đánh dấu lại ở đây (đó là bản sao thứ hai của telemetry).
            raise AuxiliaryAIError(_t("Dịch vụ dịch đang bận, thử lại sau.")) from None
    finally:
        if ve is not None:
            admission.release_by_id(ve.id)

    van = (kq.noi_dung or "").strip()
    if van.startswith("```"):
        van = van.split("\n", 1)[-1].rsplit("```", 1)[0]
    van = van.strip().removeprefix("json").strip()
    try:
        ket_qua = json.loads(van)
    except json.JSONDecodeError:
        raise AuxiliaryAIError(_t("Bản dịch trả về không phải JSON hợp lệ.")) from None

    # 🔴 PHÉP KIỂM THAY CHO `responseSchema` ĐÃ MẤT.
    #
    #    Hạ nguồn (`translate_cues`) đã đối chiếu id, thứ tự, và chặn text rỗng —
    #    nhưng nó gọi `item.get(...)`, tức nó **giả định phần tử là dict**. Trước
    #    đây `responseSchema` bảo đảm điều đó ở tầng giao thức; nay không còn ai
    #    bảo đảm, nên nếu model trả `["a","b"]` thì hạ nguồn ném `AttributeError`
    #    — một lỗi KHÔNG CÓ TÊN, và nó sẽ đi lên như một sự cố hạ tầng.
    #
    # ⇒ Gỡ một bảo đảm ở tầng giao thức thì phải **thêm đúng phép kiểm mà nó
    #   đang làm**. Đây chính là phép kiểm ấy.
    if not isinstance(ket_qua, list) or not all(
            isinstance(m, dict) for m in ket_qua):
        raise AuxiliaryAIError(_t("Bản dịch trả về sai cấu trúc (cần mảng object)."))
    return ket_qua


def translate_cues(db, cues:list[dict], target_language:str, *, call=None,
                   on_progress=None, is_cancelled=None) -> list[dict]:
    if not cues or len(cues)>_MAX_CUES: raise AuxiliaryAIError("Số cue dịch không hợp lệ.")
    target=(target_language or "").strip()[:64]
    if not target: raise AuxiliaryAIError("Thiếu ngôn ngữ đích.")
    translated={}; chunks=list(_chunks(cues)); invoke=call or (lambda batch:_dich_mot_lo(db,batch,target))
    for index,batch in enumerate(chunks):
        if is_cancelled and is_cancelled(): raise AuxiliaryAIError("Tác vụ đã bị hủy.")
        result=invoke(batch)
        expected=[item["id"] for item in batch]
        if not isinstance(result,list) or [str(item.get("id","")) for item in result]!=expected:
            raise AuxiliaryAIError(_t("Bản dịch thiếu/thừa hoặc sai thứ tự cue."))
        for item in result:
            text=str(item.get("text","")).strip()
            if not text: raise AuxiliaryAIError(_t("Bản dịch có cue rỗng."))
            translated[str(item["id"])]=text[:4000]
        if on_progress:on_progress(10+int(80*(index+1)/len(chunks)),"đang dịch transcript")
    return [{**cue,"text":translated[str(cue["id"])],"words":[]} for cue in cues]
