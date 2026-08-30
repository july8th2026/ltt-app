"""
jobs.py — handler chạy trong worker.

⭐ Handler này **mỏng có chủ ý**. Quy tắc nghiệp vụ ở `features.py`; tệp này chỉ
   làm bốn việc: mở phiên CSDL ngắn, gọi nghiệp vụ, đưa tệp vào kho, và **báo
   `credit_cost`**.

⛔ `jobs.py` là MỘT CÁNH CỬA. Quy tắc nằm trong một cánh cửa thì cửa thứ hai phải
   chép lại, và hai bản chép sẽ lệch. Bài học đã ghi ở `apps/anhnoibo/jobs.py`.

⚠️ KHÔNG giữ một phiên CSDL suốt cả job. Một bài dài chạy hàng chục giây; giữ
   transaction mở suốt thời gian đó là giữ khoá CSDL trong lúc chờ mạng.
"""
from __future__ import annotations

import logging
import os
import tempfile

from platform_core.i18n import _ as _t

from .features import DangBanTam, LoiGiongNoi  # noqa: F401 (giữ tên cho chỗ import)

log = logging.getLogger(__name__)


def _voi_db(ham):
    """Chạy `ham(db)` trong một phiên CSDL NGẮN rồi đóng ngay.

    Không dùng `ctx.db`: `JobContext` **không có** thuộc tính đó — nó chỉ cấp
    `job_id`/`gpu_uuid`/`progress()`.
    """
    from platform_core.db import get_session

    gen = get_session()
    db = next(gen)
    try:
        kq = ham(db)
        db.commit()
        return kq
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _do_thoi_luong(duong: str) -> float:
    """Thời lượng THẬT bằng ffprobe. **Đây là nguồn chân lý cho tiền.**

    Không đo được ⇒ trả `0.0`, và `KetQua.credit_that` sẽ thu **0** (khuôn 3.5).
    Thu tiền không bằng chứng tệ hơn mất một ít tiền.
    """
    try:
        from platform_core.media import duration_seconds
        return float(duration_seconds(duong) or 0.0)
    except Exception as e:  # noqa: BLE001 - không đo được là một kết quả, không phải lỗi
        log.warning("khong do duoc thoi luong %s: %s", duong, e)
        return 0.0


def handle(params: dict, ctx=None) -> dict:
    """Cửa DUY NHẤT mà nền tảng gọi. Tự phân nhánh theo `job_type`.

    🔴 `platform_core/jobs.py::resolve_handler` **luôn** lấy `handle` bất kể
       `job_type` — nó tra app sở hữu rồi `getattr(mod, "handle")`, hết. Một app
       nhiều loại job mà đặt tên hàm theo loại (`handle_enroll`, …) thì những hàm
       đó **không bao giờ được gọi**, và triệu chứng là job ghi danh chạy nhầm
       nhánh tạo tiếng rồi hỏng vì thiếu `text` — một thông điệp trỏ sai chỗ hoàn
       toàn.

    ⭐ Đọc `ctx.job_type` trước, `params["_job_type"]` sau: `ctx` là thứ **nền
       tảng** đặt, còn params là thứ cửa gọi đặt — nên khi hai cái lệch nhau thì
       nền tảng đúng. Vẫn giữ đường params làm dự phòng cho lời gọi trực tiếp
       trong test.
    """
    loai = str(getattr(ctx, "job_type", "") or params.get("_job_type") or "")
    if loai.endswith(".enroll"):
        return _ghi_danh(params, ctx)
    return _tao_tieng(params, ctx)


