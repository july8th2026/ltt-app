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

from .features import DangBanTam, LoiGiongNoi, LoiHaTang  # noqa: F401 (giữ tên cho chỗ import)
from .tham_so_cong_khai import TRAN_MOI_LUOT_SINH

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

    from . import features, sidecar_client, tham_chieu, toc_do

    yc = features.chuan_hoa(params)

    if not sidecar_client.san_sang():
        raise LoiGiongNoi(_t(
            "Máy tạo tiếng nói chưa được thiết lập trên máy chủ này "
            "(thiếu LTT_VOICE_SIDECAR_TOKEN)."))

    ref_b64, preset, _ = _voi_db(lambda db: features.giai_giong(db, yc))

    # ── chia đoạn: văn bản dài đi ĐƯỜNG KHÁC, không phải bị từ chối ──────────
    #
    # `TRAN_MOI_LUOT_SINH` là trần của MỘT lượt `infer` (trần chất lượng, Q119).
    # `TRAN_KY_TU_CONG_KHAI` là trần của MỘT YÊU CẦU. Trước 31/08 hai thứ này là
    # một con số, nên "dài hơn 1.500" đồng nghĩa với "bị từ chối" — dù chính
    # thông điệp lỗi của cổng đã nói *"phải đi đường long-form nhiều lượt"*.
    #
    # ⭐ Chia lượt an toàn vì đã ĐO, không vì hợp lý: giọng mặc định giữ nguyên
    #    người nói qua các lượt gọi riêng (0,9254 — cao hơn cả sàn nhiễu 0,8524
    #    của hai nửa trong cùng một lượt). Xem
    #    `voice_sidecar/do_giu_giong_nhieu_luot.py`.
    chuan = features.chuan_bi_van_ban(yc, tran_moi_doan=TRAN_MOI_LUOT_SINH)
    doan = chuan.doan or [yc.text]

    # ⛔ BẬN KHÔNG PHẢI HỎNG — để `DangBanTam` bay lên nguyên vẹn cho job_runner
    #    xếp lại. Bọc nó thành LoiGiongNoi ở đây là biến "máy đang bận" thành
    #    "job hỏng", và một job hỏng sẽ TRỪ CREDIT cho việc chưa từng chạy.
    if len(doan) > 1:
        wav_bytes, headers = features.goi_cong_dai(
            doan, ref_b64=ref_b64, preset=preset)
    else:
        wav_bytes, headers = features.goi_cong(
            doan[0], ref_b64=ref_b64, preset=preset)

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

    # ── TỐC ĐỘ HẬU KỲ ────────────────────────────────────────────────────────
    #
    # 🔴 ĐÚNG CHỖ NÀY, KHÔNG SỚM HƠN. Hai lý do độc lập, và cả hai đều hỏng
    #    theo kiểu im lặng nếu đặt sai:
    #
    #    ① `giay` ở trên là cơ sở TÍNH TIỀN. Kéo giãn 1,5× làm tệp ngắn đi một
    #       phần ba, nên đặt trước phép đo là để khách chọn tốc độ nhanh trả ít
    #       hơn cho **cùng một lượng việc GPU**. Đó là một lỗ khai thác được.
    #    ② Chốt chất lượng K1 chạy trong sidecar, trên sóng âm CHƯA kéo giãn.
    #       Hệ cũ ghi lại bài học này: time-stretch làm lệch MỌI số đo F0, nên
    #       nó đóng băng `post_speed` vô điều kiện trước khi đọc bất kỳ số nào.
    #
    # ⇒ Thứ tự bất biến: sinh → đo → (tính tiền theo `giay`) → kéo giãn → lưu.
    giay_phat = 0.0
    if toc_do.can_doi(yc.toc_do):
        wav_bytes = toc_do.ap_dung(wav_bytes, yc.toc_do)
        giay_phat = giay / toc_do.hop_le(yc.toc_do)

    job_id = str(getattr(ctx, "job_id", "") or "adhoc")
    # 🔴 `{job_id}/` — CÓ dấu gạch chéo sau job id, không phải `{job_id}.wav`.
    #
    #    `platform_core/job_content.py` nhận diện tệp thuộc về một job bằng
    #    cách tìm **`/{job_id}/` như một đoạn đường dẫn**, và nó cố ý sai
    #    theo hướng bỏ sót: thà không dọn còn hơn xoá nhầm tệp của job khác.
    #
    #    Bản đầu ghi `.../{job_id}.wav` — job id nằm cuối, theo sau là dấu
    #    chấm. Không khớp. Hệ quả: **tệp tiếng của app này không bao giờ
    #    bị dọn**, trong khi vòng bảo trì vẫn chạy, vẫn báo thành công, và
    #    `content_expired_at` vẫn được đánh dấu. Một rò rỉ hoàn toàn im
    #    lặng: đủ giấy tờ nói đã dọn, không tệp nào bị xoá.
    #
    #    Bảy app còn lại đều theo đúng `{app}/{owner}/{job_id}/...`; chỉ
    #    app này lệch. `tests/test_343` chốt lại cả hai chiều.
    khoa = f"voice/out/{yc.owner_id or 'chung'}/{job_id}/tieng.wav"
    get_storage().put(khoa, io.BytesIO(wav_bytes), content_type="audio/wav")

    ket = features.KetQua(
        yeu_cau=yc, audio_key=khoa, giay=giay, giay_phat=giay_phat,
        text_da_chuan_hoa=chuan.da_chuan_hoa, so_doan=len(doan))

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
    # ⛔ Giữ dạng chuỗi: `User.id` là UUID chuỗi. Bản đầu ép `int()` rồi nuốt
    #    lỗi thành `0` — một giá trị hợp lệ về kiểu, sai về nghĩa, và nó biến
    #    "ghi danh cho ai" thành "ghi danh cho người dùng số 0".
    owner_id = str(p.get("owner_id") or "").strip()
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
            # ⛔ `LoiHaTang`, KHÔNG phải `LoiGiongNoi` — cùng lỗi đã sửa ở
            #    `features._goi_va_dich_loi` (09b5ab6), và bản sửa đó BỎ SÓT chỗ
            #    này. `LoiGiongNoi` kế thừa `LoiNguoiGoi` nên nền tảng không thử
            #    lại, trong khi thông điệp hứa với khách là "vui lòng thử lại".
            #    Cổng giọng khởi động lại sau deploy ⇒ mọi lượt ghi danh đang
            #    bay hỏng vĩnh viễn thay vì được xếp lại vài giây sau.
            raise LoiHaTang(_t("Không ghi danh được giọng. Vui lòng thử lại.")) from e
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    khoa, vt = tham_chieu.luu_bieu_dien(owner_id=owner_id, public_id=public_id,
                                        ref_b64=kq["ref_b64"])

    # ⭐ Hồ sơ chọn đoạn đi thẳng ra kết quả job: khách quay lại hỏi "sao giọng
    #    nghe không giống tôi" thì đây là thứ trả lời được — ta đã lấy đoạn nào
    #    trong clip của họ, và vì sao. Không có nó thì phép chọn là một phỏng
    #    đoán chạy ngầm, đúng lớp lỗi cả app này đi sửa.
    #
    # ⚠️ Đây là để HIỆN, không phải để đối chất: `job_content.purge_expired` dọn
    #    `result = {}` sau 30 ngày. Bằng chứng cần sống lâu hơn thì phải nằm ở
    #    một cột trong bảng của app.
    chon = kq.get("chon_doan") or {}

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
        "chon_doan": chon,
    }
