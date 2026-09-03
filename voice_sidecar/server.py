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
import re
import wave

import numpy as np
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel

from . import engine as eng
from . import ngan_sach, noi_dai, tham_so

log = logging.getLogger("ltt.voice.server")


# ── WAV ──────────────────────────────────────────────────────────────────────
#: Dấu kết câu. Chỉ dùng để ĐẾM câu cho bộ ghép — không chia gì cả.
_KET_CAU = re.compile(r"[.!?…]+(?:\s|$)")


def _pcm16(wav_f32: np.ndarray) -> bytes:
    """float32 [-1,1] -> PCM16. Kẹp trước khi ép kiểu, không sau.

    Ép trước rồi kẹp là cách kinh điển để một mẫu vượt biên quấn vòng thành một
    tiếng *tách* rất to — thứ chỉ nghe thấy chứ không thấy trong test.
    """
    return (np.clip(np.asarray(wav_f32, dtype=np.float32), -1.0, 1.0)
            * 32767.0).astype(np.int16).tobytes()


def _dau(v) -> str:
    r"""Một giá trị an toàn để đặt vào đầu HTTP.

    🔴 ĐẦU HTTP CHỈ NHẬN latin-1, và Starlette **ném** khi gặp ký tự ngoài bảng
       đó. Nghĩa là một chữ tiếng Việt hay một dấu gạch ngang dài lọt vào một
       trường chẩn đoán sẽ làm **cả phản hồi** thành `500`.

    ⛔ Và đây là kiểu hỏng tệ nhất trong các kiểu: **việc đã làm xong rồi mới bị
       vứt đi**. Model đã sinh đủ tiếng, đã ghép, đã cân mức — rồi cả lượt tan
       vì một chuỗi *giải thích* có dấu `—`. Khách thấy "lỗi hệ thống", máy chủ
       thấy một `UnicodeEncodeError` ở tầng Starlette không nhắc gì tới giọng
       nói, và GPU thì đã tiêu thật.

    ⭐ Đã xảy ra thật 01/09/2026. `noi_dai.nhip_nghi` có ba lối ra; **một** trong
       ba viết `"UOC THO tu N khoang lang bat ky (khong biet so cau) — con so
       nay thien ve khe TU"`. Lối ra đó chạy khi không dò được ranh giới câu nào
       giữa các đoạn — tức đúng lúc khách nộp **nhiều dòng ngắn**, mỗi dòng một
       câu. Hai lối ra kia thuần ASCII, nên lỗi chỉ hiện ở một phần ba số ca và
       trông như ngẫu nhiên.

    ⛔ ĐỪNG sửa bằng cách bỏ dấu `—` trong chuỗi đó. Đó là đập một con chuột
       trong khi cái lỗ vẫn mở: mọi chuỗi chẩn đoán viết bằng tiếng Việt sau này
       đều là một quả mìn, và không có gì trong hệ thống kiểu nào phản đối. Sửa
       ở **cửa ra** thì cửa đóng cho tất cả.
    """
    s = "" if v is None else str(v)
    try:
        s.encode("latin-1")
        return s
    except UnicodeEncodeError:
        # Giữ được chữ nào hay chữ ấy; phần còn lại thành `?`. Đây là trường
        # CHẨN ĐOÁN — đọc được gần đúng vẫn hơn là làm hỏng cả phản hồi.
        return s.encode("latin-1", "replace").decode("latin-1")


