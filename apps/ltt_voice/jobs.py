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
from platform_core.jobs import DangBan, LoiNguoiGoi

from .features import DangBanTam, LoiGiongNoi, LoiHaTang  # noqa: F401 (giữ tên cho chỗ import)
from .tham_so_cong_khai import SO_LAN_THU_JOB, TRAN_MOI_LUOT_SINH

log = logging.getLogger(__name__)

#: Mã HTTP 4xx mà `sidecar_client.LoiSidecar` mang theo nhưng KHÔNG coi là lỗi
#: vĩnh viễn của chính clip (review round 1, IMPORTANT 1):
#:   408 Request Timeout    — mạng/cổng chậm, không phải clip sai;
#:   409 Conflict           — trạng thái phía cổng, không phải clip sai;
#:   429 Too Many Requests  — đã tách thành `SidecarBan` riêng ở
#:                            `_dich_loi_http`; giữ ở đây cho rõ Ý ĐỊNH nếu
#:                            đường tách đó đổi.
_HTTP_4XX_TAM_THOI = frozenset({408, 409, 429})


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
        # 🔴 T-14 (review round 1, IMPORTANT 1-b): AN TOÀN CUỐI ở LƯỢT THỬ
        #    CUỐI. Không phải mọi thất bại của `_ghi_danh` tự đặt `loi` — một
        #    lỗi HẠ TẦNG (`LoiHaTang`, vd cổng trả 5xx) vẫn PHẢI được thử lại,
        #    và nền tảng (`platform_core/job_runner.py::_chay_handler`) tự
        #    làm việc đó tới `SO_LAN_THU_JOB` lần. Nhưng nền tảng KHÔNG BIẾT
        #    gì về `VoiceProfile.trang_thai` — đó là dữ liệu của app này —
        #    nên khi nó âm thầm bỏ cuộc sau lượt cuối, hồ sơ mắc kẹt vĩnh
        #    viễn ở `dang_ghi_danh` (và thu hồi bị chặn ở trạng thái đó, xem
        #    `giong_vong_doi._CHUYEN`). Bắt Ở ĐÂY, không sửa `_ghi_danh`:
        #    `tests/test_367_...::test_ghi_danh_dich_loi_HA_TANG_dung_lop`
        #    đọc `inspect.getsource(jobs._ghi_danh)` và giả định thân hàm đó
        #    KHÔNG đổi hình dạng ngoài các nhánh `except` đã có.
        try:
            return _ghi_danh(params, ctx)
        except DangBan:
            # "Bận" (`DangBanTam` kế thừa `DangBan`) KHÔNG tiêu một lượt thử
            # (`job_runner._provider_failure_kind`: nhánh `resource_wait`
            # không tăng `job.attempts`) — `ctx.attempt` ở lượt kế vẫn y hệt
            # lượt này, nên đây KHÔNG PHẢI lượt cuối thật. Ném thẳng.
            raise
        except Exception:
            _dat_loi_khi_het_luot(params, ctx)
            raise
    return _tao_tieng(params, ctx)


