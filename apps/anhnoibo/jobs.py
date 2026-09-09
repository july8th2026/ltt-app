"""
jobs.py — handler chạy trong worker cho `anhnoibo.generate`.

⭐ Handler này **mỏng có chủ ý**: mọi việc thật nằm ở `platform_core/image_gen/`.
   App chỉ đọc tham số, kiểm quyền, gọi bộ điều phối, và dịch lỗi thành thứ khách
   đọc được.

⛔ BẬN KHÔNG PHẢI HỎNG. Máy B dùng chung GPU với dự án video. `BanError` phải ra
   thành một thông điệp nói rõ *"máy đang bận, còn khoảng N phút"* — không phải
   "tạo ảnh thất bại". Hai câu đó dẫn tới hai hành động khác hẳn của khách, và một
   job bị coi là hỏng sẽ **trừ credit** cho một việc chưa từng chạy.

⛔ ẢNH THAM CHIẾU PHẢI THUỘC ĐÚNG NGƯỜI DÙNG. Khoá lưu trữ là chuỗi khách gửi lên;
   không kiểm thì khách A đọc được ảnh của khách B chỉ bằng cách đoán khoá.
   `apps/thumbnail/jobs.py` đã kiểm đúng như vậy — đây không phải sáng kiến riêng.

⛔ NGHIỆP VỤ KHÔNG Ở ĐÂY NỮA — nó ở `features.py` (H37/L6). File này chỉ còn:
   gọi kiểm tham số, dựng bộ điều phối, dịch lỗi hạ tầng thành câu chữ khách đọc
   được. Lý do: `jobs.py` là **một cánh cửa**, và quy tắc nghiệp vụ nằm trong một
   cánh cửa thì cửa thứ hai phải chép lại. Hai bản chép sẽ lệch nhau.

⚠️ KHÔNG giữ một phiên CSDL suốt cả job. Một lượt vẽ có thể mất 15 phút; giữ
   transaction mở suốt thời gian đó là giữ khoá CSDL trong lúc chờ mạng. Mọi lần
   chạm CSDL ở đây đều đi qua `_voi_db()` — mở ngắn, commit, đóng.
"""
from __future__ import annotations

import logging

from platform_core.i18n import _ as _t
from platform_core.jobs import DangBan

from .features import LoiTaoAnh  # noqa: F401  (giữ tên cũ cho chỗ đang import)

log = logging.getLogger(__name__)


def _dang_ban(eta_s) -> DangBan:
    """Dựng tín hiệu BẬN của nền tảng, giữ nguyên câu chữ khách đọc được.

    `eta_s` rỗng = cổng **không biết** còn bao lâu; không đoán số phút, và để
    `retry_after_s` rỗng cho nền tảng dùng giãn cách mặc định.
    """
    phut = int((eta_s or 0) / 60)
    return DangBan(
        _t("Máy tạo ảnh đang bận{them}. Bạn có thể thử lại sau, hoặc chọn "
           "model đám mây.").format(
               them=_t(" — còn khoảng {p} phút").format(p=phut) if phut else ""),
        retry_after_s=eta_s)


def _xep_lai_neu_may_ban(cong) -> None:
    """Hỏi `/health` của cổng render; máy bận thì ném `DangBan` NGAY.

    ⛔ Cổng **không trả lời** thì KHÔNG coi là bận — để đường thường đi tiếp và
       hỏng như một lỗi hạ tầng (có đếm lượt thử). "Bận" xếp lại vô hạn; một
       cổng đã chết mà xếp lại vô hạn là job nằm `queued` mãi không ai được báo.
    `cong` rỗng (bộ điều phối giả trong test) ⇒ bỏ qua.
    """
    if cong is None:
        return
    from platform_core.image_gen import cong_render
    try:
        h = cong.health() or {}
    except cong_render.CongRenderError as e:
        log.info("khong hoi duoc /health cong render, di duong thuong: %s", e)
        return
    if h.get("busy"):
        raise _dang_ban(h.get("eta_s"))