def _wav_bytes(wav_f32: np.ndarray, sr: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(_pcm16(wav_f32))
    return buf.getvalue()


#: Thư mục mà cổng này được phép GHI vào. Rỗng ⇒ chỉ thư mục tạm của hệ thống.
#:
#: 🔴 CỬA ĐỌC VÀ CỬA GHI KHÔNG CÙNG MỘT MỨC RỦI RO, và trước `/v1/lo-ra-tep`
#:    thì cổng này chỉ có cửa ĐỌC (`/v1/enroll` nhận `duong_wav`).
#:
#:    Một cửa nhận đường dẫn tuỳ ý để GHI là một cửa ghi đè được `app.env`,
#:    ghi đè được chính `server.py`, ghi đè được một tệp của Windows. Token
#:    dùng chung và loopback vẫn là hàng rào đầu, nhưng "chỉ máy này gọi được"
#:    không có nghĩa là "mọi thứ chạy trên máy này đều đáng tin".
#:
#: ⭐ Nên đường ghi bị KẸP vào một gốc, và mặc định là thư mục tạm — chỗ worker
#:    vốn đã dựng tệp của nó. Fail-closed: không nằm dưới gốc thì 400.
_GOC_GHI = (os.environ.get("LTT_VOICE_THU_MUC_TAM") or "").strip()


def _goc_cho_phep() -> list:
    import tempfile
    goc = [tempfile.gettempdir()]
    if _GOC_GHI:
        goc.append(_GOC_GHI)
    return [os.path.realpath(g) for g in goc if g]


def _kiem_duong_ghi(duong: str) -> str:
    """Đường ghi phải nằm DƯỚI một gốc cho phép. Trả đường đã chuẩn hoá."""
    if not duong or not str(duong).strip():
        raise HTTPException(status_code=400, detail="thieu duong ra")
    that = os.path.realpath(str(duong))
    for g in _goc_cho_phep():
        # `commonpath` chứ không `startswith`: `C:	mp-khac` bắt đầu bằng
        # `C:	mp` nhưng không nằm trong nó. Một phép so chuỗi ở đây là một lỗ.
        try:
            if os.path.commonpath([that, g]) == g:
                return that
        except ValueError:
            continue            # khác ổ đĩa -> chắc chắn không nằm trong gốc
    raise HTTPException(
        status_code=400,
        detail="duong ra nam ngoai thu muc cho phep (LTT_VOICE_THU_MUC_TAM)")


def _ghi_float32(wav_f32: np.ndarray, sr: int, duong: str) -> None:
    """Ghi một đoạn ra WAV **float32**, giữ nguyên khoảng dư.

    ⛔ KHÔNG PCM16 ở đây. Xem `test_ghep_tep_canh_bao_mat_khoang_du_khi_luu_pcm16`:
       mẫu vượt 1,0 mà lưu bằng PCM16 là kẹp ngay lúc ghi, trước khi bộ hạ trần
       đỉnh của `noi_dai.ghep_tep` kịp chạy — và méo đã nằm trong tệp thì không
       cứu được. Bản đọc cuối cùng vẫn ra PCM16, nhưng chỉ SAU khi đã hạ trần.
    """
    import soundfile as sf
    thu_muc = os.path.dirname(duong)
    if thu_muc:
        os.makedirs(thu_muc, exist_ok=True)
    sf.write(duong, np.asarray(wav_f32, dtype=np.float32), int(sr),
             subtype="FLOAT")


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


class ThanLoRaTep(BaseModel):
    """Sinh một lô đoạn và GHI THẲNG RA TỆP, thay vì trả byte qua HTTP.

    ⭐ Cùng lối `/v1/enroll` đã dùng: sidecar và worker ở **cùng một máy**, nên
       đẩy âm thanh qua HTTP là chép một thứ đang nằm sẵn trên đĩa. Với đường
       văn bản dài thì đó không còn là chuyện lãng phí mà là chuyện trần cứng —
       một cuốn sách nghĩa là hàng trăm MB base64 đi qua một tiến trình web.
    """
    texts: list[str]
    #: Đường dẫn tệp **cục bộ** cho từng đoạn. Phải cùng số phần tử với `texts`.
    duong_ra: list[str]
    ref_b64: str | None = None
    preset: str | None = None


class ThanGhepTep(BaseModel):
    duong_vao: list[str]
    duong_ra: str
    #: Số câu của từng đoạn. Bộ ghép cần nó để biết đâu là ranh giới CÂU giữa
    #: hằng trăm khe TỪ — xem `noi_dai.nhip_nghi`. Thiếu thì nhịp nghỉ đo được
    #: sẽ là khe từ, và mối nối nghe gần như dính liền.
    so_cau: list[int] | None = None


class ThanGhiDanhKho(BaseModel):
    duong_wav: str
    denoise: bool = True
    #: Số cửa sổ trong kho. `chon_kho` tự cắt xuống nếu clip không đủ chỗ tốt.
    so_clip: int = 5


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
                "X-Tham-So": _dau(tham_so.PHIEN_BAN_THAM_SO),
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

    @app.post("/v1/speech-dai")
    def speech_dai(body: ThanLo, _: None = Depends(auth)):
        """Nhiều lượt sinh -> MỘT tệp WAV liền mạch (đường văn bản dài).

        ⭐ Vì sao là một cửa riêng chứ không phải `/v1/batch` + ghép ở phía app:

           `/v1/batch` trả N tệp rời, đúng cho người gọi muốn từng đoạn riêng.
           Đường văn bản dài thì ngược lại — nó cần **một** bản đọc, và việc
           ghép là việc ÂM THANH: đo im ở mối nối, lấy trung vị nhịp nghỉ, cân
           mức. Làm việc đó ở phía app nghĩa là kéo numpy và cả một bộ phân tích
           tín hiệu vào tiến trình worker, trong khi ở đây chúng đã có sẵn.

           Chia đoạn thì ngược lại là việc VĂN BẢN, và nó ở phía app
           (`text_pipeline.chia_doan`). Mỗi bên làm đúng thứ nó có công cụ.

        Trả về **cùng hình dạng** `/v1/speech` — một WAV + header — nên tầng job
        gọi cửa nào cũng chỉ có một nhánh xử lý phản hồi.
        """
        # 🔴 KHÔNG áp trần số đoạn ở cửa này. `TRAN_SO_VAN_BAN_BATCH` là kích
        #    thước một lượt gộp lô — một chi tiết thi hành bên trong — và áp nó
        #    ở đây làm nó rò ra thành hợp đồng của người gọi. Đo 01/09: một bài
        #    mười hai đoạn nhận `413 "Lo 12 van ban, vuot tran 8"`. Không ai
        #    chọn giới hạn ấy cho khách; nó là số của một cái vòng lặp đi lạc.
        texts = ngan_sach.kiem_bai_dai(body.texts)
        c = lay()

        # Bài dài hơn một lượt gộp lô thì chia NHÓM, chứ không từ chối. Phép
        # ghép vẫn làm MỘT LẦN trên toàn bộ đoạn ở dưới, nên nhịp nghỉ và phép
        # cân mức vẫn tính trên cả bài — chia nhóm ở đây thuần tuý là chuyện xếp
        # việc cho GPU, không đụng gì tới kết quả nghe được.
        n = max(1, int(tham_so.TRAN_SO_VAN_BAN_BATCH))
        wavs, giay = [], 0.0
        for i in range(0, len(texts), n):
            phan, g = c.noi_lo(texts[i:i + n], ref_b64=body.ref_b64,
                               preset=body.preset)
            wavs.extend(phan)
            giay += g
        sr = c.sample_rate
        # Số câu mỗi đoạn: bộ ghép cần nó để biết đâu là ranh giới CÂU giữa hằng
        # trăm khe TỪ. Chỉ là đếm dấu kết câu — không phải chia đoạn, việc đó
        # vẫn ở `apps/ltt_voice/text_pipeline.py`.
        so_cau = [max(1, len(_KET_CAU.findall(t)) or 1) for t in texts]
        wav, ho_so = noi_dai.ghep(wavs, sr, so_cau=so_cau)
        thoi_luong = len(wav) / float(sr) if sr else 0.0
        return Response(
            content=_wav_bytes(wav, sr), media_type="audio/wav",
            headers={
                "X-Duration-S": f"{thoi_luong:.3f}",
                "X-Gen-S": f"{giay:.3f}",
                "X-RTF": f"{(giay / thoi_luong):.4f}" if thoi_luong else "0",
                "X-Sample-Rate": str(sr),
                "X-Tham-So": _dau(tham_so.PHIEN_BAN_THAM_SO),
                # Hồ sơ phép ghép. Khi một bản đọc nghe lạ ở mối nối thì đây là
                # thứ trả lời được "nghỉ bao lâu, con số đó từ đâu ra, đoạn nào
                # bị cân mức" — thay vì phải chạy lại rồi đoán.
                "X-So-Doan": _dau(ho_so.get("so_doan", 0)),
                "X-Nghi-S": _dau(ho_so.get("nghi_s", 0.0)),
                "X-Nguon-Nghi": _dau(ho_so.get("nguon_nghi", "")),
                # Mốc từng đoạn, giây, ngăn bằng dấu phẩy. Thiếu nó thì người
                # đo lại phải CHIA DEU mà đoán, và chia đều sai luỹ tiến vì mỗi
                # mối nối chèn thêm `nghi` giây — sinh ra đúng hình dạng một xu
                # hướng đơn điệu. Xem chú thích ở `noi_dai.ghep`.
                "X-Moc-S": _dau(",".join(str(x) for x in
                                         (ho_so.get("moc_s") or ()))),
                "X-Ha-Tran-Db": _dau(ho_so.get("ha_tran_db", 0.0)),
            })

    @app.post("/v1/lo-ra-tep")
    def lo_ra_tep(body: ThanLoRaTep, _: None = Depends(auth)):
        """Sinh một lô đoạn -> GHI RA TỆP. Trả hồ sơ từng đoạn, không trả byte.

        🔴 VÌ SAO KHÔNG DÙNG `/v1/batch` CHO ĐƯỜNG TÀI LIỆU DÀI.

           `/v1/batch` trả base64 của từng WAV trong một phản hồi JSON. Với tám
           đoạn thì đó là vài MB, không sao. Với một cuốn sách thì mỗi lô vẫn
           vài MB nhưng **worker phải giữ chúng, giải base64, rồi ghi ra đĩa** —
           và nó làm việc đó hàng chục lần. Sidecar đã có sóng âm trong tay và
           đã có `soundfile`; để nó ghi thẳng là bỏ được cả một vòng chép.

        ⭐ VÀ GHI BẰNG FLOAT32, KHÔNG PHẢI PCM16. Đây là một ràng buộc đã chốt
           bằng phép kiểm (`test_ghep_tep_canh_bao_mat_khoang_du_khi_luu_pcm16`):
           mẫu vượt 1,0 mà lưu bằng PCM16 là **kẹp ngay lúc ghi**, trước khi bộ
           hạ trần đỉnh của `noi_dai` kịp chạy. Méo nằm trong tệp rồi thì không
           bộ hạ trần nào cứu được nữa.
        """
        if len(body.duong_ra) != len(body.texts):
            raise HTTPException(
                status_code=400,
                detail=(f"{len(body.texts)} van ban nhung {len(body.duong_ra)} "
                        f"duong ra"))
        for d in body.duong_ra:
            _kiem_duong_ghi(d)

        texts = ngan_sach.kiem_bai_dai(body.texts)
        c = lay()
        sr = c.sample_rate

        # Chia nhóm theo kích thước một lượt gộp lô — cùng lý do `/v1/speech-dai`
        # làm vậy: đó là chuyện xếp việc cho GPU, không phải hợp đồng của khách.
        n = max(1, int(tham_so.TRAN_SO_VAN_BAN_BATCH))
        muc, giay_sinh = [], 0.0
        for i in range(0, len(texts), n):
            phan, g = c.noi_lo(texts[i:i + n], ref_b64=body.ref_b64,
                               preset=body.preset)
            giay_sinh += g
            for j, w in enumerate(phan):
                duong = body.duong_ra[i + j]
                _ghi_float32(w, sr, duong)
                muc.append({
                    "chi_so": i + j,
                    "duong": duong,
                    "giay": round(len(w) / float(sr), 3) if sr else 0.0,
                    "so_cau": max(1, len(_KET_CAU.findall(texts[i + j])) or 1),
                })

        tong = sum(m["giay"] for m in muc)
        return {"items": muc, "sample_rate": sr,
                "gen_s": round(giay_sinh, 3),
                "rtf": round(giay_sinh / tong, 4) if tong else 0.0,
                "tham_so": tham_so.PHIEN_BAN_THAM_SO}

    @app.post("/v1/ghep-tep")
    def ghep_tep(body: ThanGhepTep, _: None = Depends(auth)):
        """Ghép các đoạn ĐÃ CÓ TRÊN ĐĨA thành một bản đọc. Trả hồ sơ phép ghép.

        ⭐ Tách khỏi `/v1/speech-dai` chứ không thay nó: cửa kia sinh **và**
           ghép trong một lượt gọi, đúng cho bài vừa phải. Cửa này chỉ ghép, nên
           nó cho phép sinh lại **một** đoạn hỏng rồi ghép lại cả bài mà không
           phải đọc lại 79 đoạn kia.
        """
        if not body.duong_vao:
            raise HTTPException(status_code=400, detail="khong co doan nao")
        for d in body.duong_vao:
            if not os.path.isfile(d):
                raise HTTPException(status_code=400,
                                    detail=f"khong thay tep: {d}")
        _kiem_duong_ghi(body.duong_ra)
        if body.so_cau is not None and len(body.so_cau) != len(body.duong_vao):
            raise HTTPException(
                status_code=400,
                detail=(f"so_cau co {len(body.so_cau)} muc cho "
                        f"{len(body.duong_vao)} doan"))
        return noi_dai.ghep_tep(body.duong_vao, body.duong_ra,
                                so_cau=body.so_cau)

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
    @app.post("/v1/enroll-kho")
    def enroll_kho(body: ThanGhiDanhKho, _: None = Depends(auth)) -> dict:
        """Ghi danh theo KHO nhiều cửa sổ (K2).

        ⛔ Cửa RIÊNG chứ không phải một tham số của `/v1/enroll`. Hai lý do:
           nó tốn `so_clip` lần `prepare_reference` nên chi phí khác hẳn, và
           đường cũ phải giữ nguyên **không đổi một dòng nào** trong lúc còn đo
           xem đường mới có tốt hơn không.
        """
        c = lay()
        return c.ghi_danh_kho(body.duong_wav, denoise=body.denoise,
                              so_clip=body.so_clip)

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