def _dat_loi_khi_het_luot(params: dict, ctx=None) -> None:
    """AN TOÀN CUỐI của T-14 (review round 1, IMPORTANT 1-b) — xem chú thích
    ở `handle()`. Chỉ đặt `loi` khi ĐÂY THẬT SỰ là lượt thử CUỐI của job
    `ltt_voice.enroll` và hồ sơ vẫn còn `dang_ghi_danh`; mọi nhánh khác là
    no-op im lặng.

    ⚠️ `ctx.attempt` là số 1-based mà `job_runner._chay_handler` gán TRƯỚC khi
       gọi handler (`int(job.attempts or 0) + 1`) — lượt cuối là khi nó bằng
       đúng số lần thử job này được khai lúc nộp. `ltt_voice.enroll` LUÔN khai
       đúng `SO_LAN_THU_JOB` (cả cửa web `tao_giong` lẫn Public API đều đi
       qua `AppManifest.so_lan_thu_for`, xem `manifest.py:so_lan_thu`) — nên
       so với hằng số MODULE này an toàn, không cần đọc CSDL `Job.max_attempts`
       (tránh một phép đọc `platform_core.models.Job` không cần thiết).

    ⛔ `ctx=None` (gọi `_ghi_danh`/`handle` trực tiếp trong test hay từ một
       lời gọi không qua worker) ⇒ bỏ qua: không có lượt thử nào để đếm.
    """
    if ctx is None:
        return
    try:
        if int(getattr(ctx, "attempt", 0) or 0) < SO_LAN_THU_JOB:
            return
    except (TypeError, ValueError):
        return
    p = params or {}
    owner_id = str(p.get("owner_id") or "").strip()
    public_id = str(p.get("voice_id") or "").strip()
    if not (owner_id and public_id):
        return

    def _dat(db):
        from . import giong_vong_doi, tham_chieu
        from .tables import VoiceProfile
        ho_so = tham_chieu.tim_profile(db, public_id, owner_id=owner_id)
        if ho_so is None:
            return
        db.execute(
            VoiceProfile.__table__.update()
            .where(VoiceProfile.id == ho_so.id,
                  VoiceProfile.trang_thai == giong_vong_doi.TT_DANG_GHI_DANH)
            .values(trang_thai=giong_vong_doi.TT_LOI))
    try:
        _voi_db(_dat)
    except Exception:  # noqa: BLE001 - an toan cuoi, khong duoc lam vo mot loi dang bay len
        log.warning("khong dat duoc trang thai loi o luot cuoi cho %s/%s",
                   owner_id, public_id, exc_info=True)


