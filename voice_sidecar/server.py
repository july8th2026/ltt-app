"""
server.py — cổng giọng nói của LTT VOICE. Chỉ nghe `127.0.0.1`.

Khuôn lấy từ `codex_sidecar/server.py` đã chạy thật trên máy A: loopback + bearer
token sinh lúc cài, chỉ web/worker cùng máy gọi tới.

Bốn chốt của khuôn tầng 1 (`docs/KHUON_BAN_MODEL_NHA.md`) nằm ở đây:

  1.3  bận ⇒ **429**, không bao giờ 5xx   (D-005: máy A coi 5xx là *hỏng*)
  1.4  giới hạn đồng thời khớp năng lực thật của engine (một GPU = một việc)
  1.6  chốt "GPU hay CPU" đọc từ **số đo** (`torch.cuda.memory_allocated`)
  1.7  `/live` **không cần khoá** · `/health` **cần khoá**

⛔ KHÔNG BAO GIỜ đưa cổng này ra Cloudflare hay ra LAN. Nó không có xác thực nào
   ngoài một bearer token dùng chung, và nó nhận đường dẫn tệp cục bộ.
"""
from __future__ import annotations

import io
import logging
import os
import wave

import numpy as np
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel

from . import engine as eng
from . import ngan_sach, tham_so

log = logging.getLogger("ltt.voice.server")


# ── WAV ──────────────────────────────────────────────────────────────────────
def _pcm16(wav_f32: np.ndarray) -> bytes:
    """float32 [-1,1] -> PCM16. Kẹp trước khi ép kiểu, không sau.

    Ép trước rồi kẹp là cách kinh điển để một mẫu vượt biên quấn vòng thành một
    tiếng *tách* rất to — thứ chỉ nghe thấy chứ không thấy trong test.
    """
    return (np.clip(np.asarray(wav_f32, dtype=np.float32), -1.0, 1.0)
            * 32767.0).astype(np.int16).tobytes()