def _tao_tieng(params: dict, ctx=None) -> dict:
    """`ltt_voice.synthesize` — tạo tiếng nói từ văn bản."""
    import io

    from platform_core.storage import get_storage

    from . import features, sidecar_client, tham_chieu

    yc = features.chuan_hoa(params)

    if not sidecar_client.san_sang():
        raise LoiGiongNoi(_t(
            "Máy tạo tiếng nói chưa được thiết lập trên máy chủ này "
            "(thiếu LTT_VOICE_SIDECAR_TOKEN)."))

    ref_b64, preset, _ = _voi_db(lambda db: features.giai_giong(db, yc))

    # ⛔ BẬN KHÔNG PHẢI HỎNG — để `DangBanTam` bay lên nguyên vẹn cho job_runner
    #    xếp lại. Bọc nó thành LoiGiongNoi ở đây là biến "máy đang bận" thành
    #    "job hỏng", và một job hỏng sẽ TRỪ CREDIT cho việc chưa từng chạy.
    wav_bytes, headers = features.goi_cong(yc.text, ref_b64=ref_b64, preset=preset)

    # Đo trên tệp thật, không tin header của sidecar. Header chỉ để đối chiếu.
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    try:
        tmp.write(wav_bytes)
        tmp.close()
        giay = _do_thoi_luong(tmp.name)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    khai = headers.get("X-Duration-S")
    if khai and giay:
        try:
            lech = abs(float(khai) - giay)
            if lech > 0.5:
                # Không phải lỗi để dừng, nhưng là dấu hiệu một trong hai phía
                # đang tính sai — và một trong hai phía đó ra hoá đơn.
                log.warning("job %s: sidecar khai %ss, ffprobe do %.3fs (lech %.3f)",
                            getattr(ctx, "job_id", "?"), khai, giay, lech)
        except (TypeError, ValueError):
            pass

    job_id = str(getattr(ctx, "job_id", "") or "adhoc")
    khoa = f"voice/out/{yc.owner_id or 'chung'}/{job_id}.wav"
    get_storage().put(khoa, io.BytesIO(wav_bytes), content_type="audio/wav")

    ket = features.KetQua(
        yeu_cau=yc, audio_key=khoa, giay=giay,
        text_da_chuan_hoa=yc.text, so_doan=1)

    if giay <= 0:
        log.warning("job %s: khong do duoc thoi luong -> thu 0 credit", job_id)

    return ket.as_result()


def _ghi_danh(params: dict, ctx=None) -> dict:
    """`ltt_voice.enroll` — clip tham chiếu -> biểu diễn giọng.

    ⭐ IDEMPOTENT theo **hash tệp nguồn**. Gửi lại đúng clip đó cho đúng giọng đó
       không tạo thêm biểu diễn và không thu thêm tiền: bảng `voice_ref` có ràng
       buộc DUY NHẤT `(profile_id, sha256)`, nên lần thứ hai đọc lại bản cũ.
    """
    from . import features, gia, sidecar_client, tham_chieu

    p = params or {}
    try:
        owner_id = int(p.get("owner_id") or 0)
    except (TypeError, ValueError):
        owner_id = 0
    public_id = str(p.get("voice_id") or "").strip()
    nguon_key = str(p.get("source_key") or "").strip()
    if not (owner_id and public_id and nguon_key):
        raise LoiGiongNoi(_t("Thiếu thông tin để ghi danh giọng."))

    if not sidecar_client.san_sang():
        raise LoiGiongNoi(_t("Máy tạo tiếng nói chưa được thiết lập."))

    ho_so = _voi_db(lambda db: tham_chieu.tim_profile(db, public_id,
                                                      owner_id=owner_id))
    if ho_so is None:
        raise LoiGiongNoi(_t("Không tìm thấy giọng này trong tài khoản của bạn."))

    # Tải bản gốc từ kho về một tệp tạm — sidecar nhận đường dẫn cục bộ.
    from platform_core.storage import get_storage
    st = get_storage()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    try:
        with st.open(nguon_key) as f:
            tmp.write(f.read())
        tmp.close()
        try:
            kq = sidecar_client.ghi_danh(tmp.name, denoise=True)
        except sidecar_client.SidecarBan as e:
            raise DangBanTam(retry_after_s=e.retry_after_s) from e
        except sidecar_client.LoiSidecar as e:
            raise LoiGiongNoi(_t("Không ghi danh được giọng. Vui lòng thử lại.")) from e
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    khoa, vt = tham_chieu.luu_bieu_dien(owner_id=owner_id, public_id=public_id,
                                        ref_b64=kq["ref_b64"])

    def _ghi(db):
        from .tables import VoiceProfile, VoiceRepr
        r = VoiceRepr(profile_id=ho_so.id, ref_id=int(p.get("ref_id") or 0),
                      engine="vieneu",
                      model_repo=str(p.get("model_repo") or ""),
                      model_revision=str(p.get("model_revision") or ""),
                      sdk_version=str(p.get("sdk_version") or ""),
                      storage_key=khoa, fingerprint=vt,
                      trang_thai="dang_dung")
        db.add(r)
        # ⛔ Profile chỉ sang `active` SAU KHI có biểu diễn. Đảo thứ tự là để lại
        #    một giọng "dùng được" mà gọi tới thì không có gì để đọc.
        db.execute(
            VoiceProfile.__table__.update()
            .where(VoiceProfile.id == ho_so.id)
            .values(trang_thai="active"))
        return r

    _voi_db(_ghi)

    return {
        "voice_id": public_id,
        "fingerprint": vt,
        "emb_dim": kq.get("emb_dim"),
        "credit_cost": gia.CREDIT_GHI_DANH,
        "phien_ban_gia": gia.PHIEN_BAN_GIA,
    }