def _tao_tieng(params: dict, ctx=None) -> dict:
    """`ltt_voice.synthesize` — tạo tiếng nói từ văn bản."""
    from . import features, sidecar_client, tham_chieu, tu_dien_rieng

    yc = features.chuan_hoa(params)

    if not sidecar_client.san_sang():
        raise LoiGiongNoi(_t(
            "Máy tạo tiếng nói chưa được thiết lập trên máy chủ này "
            "(thiếu LTT_VOICE_SIDECAR_TOKEN)."))

    # 🔴 THÀNH PHẦN THỨ BA KHÔNG ĐƯỢC VỨT ĐI NỮA.
    #
    #    Trước 07/09/2026 dòng này là `ref_b64, preset, _ = ...`, và dấu gạch
    #    dưới ấy làm **cả chuỗi cảnh báo chết**: `lan_ngon_ngu.doi_chieu` được
    #    gọi ở cả hai nhánh của `giai_giong`, `KetQua` có sẵn trường `canh_bao`,
    #    `as_result()` có sẵn khoá `canh_bao` — và không có gì đi giữa hai đầu
    #    đó. Một đường ống đủ mọi khớp nối, không bao giờ có nước.
    #
    # ⛔ Và nó vừa thành thứ KHÔNG ĐƯỢC PHÉP chết: `lui_giong` báo qua đúng
    #    kênh này. Một đường lùi im lặng là chính cái lỗi mà `lui_giong.py`
    #    được viết ra để sửa — mất dòng cảnh báo là mất toàn bộ điểm của nó.
    ref_b64, preset, canh_bao = _voi_db(lambda db: features.giai_giong(db, yc))

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
    # ── TỪ ĐIỂN PHÁT ÂM RIÊNG CỦA KHÁCH ─────────────────────────────────────
    #
    # ⭐ `chuan_bi_van_ban(tu_dien_rieng=...)` nhận tham số này từ lâu, qua ba
    #    tầng xuống tới `tu_dien.ap_dung(them=...)` — và **không ai truyền**.
    #    Cả chuỗi ấy chưa từng chạy một lần nào cho tới 01/09/2026.
    #
    # 🔴 PHẢI Ở ĐÂY, trong worker, KHÔNG ở route. Public API đi thẳng xuống job
    #    và không qua route nào — đặt phép nạp này ở một cánh cửa thì cánh cửa
    #    kia không có nó, và khách gọi API sẽ nghe tên riêng của họ đọc sai
    #    trong khi trên web thì đúng. Cùng cái bẫy `features.py` cảnh báo.
    tu_rieng = _voi_db(lambda db: tu_dien_rieng.nhu_dict(db, yc.owner_id))         if yc.owner_id else {}
    chuan = features.chuan_bi_van_ban(yc, tran_moi_doan=TRAN_MOI_LUOT_SINH,
                                      tu_dien_rieng=tu_rieng)

    # ── TRẦN SAU CHUẨN HOÁ — chặn một lỗ KHUẾCH ĐẠI CHI PHÍ ─────────────────
    #
    # 🔴 `manifest._gia()` ước giá bằng `chuan_hoa(text)` **KHÔNG có từ điển
    #    riêng** — và nó không được phép có, vì nó chạy ở mọi lượt báo giá nên
    #    không được chạm CSDL (chú thích của chính nó nói vậy).
    #
    #    Nhưng worker thì CÓ áp từ điển. Hai bên đọc hai văn bản khác nhau, và
    #    khoảng cách ấy do khách kiểm soát:
    #
    #        do 01/09, trong pham vi tran hien tai (100 muc, `thay` <= 160):
    #          tho              1.499 ky tu   <- `_gia()` giu credit theo so nay
    #          sau tu dien    120.749 ky tu   <- worker doc so nay
    #          he so no          80,6x
    #
    #    Hệ quả không phải "thu thiếu": `credit_held` bé hơn thực tế làm phần
    #    quyết toán vượt phần giữ, và một lượt chạy đang giữa chừng bị đánh
    #    hỏng. Khách mất thời gian chờ để nhận một lỗi.
    #
    # ⭐ Trần đặt ở 3× độ dài thô: rộng gấp nhiều lần mọi phép nở thật (số →
    #    chữ nở ~3× **chỉ trên phần là số**; "LTT" → "e lờ tê tê" nở 3,3× chỉ
    #    trên ba ký tự), nhưng chặn dứt khoát ca 80×.
    #
    # ⛔ Ném `LoiGiongNoi` (= `LoiNguoiGoi`) chứ không phải lỗi hạ tầng: nền
    #    tảng KHÔNG thử lại, và credit đã giữ được hoàn. Một lỗi hạ tầng ở đây
    #    sẽ thử lại ba lần cho một thứ chắc chắn hỏng cả ba.
    _tran_sau = len(yc.text) * 3 + 200
    if len(chuan.da_chuan_hoa) > _tran_sau:
        raise LoiGiongNoi(_t(
            "Sau khi áp từ điển phát âm, văn bản dài {n} ký tự — vượt xa {t} "
            "ký tự cho phép. Hãy rút gọn một mục trong từ điển."
        ).format(n=len(chuan.da_chuan_hoa), t=_tran_sau))
    doan = chuan.doan or [yc.text]

    # ⛔ BẬN KHÔNG PHẢI HỎNG — để `DangBanTam` bay lên nguyên vẹn cho job_runner
    #    xếp lại. Bọc nó thành LoiGiongNoi ở đây là biến "máy đang bận" thành
    #    "job hỏng", và một job hỏng sẽ TRỪ CREDIT cho việc chưa từng chạy.
    job_id = str(getattr(ctx, "job_id", "") or "adhoc")

    # ── MỘT THƯ MỤC TẠM CHO CẢ LƯỢT, và mọi thứ dưới đây đi bằng ĐƯỜNG DẪN ──
    #
    # 🔴 Bản trước cầm `wav_bytes` từ lúc sinh tới lúc cất kho, và cầm hai bản
    #    cùng lúc trong lúc đổi tốc độ. Với bài 1.500 ký tự thì không ai thấy;
    #    với một cuốn sách thì đó là trần thật của sản phẩm, và nó chưa từng
    #    được khai ra ở đâu. Xem `ban_doc_dai` và `noi_dai.ghep_tep`.
    #
    # ⭐ Đường ngắn KHÔNG chậm đi vì việc này: nó vốn đã ghi ra một tệp tạm để
    #    đo thời lượng bằng ffprobe rồi xoá đi. Nay nó giữ đúng tệp ấy lại.
    with tempfile.TemporaryDirectory(prefix="lttvoice-") as thu_muc:
        if len(doan) > 1:
            from . import ban_doc_dai
            duong, ho_so = ban_doc_dai.dung(
                doan, thu_muc=thu_muc, owner_id=yc.owner_id or "",
                job_id=job_id, ref_b64=ref_b64, preset=preset, ctx=ctx)
            khai = ho_so.get("giay")
            # ⭐ `ban_doc_dai` cộng dồn `gen_s` của TỪNG lô. Đó là con số đúng:
            #    một bài dài là nhiều lượt GPU, và ta muốn tổng.
            gen_s = _so(ho_so.get("gen_s"))
        else:
            wav_bytes, headers = features.goi_cong(
                doan[0], ref_b64=ref_b64, preset=preset)
            duong = os.path.join(thu_muc, "tieng.wav")
            with open(duong, "wb") as f:
                f.write(wav_bytes)
            khai = headers.get("X-Duration-S")
            gen_s = _so(headers.get("X-Gen-S"))

        return _cat_kho(yc, duong, thu_muc, job_id=job_id, khai=khai,
                        chuan=chuan, so_doan=len(doan), ctx=ctx,
                        canh_bao=canh_bao, giong_that=preset, gen_s=gen_s)


