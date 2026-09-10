"""Cửa PHÁT DẦN (U-07) — nghe câu đầu trong ~2 giây thay vì chờ cả bài.

Mô hình tính tiền **β**, chốt bởi chủ sản phẩm 09/09/2026: giữ chỗ trước, quyết
toán theo **số byte PCM đã thật sự gửi đi**. Khách ngắt giữa chừng thì trả đúng
phần đã nghe.

## 🔴 BỐN THỨ CỬA NÀY PHẢI GIỮ, VÀ CHÚNG ĐỀU DỄ MẤT Ở MỘT ĐƯỜNG STREAM

    quyen so huu   `features.giai_giong` — cho duy nhat kiem, khong chep lai
    suat GPU       `admission` giu SUOT generator, khong chi luc mo
    tien           giu truoc · quyet toan sau · hoan phan du
    ban ghi        mot `job_id` tong hop de so credit co khoa

## ⛔ VÌ SAO KHÔNG DÙNG `hold_persisted`

Nó là context manager, và khối của nó **kết thúc trước khi** generator chạy —
Starlette gọi generator sau khi route trả về. Dùng nó ở đây là nhả suất GPU
ngay lúc bắt đầu phát, tức đúng thứ `engine.phat_dan` cấm: *"nhả sớm là để lượt
thứ hai chen vào giữa lúc lượt đầu còn đang chiếm engine."*

⇒ Giành **trước** khi trả phản hồi (để còn 503 được), rồi `keep_alive` trong
  generator lo nhịp đập và nhả.

## ⚠️ PHIÊN CSDL CỦA GENERATOR PHẢI LÀ PHIÊN RIÊNG

Phiên của route đóng khi route trả về. Quyết toán chạy sau đó, nên nó mở phiên
của chính nó — cùng lý do `admission.hold_persisted` tự mở phiên.
"""
from __future__ import annotations

import logging
import uuid

from ._chung import (Depends, Form, JSONResponse, Request, StreamingResponse,
                     _het_phien, _t, _uid, features, gia, require_login, router,
                     user_hien_tai, verify_csrf_token)
from .. import text_pipeline

log = logging.getLogger(__name__)

#: Trần một lượt phát dần = trần MỘT lượt sinh. Đường này là một lượt đọc liền
#: mạch, không phải một bài nhiều đoạn — bài dài đi qua Dự án hoặc hàng đợi job.
from ..tham_so_cong_khai import TRAN_MOI_LUOT_SINH  # noqa: E402

#: Trần thời gian một lượt phát. Rộng hơn `nghe_thu` (45 s) vì bài dài hơn,
#: nhưng vẫn PHẢI có: không trần thì một cổng treo giữ một worker web mãi mãi.
TRAN_THOI_GIAN_S = 300.0


def bat_phat_dan() -> bool:
    """Cửa này có mở không.

    ⭐ CÙNG TÊN BIẾN VỚI SIDECAR (`LTT_VOICE_STREAM`), và đó là chủ ý. Web và
       sidecar là hai tiến trình, nhưng cả hai lấy môi trường từ **một**
       `secrets\\app.env` — nên một dòng bật cả hai, và không có trạng thái
       "web mở mà cổng đóng".

    ⚠️ `nssm` nướng ENV lúc CÀI. Sửa `app.env` rồi `Restart-Service` là **KHÔNG
       ĐỦ** — phải chạy `setup\\nap_lai_env.ps1`. Dự án này đã dính ba lần.

    ⛔ Tắt thì route trả **404**, không phải một nút xám. Một bề mặt tồn tại mà
       luôn hỏng là thứ `manifest.py` gọi là *"một lời hứa thành một lỗi"*.
    """
    import os
    return (os.environ.get("LTT_VOICE_STREAM", "0") or "0").strip() == "1"


def _quyet_toan(uid: str, ma_phien: str, so_byte_pcm: int, sr: int) -> None:
    """Thu theo phần ĐÃ GỬI, hoàn phần dư. Chạy trong `finally` của generator.

    ⛔ Nuốt mọi lỗi. Đây là nhánh dọn dẹp: ném ở đây không cứu được gì (phản hồi
       đã gửi xong) mà lại che mất lỗi thật. Khoản giữ không kết sổ được vẫn có
       đường về — `credit.giu_cho_treo` nhặt nó sau 6 giờ vì không hàng `Job`
       nào mang khoá ấy.
    """
    from platform_core import credit
    from platform_core.db import get_session

    gen = get_session()
    db = next(gen)
    try:
        giay = gia.giay_tu_pcm(so_byte_pcm, sr) if sr > 0 else 0.0
        credit.quyet_toan(db, uid, ma_phien, gia.tinh(giay) if giay > 0 else 0)
        db.commit()
        log.info("phat dan %s: %.2fs -> %d credit", ma_phien, giay,
                 gia.tinh(giay) if giay > 0 else 0)
    except Exception:  # noqa: BLE001 - nhanh don dep, xem docstring
        log.exception("phat dan %s: khong quyet toan duoc", ma_phien)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.post("/phat-dan")
