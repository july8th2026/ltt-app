"""Handler job app `taoanh` — sinh ảnh từ prompt TỰ DO qua **LTT_IMAGE**.

🔴 DI TRÚ 09/09/2026 — AI CLEAN REBUILD V2 pha 06.2. Bản cũ tự dựng HTTP tới
   Gemini Image API, tự cấp khoá qua `api_pool` ở tầng app, và fallback
   `GEMINI_API_KEY`. Cả ba biến mất; đường mới đi qua
   `platform_core.image_gen.DieuPhoi` — cùng đường `anhnoibo` đang chạy.

## ⚠️ BA CHẾ ĐỘ BỊ GỠ, và đó là quyết định có bằng chứng

`taoanh` có năm chế độ; `hidream-o1` **khai** ba (`t2i` · `edit` · `subject`).
`semantic_inpaint`, `outpaint`, `style_transfer` không map được nên bị gỡ —
xem `_CHE_DO_MAP`. Chúng **không** được nguỵ trang thành `edit`.

## Hợp đồng handler giữ nguyên

Idempotent theo `job_id` · báo tiến độ qua `ctx` · NÉM khi thất bại để nền
tảng hoàn credit đã giữ. Khoá API chỉ ở máy chủ, và nay app **không giữ
khoá nào** — việc cấp khoá thuộc về nền tảng.
"""
from __future__ import annotations

from platform_core.i18n import _ as _t
from platform_core.public_api import costing

#: Bí danh công khai của model ảnh nhà. KHÔNG phải id nội bộ — id ấy nằm ở
#: `providers.REGISTRY` và chỉ được dịch **ngay trước khi ra khỏi nền tảng**.
_MODEL = "hidream-o1"

#: ⛔ CHẾ ĐỘ: `LTT_IMAGE` khai **ba** (`t2i` · `edit` · `subject`), `taoanh` có
#:    **năm**. Ba chế độ không map được — `semantic_inpaint`, `outpaint`,
#:    `style_transfer` — bị **GỠ**, không nguỵ trang thành `edit`.
#:
#: ⭐ Đây là NĂNG LỰC KHAI BÁO, không phải phỏng đoán:
#:      providers.REGISTRY["ltt_image"].models[0].capabilities["modes"]
#:        -> ['t2i', 'edit', 'subject']
#:    và `mode` được gửi thẳng xuống cổng, nên một giá trị lạ bị từ chối.
#:
#: ⛔ Ánh xạ chúng về `edit` kèm một câu chỉ dẫn sẽ **trông như** còn chạy, rồi
#:    trả về một tấm ảnh không đúng thứ khách xin. Pack nói rõ: *"feature
#:    LTT_IMAGE không hỗ trợ ⇒ disable/remove, không fallback."* Một tính năng
#:    hỏng lặng lẽ đắt hơn một tính năng bị gỡ tử tế.
_CHE_DO_MAP = {"generate": "t2i", "edit": "edit"}

#: `hidream-o1` khai `max_refs: 2`. Bản Gemini cho 8 — đó là năng lực của động
#: cơ CŨ, và giữ số 8 sau khi đổi động cơ là hứa một thứ không còn.
_MAX_REFS = 2


def _canvas_reference_keys(params: dict, owner_id: str) -> list[str]:
    """Normalise typed Canvas image inputs and enforce workflow ownership."""
    raw: list[object] = []
    if params.get("image_key"):
        raw.append(params["image_key"])
    raw.extend(list(params.get("image_keys") or []))
    keys: list[str] = []
    for value in raw:
        key = str(value or "").replace("\\", "/").strip("/")
        parts = key.split("/")
        if not owner_id or len(parts) < 3 or parts[1] != owner_id:
            raise ValueError(_t('Ảnh đầu vào không thuộc tài khoản đang chạy workflow.'))
        if key not in keys:
            keys.append(key)
    if len(keys) > 8:
        raise ValueError(_t('Một node Image chỉ nhận tối đa 8 ảnh tham chiếu.'))
    return keys


def _dieu_phoi():
    """Dựng bộ điều phối LTT_IMAGE. Tách ra để test tiêm được mà không chạm mạng."""
    from platform_core import providers
    from platform_core.image_gen import cong_render, dich_llm, dieu_phoi
    from platform_core.storage import get_storage

    prov = providers.get("ltt_image")
    base = getattr(prov, "base_url", "") if prov else ""
    if not base:
        # Fail-closed: chưa đặt `LTT_RENDER_BASE_URL` thì KHÔNG đoán bừa một địa chỉ.
        raise RuntimeError(_t(
            "Model nội bộ chưa được cấu hình trên máy chủ này "
            "(thiếu LTT_RENDER_BASE_URL)."))

    from platform_core.db import get_session

    def _voi_db(ham):
        gen = get_session(); db = next(gen)
        try:
            return ham(db)
        finally:
            try: next(gen)
            except StopIteration: pass

    def goi_llm(text, he_thong):
        return _voi_db(lambda db: dich_llm.goi_llm(text, he_thong, db=db))

    from platform_core.image_gen.http_cong import goi_http
    return dieu_phoi.DieuPhoi(cong=cong_render.CongRender(goi=goi_http(base)),
                              storage=get_storage(), goi_llm=goi_llm)