def _so(x) -> float:
    """Header/hồ sơ -> `float`, và **không bao giờ ném**.

    ⛔ Đây là số liệu vận hành. Một sidecar bản cũ không trả `X-Gen-S`, và một
       `ValueError` ở đây sẽ đánh hỏng một lượt sinh **đã thành công** — biến
       một chỉ số thiếu thành một job hỏng và một khoản credit phải hoàn.
    """
    try:
        return max(0.0, float(x))
    except (TypeError, ValueError):
        return 0.0


def _cat_kho(yc, duong: str, thu_muc: str, *, job_id: str, khai, gen_s: float = 0.0,
             chuan, so_doan: int, ctx=None, canh_bao=(),
             giong_that: str = "") -> dict:
    """Đo, đổi tốc độ, cất kho. Tách ra vì thân `_tao_tieng` đã đủ dài.

    ⚠️ Nhận `duong` chứ không nhận `bytes`: đây là chỗ duy nhất còn chạm tới cả
       bản đọc, và nó phải chạm bằng tệp.
    """
    from platform_core.storage import get_storage

    from . import features, toc_do

    # Đo trên tệp thật, không tin header của sidecar. Header chỉ để đối chiếu.
    giay = _do_thoi_luong(duong)
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
        duong = toc_do.ap_dung_tep(duong, os.path.join(thu_muc, "nhanh.wav"),
                                   yc.toc_do)
        giay_phat = giay / toc_do.hop_le(yc.toc_do)

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
    # Luồng tệp, không `BytesIO`: `LocalStorage.put` chép bằng
    # `shutil.copyfileobj`, nên một handle là đủ và cả bản đọc không bao giờ
    # phải nằm trong bộ nhớ.
    with open(duong, "rb") as f:
        get_storage().put(khoa, f, content_type="audio/wav")

    # ⭐ `giong_that` chi khac `yc.preset` khi `giai_giong` DA LUI GIONG. Ghi
    #    lai o day de lich su tra loi duoc cau *"vi sao bai nay nghe khac"* —
    #    mot dong canh bao tren man hinh song het mot phien, ban ghi thi khong.
    ket = features.KetQua(
        yeu_cau=yc, audio_key=khoa, giay=giay, giay_phat=giay_phat,
        text_da_chuan_hoa=chuan.da_chuan_hoa, so_doan=so_doan,
        canh_bao=tuple(canh_bao or ()), giong_that=giong_that or "",
        gen_s=gen_s)

    if giay <= 0:
        log.warning("job %s: khong do duoc thoi luong -> thu 0 credit", job_id)

    return ket.as_result()