def phat_dan(request: Request, text: str = Form(""), voice_id: str = Form(""),
             preset: str = Form(""), csrf_token: str = Form(""),
             user=Depends(user_hien_tai), _=Depends(require_login)):
    """Đọc và phát dần. Trả `audio/wav` chunked."""
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.llm import admission
    from .. import sidecar_client

    if not bat_phat_dan():
        # 404, cùng mã sidecar dùng: cửa **không tồn tại** khi cờ tắt.
        return JSONResponse({"ok": False, "loi": _t("Không có đường này.")},
                            status_code=404)
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()

    uid = _uid(user)
    try:
        yc = features.chuan_hoa({"text": text, "voice_id": voice_id,
                                 "preset": preset, "owner_id": uid})
    except features.LoiGiongNoi as e:
        return JSONResponse({"ok": False, "loi": str(e)}, status_code=400)

    # Đếm ký tự SAU chuẩn hoá — cùng thước với `manifest._gia()`. Đếm trước
    # chuẩn hoá là giữ thiếu ở đúng những câu chuẩn hoá làm nở ra.
    chuan = text_pipeline.chuan_bi(yc.text, tran_moi_doan=TRAN_MOI_LUOT_SINH,
                                   doc_so_tran=yc.doc_so_tran)
    so_ky_tu = len(chuan.da_chuan_hoa)
    if so_ky_tu > TRAN_MOI_LUOT_SINH:
        return JSONResponse({"ok": False, "loi": _t(
            "Phát dần tối đa {n} ký tự một lượt. Bài dài hơn hãy dùng Dự án."
        ).format(n=TRAN_MOI_LUOT_SINH)}, status_code=400)

    gen_db = get_session()
    db = next(gen_db)
    ma_phien = "stream:" + uuid.uuid4().hex
    lease_id = ""
    try:
        # ⛔ Quyền sở hữu kiểm ở ĐÂY, qua cửa duy nhất. Không chép phép kiểm.
        try:
            ref_b64, preset_that, canh_bao = features.giai_giong(db, yc)
        except features.LoiGiongNoi as e:
            return JSONResponse({"ok": False, "loi": str(e)}, status_code=400)

        giu = gia.uoc_tran(so_ky_tu=so_ky_tu, giong=(preset_that or ""))
        try:
            credit.giu_cho(db, uid, giu, ma_phien)
            db.commit()
        except credit.ThieuCreditError:
            return JSONResponse({"ok": False, "loi": _t(
                "Không đủ credit cho lượt đọc này.")}, status_code=402)

        # 🔴 GIÀNH TRƯỚC KHI TRẢ PHẢN HỒI. Sau khi `StreamingResponse` bắt đầu
        #    thì không đổi được mã trạng thái nữa — muốn 503 thì phải 503 ở đây.
        lease = admission.acquire(db, resource="vieneu_gpu", slots=1,
                                  user_id=uid, mode="phat_dan",
                                  holder_id=f"phatdan:{uid}", job_id=ma_phien)
        db.commit()
        if lease is None:
            credit.hoan(db, uid, ma_phien)
            db.commit()
            return JSONResponse({"ok": False, "loi": _t(
                "Máy đang bận tạo tiếng cho lượt khác. Thử lại sau ít giây."
            )}, status_code=503)
        lease_id = str(lease.id)
    finally:
        try:
            next(gen_db)
        except StopIteration:
            pass

    def luong():
        so_byte_pcm = 0
        sr = 0
        try:
            with admission.keep_alive(lease_id):
                for khoi in sidecar_client.phat_dan(
                        yc.text, ref_b64=ref_b64, preset=preset_that,
                        timeout=TRAN_THOI_GIAN_S):
                    if sr == 0:
                        # Khối đầu mang header. Sai định dạng thì `DinhDangLa`
                        # nổ ở đây — thà hỏng một lượt còn hơn thu sai mọi lượt.
                        sr = gia.doc_sample_rate(khoi)
                        so_byte_pcm += max(0, len(khoi) - gia.DAI_HEADER_WAV)
                    else:
                        so_byte_pcm += len(khoi)
                    yield khoi
        finally:
            _quyet_toan(uid, ma_phien, so_byte_pcm, sr)

    dau = {"Cache-Control": "no-store", "X-Ma-Phien": ma_phien}
    if canh_bao:
        # 🔴 CẢNH BÁO LÙI GIỌNG PHẢI TỚI ĐƯỢC KHÁCH — nguyên văn, không phải
        #    một lá cờ. Bản đầu của tôi đặt `"1"`, và đó là một lỗi thật: khách
        #    biết *"có gì đó đã đổi"* mà không biết **đổi thành giọng nào**.
        #    Đúng thứ `lui_giong.py` sinh ra để chống — *"lùi im lặng chính là
        #    thứ ta đang đi sửa"* — chỉ là im một nửa.
        #
        # ⛔ MÃ HOÁ PHẦN TRĂM, không nhét chuỗi thô. Đầu HTTP chỉ nhận latin-1
        #    và Starlette **ném** khi gặp ký tự ngoài bảng đó; câu cảnh báo thì
        #    luôn có dấu tiếng Việt. `voice_sidecar/server.py::_dau` đã ghi lại
        #    đúng kiểu hỏng ấy: *"việc đã làm xong rồi mới bị vứt đi"* — model
        #    sinh đủ tiếng, rồi cả lượt tan vì một chuỗi GIẢI THÍCH.
        from urllib.parse import quote
        dau["X-Canh-Bao"] = quote(canh_bao[0], safe="")
    return StreamingResponse(luong(), media_type="audio/wav", headers=dau)