def handle(params: dict, ctx=None) -> dict:
    """Sinh 1–4 ảnh từ prompt tự do qua LTT_IMAGE; trả danh sách khoá ảnh."""
    from apps.taoanh.features import clean_mode
    from apps.taoanh.manifest import unit_credit
    from platform_core.image_gen import cong_render, dieu_phoi

    prompt = str(params.get("prompt", "")).strip()
    if not prompt:
        raise ValueError(_t('Chưa nhập mô tả ảnh (prompt).'))
    owner_id = str(params.get("owner_id", "")) or "unknown"
    job_id = getattr(ctx, "job_id", "") or "adhoc"
    try:
        count = max(1, min(int(params.get("count", 1)), 4))
    except (TypeError, ValueError):
        count = 1

    # ⛔ CHẾ ĐỘ KHÔNG MAP ĐƯỢC THÌ TỪ CHỐI CÓ TÊN, không âm thầm hạ về `edit`.
    #    Một tính năng hỏng lặng lẽ đắt hơn một tính năng bị gỡ tử tế: khách sẽ
    #    nhận về một tấm ảnh trông hợp lý mà không phải thứ họ xin.
    che_do_cu = clean_mode(str(params.get("edit_mode") or "generate"))
    if che_do_cu not in _CHE_DO_MAP:
        raise ValueError(_t(
            'Chế độ "{ten}" không còn được hỗ trợ. Model nội bộ nhận: tạo mới '
            'và chỉnh sửa.').format(ten=che_do_cu))
    che_do = _CHE_DO_MAP[che_do_cu]

    ref_keys = _canvas_reference_keys(params, owner_id)
    for spec in list(params.get("references") or [])[:_MAX_REFS]:
        khoa = str(spec.get("key") or "")
        if not khoa.startswith(f"taoanh/{owner_id}/"):
            raise ValueError(_t('Ảnh tham chiếu không hợp lệ hoặc không thuộc người dùng.'))
        if khoa not in ref_keys:
            ref_keys.append(khoa)
    if len(ref_keys) > _MAX_REFS:
        # ⚠️ Trần này là NĂNG LỰC KHAI BÁO của `hidream-o1` (`max_refs: 2`), không
        #    phải một con số ta chọn. Bản Gemini cho 8; giữ số 8 sau khi đổi động
        #    cơ là hứa một thứ không còn.
        raise ValueError(_t(
            'Model nội bộ nhận tối đa {n} ảnh tham chiếu.').format(n=_MAX_REFS))
    if che_do != "t2i" and not ref_keys:
        raise ValueError(_t('Chế độ chỉnh sửa cần ảnh nguồn.'))

    dp = _dieu_phoi()
    if ctx is not None:
        ctx.progress(10, "đang chuẩn bị")
    try:
        kq = dp.chay(job_id=str(job_id), prompt=prompt, model=_MODEL,
                     mode=che_do, ref_keys=ref_keys, so_anh=count,
                     tien_to_khoa=f"taoanh/{owner_id}")
    except cong_render.BanError as e:
        # ⛔ Máy bận KHÔNG phải "thất bại". Ném `DangBan` của nền tảng để job về
        #    hàng đợi (`resource_wait`) — không tiêu một lượt thử, không chạm
        #    tiền. Ném `RuntimeError` ở đây sẽ tiêu ba lượt rồi hỏng job kèm
        #    hoàn tiền cho một việc CHƯA TỪNG CHẠY.
        from platform_core.jobs import DangBan
        eta = getattr(e, "eta_s", 0) or 0
        phut = int(eta / 60)
        raise DangBan(
            _t("Máy tạo ảnh đang bận{them}. Bạn có thể thử lại sau.").format(
                them=_t(" — còn khoảng {p} phút").format(p=phut) if phut else ""),
            retry_after_s=eta) from e
    except dieu_phoi.DieuPhoiError as e:
        raise RuntimeError(str(e)) from e

    keys = list(kq.image_keys)
    if not keys:
        raise RuntimeError(_t('Không tạo được ảnh nào.'))
    if ctx is not None:
        ctx.progress(100, "xong")

    # 🔴 TÍNH TIỀN THEO ẢNH THẬT SỰ NHẬN ĐƯỢC, không theo số đã xin.
    return {"image_keys": keys, "count": len(keys), "prompt": prompt,
            "prompt_da_gui": kq.prompt_da_gui, "da_dich": kq.da_dich,
            "edit_mode": che_do_cu,
            "credit_cost": len(keys) * unit_credit(_MODEL), "errors": [],
            costing.KHOA_GOI_PROVIDER: [{"model": _MODEL, "count": len(keys)}]}