def _voi_db(ham):
    """Chạy `ham(db)` trong một phiên CSDL NGẮN rồi đóng ngay.

    Không dùng `ctx.db`: `JobContext` **không có** thuộc tính đó. Nó chỉ cấp
    `job_id`/`gpu_uuid`/`progress()` — mọi thứ khác app tự lấy.
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


def _dieu_phoi():
    """Dựng bộ điều phối. Tách ra để test tiêm được mà không chạm mạng."""
    from platform_core import providers
    from platform_core.image_gen import cong_render, dich_llm, dieu_phoi
    from platform_core.storage import get_storage

    prov = providers.get("ltt_image")
    base = getattr(prov, "base_url", "") if prov else ""
    if not base:
        # Fail-closed: chua dat LTT_RENDER_BASE_URL thi khong doan bua mot dia chi.
        raise LoiTaoAnh(_t(
            "Model nội bộ chưa được cấu hình trên máy chủ này "
            "(thiếu LTT_RENDER_BASE_URL)."))

    from .http_cong import goi_http

    def goi_llm(text, he_thong):
        return _voi_db(lambda db: dich_llm.goi_llm(text, he_thong, db=db))

    return dieu_phoi.DieuPhoi(cong=cong_render.CongRender(goi=goi_http(base)),
                              storage=get_storage(), goi_llm=goi_llm)


def handle(params: dict, ctx=None) -> dict:
    from platform_core.image_gen import cong_render, dieu_phoi

    from . import features

    yc = features.chuan_hoa(params)

    dp = _dieu_phoi()
    # ⭐ HỎI BẬN TRƯỚC KHI DỊCH PROMPT. `DieuPhoi.chay` dịch prompt (một lượt
    #    Gemini có tính tiền) RỒI mới gửi máy B — nên khi máy B bận cả giờ, mỗi
    #    lần job quay lại từ hàng đợi là một lượt dịch nữa cho cùng một câu.
    #    `cong.health()` là một GET trong LAN; hỏi trước thì lượt bận không tốn
    #    gì ngoài chính lượt hỏi. Không thay được `except BanError` bên dưới:
    #    giữa lúc hỏi và lúc gửi, dự án video có thể vừa bắt đầu một lượt.
    _xep_lai_neu_may_ban(getattr(dp, "cong", None))
    try:
        kq = dp.chay(job_id=str(getattr(ctx, "job_id", "") or "adhoc"),
                     prompt=yc.prompt, mode=yc.che_do, ref_keys=list(yc.ref_keys),
                     so_anh=yc.so_anh, negative_prompt=yc.negative_prompt,
                     tien_to_khoa=f"anhnoibo/{yc.owner_id or 'chung'}")
    except cong_render.BanError as e:
        # ⛔ KHONG bao "that bai". May dang ban la trang thai binh thuong —
        #    va no phai la `DangBan` cua NEN TANG, khong phai `LoiTaoAnh`:
        #    `LoiTaoAnh` roi vao nhanh `retry`, tieu mot luot thu, va sau ba
        #    luot ban thi job HONG kem hoan tien cho mot viec chua tung chay
        #    (do o Phase 02 H43). `DangBan` -> `resource_wait`: ve hang doi,
        #    khong tinh luot, khong cham tien.
        raise _dang_ban(e.eta_s) from e
    except dieu_phoi.DieuPhoiError as e:
        raise LoiTaoAnh(str(e)) from e

    # 🔴 TÍNH TIỀN THEO ẢNH THẬT SỰ NHẬN ĐƯỢC, KHÔNG THEO SỐ ĐÃ XIN.
    #    `KetQua.as_result()` lo phần đó — xem `features.KetQua.gia_that_credit`.
    ket = features.KetQua(yeu_cau=yc, image_keys=tuple(kq.image_keys),
                          prompt_da_gui=kq.prompt_da_gui, da_dich=kq.da_dich,
                          canh_bao=tuple(kq.canh_bao))
    if ket.so_anh_that < yc.so_anh:
        log.warning("job %s: xin %d anh, nhan %d — tinh tien theo %d",
                    getattr(ctx, "job_id", "?"), yc.so_anh,
                    ket.so_anh_that, ket.so_anh_that)
    return ket.as_result()
