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

⚠️ KHÔNG giữ một phiên CSDL suốt cả job. Một lượt vẽ có thể mất 15 phút; giữ
   transaction mở suốt thời gian đó là giữ khoá CSDL trong lúc chờ mạng. Mọi lần
   chạm CSDL ở đây đều đi qua `_voi_db()` — mở ngắn, commit, đóng.
"""
from __future__ import annotations

import logging

from platform_core.i18n import _ as _t

log = logging.getLogger(__name__)

MAX_REF = 2


class LoiTaoAnh(Exception):
    """Lỗi hiện cho người dùng. Không kèm chi tiết hạ tầng."""


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


def _kiem_chu_so_huu(khoa: str, owner_id: str) -> str:
    """Khoá lưu trữ có dạng `{app}/{user_id}/{job_id}/...`.

    Kiểm **đoạn thứ hai**, không phải tiền tố app: ảnh tham chiếu hợp lệ có thể là
    artifact của một job trước ở app khác của **cùng người dùng đó**.
    """
    phan = str(khoa or "").strip("/").split("/")
    if len(phan) < 2 or phan[1] != owner_id:
        raise LoiTaoAnh(_t('Ảnh tham chiếu không thuộc người dùng hiện tại.'))
    return khoa


def _dieu_phoi():
    """Dựng bộ điều phối. Tách ra để test tiêm được mà không chạm mạng."""
    from platform_core import providers
    from platform_core.image_gen import cong_render, dich_gemini, dieu_phoi
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
        return _voi_db(lambda db: dich_gemini.goi_gemini(text, he_thong, db=db))

    return dieu_phoi.DieuPhoi(cong=cong_render.CongRender(goi=goi_http(base)),
                              storage=get_storage(), goi_llm=goi_llm)


def handle(params: dict, ctx=None) -> dict:
    prompt = str(params.get("prompt") or "").strip()
    if not prompt:
        raise LoiTaoAnh(_t('Chưa nhập mô tả ảnh.'))

    che_do = str(params.get("mode") or "t2i")
    if che_do not in ("t2i", "edit", "subject"):
        raise LoiTaoAnh(_t('Chế độ không hợp lệ: {ten}').format(ten=che_do))

    # `owner_id` den tu params, KHONG tu ctx — JobContext khong mang no.
    owner_id = str(params.get("owner_id") or "").strip()

    # Gom hai đường vào một: `image_key` (đường API, một ảnh) và `image_keys`
    # (đường giao diện, tối đa hai). Xem chú thích ở manifest vì sao có hai.
    refs = [str(k) for k in (params.get("image_keys") or []) if str(k).strip()]
    mot = str(params.get("image_key") or "").strip()
    if mot and mot not in refs:
        refs.insert(0, mot)

    if che_do in ("edit", "subject") and not refs:
        raise LoiTaoAnh(_t('Chế độ này cần ít nhất một ảnh tham chiếu.'))
    if che_do == "t2i" and refs:
        raise LoiTaoAnh(_t('Chế độ t2i không nhận ảnh tham chiếu.'))
    if len(refs) > MAX_REF:
        # Khong tu cat bot: cat bot la lang le giao mot thu khac thu khach yeu cau.
        raise LoiTaoAnh(_t('Tối đa {n} ảnh tham chiếu.').format(n=MAX_REF))
    if refs and not owner_id:
        # Khong biet chu so huu thi khong kiem duoc quyen — tu choi, dung doan.
        raise LoiTaoAnh(_t('Thiếu thông tin người dùng để kiểm ảnh tham chiếu.'))
    refs = [_kiem_chu_so_huu(k, owner_id) for k in refs]

    try:
        so_anh = max(1, min(int(params.get("count", 1)), 4))
    except (TypeError, ValueError):
        so_anh = 1

    from platform_core.image_gen import cong_render, dieu_phoi

    dp = _dieu_phoi()
    try:
        kq = dp.chay(job_id=str(getattr(ctx, "job_id", "") or "adhoc"),
                     prompt=prompt, mode=che_do, ref_keys=refs, so_anh=so_anh,
                     negative_prompt=str(params.get("negative_prompt") or ""),
                     tien_to_khoa=f"anhnoibo/{owner_id or 'chung'}")
    except cong_render.BanError as e:
        # ⛔ KHONG bao "that bai". May dang ban la trang thai binh thuong.
        phut = int((e.eta_s or 0) / 60)
        raise LoiTaoAnh(
            _t("Máy tạo ảnh đang bận{them}. Bạn có thể thử lại sau, hoặc chọn "
               "model đám mây.").format(
                   them=_t(" — còn khoảng {p} phút").format(p=phut) if phut else "")
        ) from e
    except dieu_phoi.DieuPhoiError as e:
        raise LoiTaoAnh(str(e)) from e

    from platform_core.public_api import costing

    return {"image_keys": list(kq.image_keys), "prompt": kq.prompt_da_gui,
            "da_dich": kq.da_dich, "canh_bao": list(kq.canh_bao),
            # Model nhà cũng có giá vốn — điện + khấu hao GPU, đo thật trên máy B.
            # `tham_chieu` đắt gấp đôi, nên phải báo cả nó chứ không chỉ số ảnh.
            costing.KHOA_GOI_PROVIDER: [
                {"model": "hidream-o1", "count": len(kq.image_keys),
                 "tham_chieu": che_do in ("edit", "subject")}]}