def _wav_bytes(wav_f32: np.ndarray, sr: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(_pcm16(wav_f32))
    return buf.getvalue()


def _wav_header_mo(sr: int) -> bytes:
    """Header WAV với `nframes` rất lớn, cho đường phát dần.

    Mẹo lấy từ `apps/web_stream.py` của upstream (tham chiếu giao thức, không
    chép mã): trình duyệt bắt đầu phát ngay khi byte đầu tới thay vì chờ biết độ
    dài — mà độ dài thì chưa tồn tại lúc bắt đầu sinh.
    """
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.setnframes(1_000_000_000)
    return buf.getvalue()


# ── thân yêu cầu ─────────────────────────────────────────────────────────────
class ThanNoi(BaseModel):
    text: str
    ref_b64: str | None = None
    preset: str | None = None


class ThanLo(BaseModel):
    texts: list[str]
    ref_b64: str | None = None
    preset: str | None = None


class ThanGhiDanh(BaseModel):
    #: Đường dẫn tệp **cục bộ**. Cùng máy nên không cần đẩy byte qua HTTP; worker
    #: đã có tệp trong thư mục tạm của nó.
    duong_wav: str
    denoise: bool = True


def create_app(cong: eng.CongGiong | None = None) -> FastAPI:
    app = FastAPI(title="LTT Voice sidecar", docs_url=None, redoc_url=None)
    _cong = cong

    def lay() -> eng.CongGiong:
        return _cong if _cong is not None else eng.lay_cong()

    token = (os.environ.get("LTT_VOICE_SIDECAR_TOKEN") or "").strip()

    def auth(authorization: str = Header(default="")) -> None:
        # Fail-closed: chưa đặt token thì KHÔNG mở toang, mà từ chối hết. Một cổng
        # không token trên máy đang phục vụ khách là một cổng ai cũng gọi được.
        if not token:
            raise HTTPException(status_code=503,
                                detail="LTT_VOICE_SIDECAR_TOKEN chua duoc dat")
        if authorization.strip() != f"Bearer {token}":
            raise HTTPException(status_code=401, detail="unauthorized")

    # ── 1.7: /live không khoá ────────────────────────────────────────────────
    @app.get("/live")
    def live() -> dict:
        """Sống hay chết. **Không** chạm engine, **không** cần khoá.

        Một phép thăm dò sống/chết không nên phải mang bí mật, và nó không được
        đánh thức việc nạp model — nếu không thì chính phép thăm dò lại là thứ
        làm chậm máy.
        """
        return {"ok": True, "dich_vu": "ltt-voice"}

    @app.get("/health")
    def health(_: None = Depends(auth)) -> dict:
        return {"ok": True, **lay().nang_luc()}

    @app.get("/v1/capabilities")
    def capabilities(_: None = Depends(auth)) -> dict:
        c = lay()
        c.nap()
        return c.nang_luc()

    # ── 1.3: bận ⇒ 429, không bao giờ 5xx ────────────────────────────────────
    @app.exception_handler(eng.DangBan)
    def _ban(request: Request, exc: eng.DangBan):
        return JSONResponse(
            status_code=429,
            content={"error": "busy", "retry_after_s": exc.retry_after_s},
            headers={"Retry-After": str(int(max(1, exc.retry_after_s)))})

    # ── 1.2: vượt ngân sách ⇒ 413, trước khi chạm GPU ────────────────────────
    @app.exception_handler(ngan_sach.VuotNganSach)
    def _vuot(request: Request, exc: ngan_sach.VuotNganSach):
        return JSONResponse(status_code=413, content={
            "error": "too_long", "detail": str(exc),
            "do_dai": exc.do_dai, "tran": exc.tran})

    @app.exception_handler(eng.LoiEngine)
    def _hong(request: Request, exc: eng.LoiEngine):
        return JSONResponse(status_code=503,
                            content={"error": "engine", "detail": str(exc)})

    # ── sinh tiếng ───────────────────────────────────────────────────────────
    @app.post("/v1/speech")
    def speech(body: ThanNoi, _: None = Depends(auth)):
        text = ngan_sach.kiem_mot_luot(body.text)     # 413 TRƯỚC khi chạm GPU
        c = lay()
        wav, giay = c.noi(text, ref_b64=body.ref_b64, preset=body.preset)
        sr = c.sample_rate
        thoi_luong = len(wav) / float(sr) if sr else 0.0
        return Response(
            content=_wav_bytes(wav, sr), media_type="audio/wav",
            headers={
                # Worker vẫn phải tự đo bằng ffprobe (nguồn chân lý cho TIỀN),
                # nhưng có sẵn ở đây thì đối chiếu được ngay khi lệch.
                "X-Duration-S": f"{thoi_luong:.3f}",
                "X-Gen-S": f"{giay:.3f}",
                "X-RTF": f"{(giay / thoi_luong):.4f}" if thoi_luong else "0",
                "X-Sample-Rate": str(sr),
                "X-Tham-So": tham_so.PHIEN_BAN_THAM_SO,
            })

    @app.post("/v1/batch")
    def batch(body: ThanLo, _: None = Depends(auth)):
        texts = ngan_sach.kiem_mot_lo(body.texts)
        c = lay()
        wavs, giay = c.noi_lo(texts, ref_b64=body.ref_b64, preset=body.preset)
        sr = c.sample_rate
        import base64 as _b64
        muc = []
        for w in wavs:
            muc.append({
                "wav_b64": _b64.b64encode(_wav_bytes(w, sr)).decode("ascii"),
                "duration_s": round(len(w) / float(sr), 3) if sr else 0.0,
            })
        tong = sum(m["duration_s"] for m in muc)
        return {"items": muc, "sample_rate": sr, "gen_s": round(giay, 3),
                "rtf": round(giay / tong, 4) if tong else 0.0,
                "tham_so": tham_so.PHIEN_BAN_THAM_SO}

    @app.post("/v1/stream")
    def stream(body: ThanNoi, _: None = Depends(auth)):
        """Phát dần. Sau cờ `LTT_VOICE_STREAM=1`.

        ⚠️ Cửa này **chưa** phải hợp đồng `STREAM` của Public API (Q119/QĐ-5) —
           nó là đường nội bộ, dựng sẵn để sau MVP chỉ còn việc viết hợp đồng.
        """
        if os.environ.get("LTT_VOICE_STREAM", "0") != "1":
            raise HTTPException(status_code=404, detail="stream chua bat")
        text = ngan_sach.kiem_mot_luot(body.text)
        c = lay()
        c.nap()
        if not c.co_streaming():
            raise HTTPException(status_code=501,
                                detail="engine nay khong co infer_stream")
        sr = c.sample_rate

        def gen():
            yield _wav_header_mo(sr)
            for chunk in c.phat_dan(text, ref_b64=body.ref_b64,
                                    preset=body.preset):
                yield _pcm16(chunk)

        return StreamingResponse(gen(), media_type="audio/wav")

    # ── ghi danh ─────────────────────────────────────────────────────────────
    @app.post("/v1/enroll")
    def enroll(body: ThanGhiDanh, _: None = Depends(auth)) -> dict:
        if not os.path.isfile(body.duong_wav):
            raise HTTPException(status_code=400,
                                detail=f"khong thay tep: {body.duong_wav}")
        return lay().ghi_danh(body.duong_wav, denoise=body.denoise)

    @app.get("/v1/voices")
    def voices(_: None = Depends(auth)) -> dict:
        c = lay()
        c.nap()
        ds = []
        for muc in (c._tts.list_preset_voices() or []):
            if isinstance(muc, (tuple, list)) and len(muc) == 2:
                ds.append({"id": muc[1], "nhan": muc[0]})
            else:
                ds.append({"id": str(muc), "nhan": str(muc)})
        return {"items": ds}

    return app


app = create_app()