def _ghi_danh(params: dict, ctx=None) -> dict:
    """`ltt_voice.enroll` — clip tham chiếu -> biểu diễn giọng.

    ⭐ IDEMPOTENT theo **hash tệp nguồn**. Gửi lại đúng clip đó cho đúng giọng đó
       không tạo thêm biểu diễn và không thu thêm tiền: bảng `voice_ref` có ràng
       buộc DUY NHẤT `(profile_id, sha256)`, nên lần thứ hai đọc lại bản cũ.
    """
    from . import features, gia, giong_vong_doi, sidecar_client, tham_chieu

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

        def _dat_loi_dieu_kien(db):
            """`UPDATE ... WHERE trang_thai = 'dang_ghi_danh'` — dùng ở CẢ HAI
            nhánh `except` dưới đây (4xx vĩnh viễn của sidecar, và
            `LoiNguoiGoi` ném thẳng ra từ `sidecar_client.ghi_danh`). Điều
            kiện chặn worker ghi đè một hồ sơ đã bị THU HỒI giữa lúc job đang
            chạy — cùng lý do với UPDATE `active` ở `_ghi` bên dưới."""
            from .tables import VoiceProfile
            db.execute(
                VoiceProfile.__table__.update()
                .where(VoiceProfile.id == ho_so.id,
                      VoiceProfile.trang_thai == giong_vong_doi.TT_DANG_GHI_DANH)
                .values(trang_thai=giong_vong_doi.TT_LOI))

        try:
            kq = sidecar_client.ghi_danh(tmp.name, denoise=True)
        except sidecar_client.SidecarBan as e:
            raise DangBanTam(retry_after_s=e.retry_after_s) from e
        except sidecar_client.LoiSidecar as e:
            ma = int(getattr(e, "status", 0) or 0)
            if 400 <= ma < 500 and ma not in _HTTP_4XX_TAM_THOI:
                # 🔴 T-14 (review round 1, IMPORTANT 1-a): LỖI VĨNH VIỄN của
                #    chính CLIP — cổng đã ĐỌC ĐƯỢC yêu cầu (không phải
                #    5xx/mất mạng) và trả lời THẲNG "cái này sai" (4xx, vd
                #    422 clip không thoả điều kiện engine). Thử lại y hệt
                #    clip đó sẽ hỏng y hệt.
                #
                #    Trước bản vá này nhánh 4xx đi CHUNG đường với 5xx (dưới
                #    đây) — `LoiHaTang`, retryable — nên nền tảng cứ thử lại
                #    `SO_LAN_THU_JOB` lần cho một thứ chắc chắn hỏng cả
                #    `SO_LAN_THU_JOB` lần, rồi ÂM THẦM bỏ cuộc mà KHÔNG BAO
                #    GIỜ đặt `loi` — hồ sơ mắc kẹt VĨNH VIỄN ở `dang_ghi_danh`,
                #    và khách KHÔNG THỂ thu hồi nó (thu hồi bị chặn ở trạng
                #    thái đó, `giong_vong_doi._CHUYEN`).
                _voi_db(_dat_loi_dieu_kien)
                raise LoiGiongNoi(_t(
                    "Clip này không dùng được để ghi danh. Hãy tạo lại "
                    "giọng với một clip khác.")) from e
            # ⛔ `LoiHaTang`, KHÔNG phải `LoiGiongNoi` — cùng lỗi đã sửa ở
            #    `features._goi_va_dich_loi` (09b5ab6), và bản sửa đó BỎ SÓT chỗ
            #    này. `LoiGiongNoi` kế thừa `LoiNguoiGoi` nên nền tảng không thử
            #    lại, trong khi thông điệp hứa với khách là "vui lòng thử lại".
            #    Cổng giọng khởi động lại sau deploy (502/503), hay 408/409/429
            #    tạm thời ⇒ mọi lượt ghi danh đang bay phải được xếp lại, không
            #    hỏng vĩnh viễn.
            raise LoiHaTang(_t("Không ghi danh được giọng. Vui lòng thử lại.")) from e
        except LoiNguoiGoi:
            # 🔴 T-14: LỖI VĨNH VIỄN của chính YÊU CẦU (vd `LoiGiongNoi("clip
            #    hỏng")` ném THẲNG từ `sidecar_client.ghi_danh`, không qua
            #    `LoiSidecar` — khác nhánh 4xx ở trên) — không phải hạ tầng,
            #    thử lại sẽ hỏng y hệt. Trước bản vá này một hồ sơ hỏng kiểu
            #    này bị BỎ QUÊN mãi ở `dang_ghi_danh`, và `features.giai_giong`
            #    lặp lại câu *"chờ khoảng một phút rồi thử lại"* — một lời
            #    hứa không bao giờ thành (xem `TT_LOI` ở `giong_vong_doi.py`).
            _voi_db(_dat_loi_dieu_kien)
            raise
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
        from sqlalchemy import select

        from .tables import VoiceProfile, VoiceRepr
        r = VoiceRepr(profile_id=ho_so.id, ref_id=int(p.get("ref_id") or 0),
                      engine="vieneu",
                      model_repo=str(p.get("model_repo") or ""),
                      model_revision=str(p.get("model_revision") or ""),
                      sdk_version=str(p.get("sdk_version") or ""),
                      storage_key=khoa, fingerprint=vt,
                      trang_thai="dang_dung")
        db.add(r)
        db.flush()  # can `r.id` de tu phan biet dong VUA THEM voi cac dong khac
        # ⛔ Profile chỉ sang `active` SAU KHI có biểu diễn. Đảo thứ tự là để lại
        #    một giọng "dùng được" mà gọi tới thì không có gì để đọc.
        #
        # 🔴 T-07: CÓ ĐIỀU KIỆN — `WHERE ... AND trang_thai = 'dang_ghi_danh'`.
        #    Trước bản vá này, một khách THU HỒI giọng ĐANG được ghi danh (job
        #    còn chạy) và job đó về đích SAU cú thu hồi sẽ ghi đè `revoked`
        #    thành `active` — worker "bắt lại sống" đúng dữ liệu sinh trắc mà
        #    khách vừa yêu cầu xoá. `dang_ghi_danh` là trạng thái DUY NHẤT
        #    được phép nhảy sang `active` (`giong_vong_doi._CHUYEN`), nên
        #    khoá điều kiện UPDATE vào đúng nó chặn được cả lớp lỗi, không chỉ
        #    ca `revoked` — `rowcount == 0` cũng đúng nếu một job thứ hai (thử
        #    lại) đã từng chạy qua đây và đổi trạng thái trước job này.
        ket = db.execute(
            VoiceProfile.__table__.update()
            .where(VoiceProfile.id == ho_so.id,
                  VoiceProfile.trang_thai == giong_vong_doi.TT_DANG_GHI_DANH)
            .values(trang_thai=giong_vong_doi.TT_ACTIVE))
        if ket.rowcount == 0:
            # 🔴 review round 1, IMPORTANT 2: KHÔNG được kết luận "đã thu hồi"
            #    chỉ từ `rowcount == 0` — đó CŨNG chính là dấu vết của một
            #    LƯỢT THỬ LẠI của CHÍNH job này SAU KHI lượt trước đã kích
            #    hoạt xong (worker chết giữa chừng đâu đó SAU khi UPDATE
            #    `active` commit — vd lúc dựng tệp nghe thử ở đuôi hàm này).
            #    Đọc trạng thái THẬT trước khi kết luận.
            trang_hien = db.execute(
                select(VoiceProfile.trang_thai)
                .where(VoiceProfile.id == ho_so.id)).scalar_one_or_none()

            if trang_hien == giong_vong_doi.TT_ACTIVE:
                # THÀNH CÔNG IDEMPOTENT — không phải lỗi. `khoa` đặt tên theo
                # sha256 của chính biểu diễn (`tham_chieu.khoa_bieu_dien`), nên
                # một lượt thử lại SINH LẠI cùng embedding sẽ trùng khoá với
                # dòng `VoiceRepr` đã có. Dòng vừa `add()` ở trên khi đó là
                # THỪA — xoá nó (KHÔNG xoá `khoa` trong kho: dòng CŨ vẫn trỏ
                # tới đúng khoá đó). Embedding KHÔNG trùng (khoá khác) thì
                # dòng vừa thêm là một biểu diễn hợp lệ THỨ HAI — giữ lại,
                # không sai gì khi có nhiều `VoiceRepr` cùng `dang_dung`
                # (`tham_chieu.tim_repr_active` tự chọn dòng MỚI NHẤT).
                trung = db.execute(
                    select(VoiceRepr.id)
                    .where(VoiceRepr.profile_id == ho_so.id,
                          VoiceRepr.storage_key == khoa,
                          VoiceRepr.id != r.id)).scalar_one_or_none()
                if trung is not None:
                    db.delete(r)
                return r

            # revoked / loi / disabled: hồ sơ không còn muốn biểu diễn NÀY
            # nữa (thu hồi/đánh dấu lỗi/tắt xảy ra giữa lúc job đang chạy).
            # Kiểm TRƯỚC KHI LÙI: còn dòng CSDL nào khác (không phải dòng vừa
            # `add()` ở trên) trỏ tới đúng `khoa` này không — xoá một khoá mà
            # một dòng khác ĐANG SỐNG còn tham chiếu là làm mồ côi dòng đó.
            con_dung = db.execute(
                select(VoiceRepr.id)
                .where(VoiceRepr.profile_id == ho_so.id,
                      VoiceRepr.storage_key == khoa,
                      VoiceRepr.id != r.id)).scalar_one_or_none()
            # `db.rollback()` bỏ luôn `VoiceRepr` vừa `add()` ở trên — nó CHƯA
            # commit, nên lùi ở đây là an toàn và không để lại một dòng
            # `voice_repr` mồ côi.
            db.rollback()
            if con_dung is None:
                # KHÔNG dòng CSDL nào khác còn trỏ tới `khoa` — xoá an toàn.
                # Đây là TỆP THẬT trên đĩa/R2; rollback CSDL không đụng tới
                # nó. Best-effort: một `.npz` mồ côi là rác, không phải một
                # lỗi cho khách.
                try:
                    st.delete(khoa)
                except Exception:  # noqa: BLE001 - don duoc thi don, khong thi thoi
                    log.warning("khong xoa duoc khoa bieu dien mo coi %s", khoa,
                               exc_info=True)
            cau = {
                giong_vong_doi.TT_REVOKED: _t("Giọng này đã bị thu hồi."),
                giong_vong_doi.TT_LOI: _t(
                    "Giọng này đã được đánh dấu lỗi ở một lượt ghi danh khác."),
                giong_vong_doi.TT_DISABLED: _t(
                    "Giọng này đã bị tắt trong lúc ghi danh."),
            }
            raise LoiGiongNoi(cau.get(trang_hien, _t(
                "Giọng này không còn ở trạng thái ghi danh nữa.")))
        return r

    _voi_db(_ghi)

    # ── TỆP NGHE THỬ, dựng ngay ở ĐUÔI job ghi danh ─────────────────────────
    #
    # ⭐ ĐÚNG CHỖ NÀY, và lý do là kinh tế chứ không phải tiện tay: job này vừa
    #    giành GPU, vừa nạp model, và vừa có `ref_b64` trong tay. Một câu chào
    #    ba dòng thêm chưa tới hai giây vào một lượt đã chạy hàng chục giây.
    #
    #    Đẩy nó sang vòng bảo trì thì phải giành GPU **lần thứ hai**, nạp model
    #    **lần thứ hai**, và giữa hai lần đó khách nhìn thấy giọng vừa tạo của
    #    mình là giọng duy nhất trong danh sách không nghe thử được.
    #
    # ⛔ KHÔNG tính thêm tiền, và không được phép làm job hỏng: `nghe_thu.dung`
    #    nuốt mọi lỗi và trả `False`. Giọng đã ghi danh xong ở trên rồi — để một
    #    tệp nghe thử đánh hỏng nó là đánh đổi sai chiều.
    from . import nghe_thu
    nghe_thu.dung(nghe_thu.khoa_rieng(owner_id, public_id),
                  ref_b64=kq["ref_b64"])

    return {
        "voice_id": public_id,
        "fingerprint": vt,
        "emb_dim": kq.get("emb_dim"),
        "credit_cost": gia.CREDIT_GHI_DANH,
        "phien_ban_gia": gia.PHIEN_BAN_GIA,
        "chon_doan": chon,
    }
