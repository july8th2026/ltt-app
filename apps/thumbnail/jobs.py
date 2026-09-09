"""Handler job app `thumbnail` — sinh thumbnail YouTube qua **LTT_IMAGE**.

🔴 DI TRÚ 09/09/2026 — AI CLEAN REBUILD V2 pha 06.3. Bản cũ tự dựng HTTP tới
   Gemini Image API, tự cấp khoá qua `api_pool` ở tầng app, và fallback
   `GEMINI_API_KEY`. Cả ba biến mất; đường mới đi qua
   `platform_core.image_gen.DieuPhoi` — cùng đường `anhnoibo` và `taoanh` chạy.

## 🔴 CHỮ TRONG ẢNH BỊ GỠ. Đây là mục quan trọng nhất của tệp này.

App này sinh ra để **viết chữ tiếng Việt lên ảnh**: tiêu đề, phụ đề, một nhóm
`text_style` sáu kiểu chữ, một nhóm `ngon_ngu` năm thứ tiếng mà mỗi mẩu đều mở
đầu bằng *"All text on the thumbnail MUST be written in…"*. Model nhà **không
làm được việc đó**, và điều ấy không phải phỏng đoán của tôi:

    providers.REGISTRY["ltt_image"].models[0].capabilities["canh_bao"]
      -> "chữ tiếng Việt CÓ DẤU vẽ trong ảnh bị sai dấu"

    D-048 (chủ sản phẩm, 24/08/2026): "HiDream không hỗ trợ tiếng Việt trong
    ảnh, tôi cũng không cần." … "Nếu sau này có khách hỏi tool sinh ảnh có chữ,
    câu trả lời là Gemini, và đó là câu trả lời cuối cùng."

⛔ Chiến dịch này xoá Gemini — tức xoá đúng câu trả lời mà D-048 đã chỉ định.
   Không có động cơ nào khác biết viết chữ. Nên **tính năng chữ-trong-ảnh bị gỡ**,
   không bị nguỵ trang: `title`/`subtitle` có nội dung thì handler **từ chối có
   tên**, và hai nhóm lựa chọn về chữ đã bị xoá khỏi sản phẩm.

⭐ Vì sao không "cứ vẽ, được đến đâu hay đến đó": bốn thứ tiếng còn lại **chưa
   ai đo**, và thứ tiếng duy nhất đã đo thì hỏng. Luật của chính khối
   `capabilities` ngay trên là *"CHỈ khai thứ ĐÃ ĐO THẬT"*. Bán một năng lực
   chưa đo là hứa một thứ ta không biết mình có.

Toàn văn cân nhắc + lối mở lại: `docs/AI_CLEAN_REBUILD/PHA06_THUMBNAIL_CHU.md`.

## Hợp đồng handler giữ nguyên

Idempotent theo `job_id` · báo tiến độ qua `ctx` · NÉM khi thất bại để nền tảng
hoàn credit đã giữ. Khoá API chỉ ở máy chủ, và nay app **không giữ khoá nào**.
"""
from __future__ import annotations

import pathlib

from platform_core.i18n import _ as _t
from platform_core.public_api import costing

#: Bí danh công khai của model ảnh nhà. KHÔNG phải id nội bộ.
_MODEL = "hidream-o1"

_PROMPTS_DIR = pathlib.Path(__file__).resolve().parent / "prompts"

#: Nhóm lựa chọn CÒN SỐNG. `text_style` và `ngon_ngu` đã bị gỡ cùng với
#: chữ-trong-ảnh — xem khối đầu tệp. Giao diện đọc danh sách này.
NHOM_LUA_CHON: tuple[str, ...] = ("phong_cach", "kieu_trend")

#: Thumbnail chỉ có MỘT ảnh tham chiếu ("remix từ output đã chọn"), nên trần 1 —
#: dưới `max_refs: 2` mà `hidream-o1` khai. Đây là trần của **sản phẩm**, không
#: phải của model, và nó không được vượt qua trần model.
_MAX_REFS = 1


def build_prompt(topic: str, *, phong_cach: str = "", kieu_trend: str = "",
                 aspect_ratio: str = "16:9", brand: dict | None = None) -> str:
    """Ghép prompt thumbnail TỪ FRAGMENT (không hardcode chuỗi prompt).

    🔴 Bốn tham số đã biến mất ở pha 06.3: `title`, `subtitle`, `text_style`,
       `ngon_ngu`. Cả bốn chỉ phục vụ **chữ vẽ trong ảnh** — thứ model nhà không
       làm được. Giữ chúng lại và im lặng bỏ qua sẽ tệ hơn: chỗ gọi vẫn truyền,
       vẫn tin là có tác dụng, và không ai biết đến ngày nhìn tấm ảnh.

    Lựa chọn rỗng/không hợp lệ → lấy mặc định (mục đầu trong `_labels.json`).
    """
    from platform_core import prompt_fragments as pf

    d = _PROMPTS_DIR
    phong_cach = phong_cach or pf.default_option(d, "phong_cach")
    kieu_trend = kieu_trend or pf.default_option(d, "kieu_trend")
    mapping = {
        "aspect_ratio": aspect_ratio,
        "user_input": topic.strip(),
        "phong_cach_style": pf.read_fragment(d, "phong_cach", phong_cach),
        "kieu_trend_layout": pf.read_fragment(d, "kieu_trend", kieu_trend),
    }
    from apps.thumbnail.features import brand_directive
    prompt = pf.build(d, mapping)
    directive = brand_directive(brand)
    return f"{prompt}\n\n{directive}" if directive else prompt


def _dieu_phoi():
    """Dựng bộ điều phối LTT_IMAGE. Tách ra để test tiêm được mà không chạm mạng."""
    from platform_core import providers
    from platform_core.db import get_session
    from platform_core.image_gen import cong_render, dich_llm, dieu_phoi
    from platform_core.image_gen.http_cong import goi_http
    from platform_core.storage import get_storage

    prov = providers.get("ltt_image")
    base = getattr(prov, "base_url", "") if prov else ""
    if not base:
        # Fail-closed: chưa đặt `LTT_RENDER_BASE_URL` thì KHÔNG đoán bừa địa chỉ.
        raise RuntimeError(_t(
            "Model nội bộ chưa được cấu hình trên máy chủ này "
            "(thiếu LTT_RENDER_BASE_URL)."))

    def _voi_db(ham):
        gen = get_session(); db = next(gen)
        try:
            return ham(db)
        finally:
            try: next(gen)
            except StopIteration: pass

    def goi_llm(text, he_thong):
        return _voi_db(lambda db: dich_llm.goi_llm(text, he_thong, db=db))

    return dieu_phoi.DieuPhoi(cong=cong_render.CongRender(goi=goi_http(base)),
                              storage=get_storage(), goi_llm=goi_llm)


def _cham(storage, key: str) -> dict:
    """Điểm kỹ thuật của một ảnh — đọc lại từ lưu trữ.

    ⚠️ Đường Gemini cũ có sẵn bytes trong tay; đường này thì máy B tải thẳng lên
       R2 nên phải đọc về. Một lượt GET cho mỗi ảnh, cạnh một lượt vẽ 58–190
       giây — không đáng để bỏ một tính năng đang hiển thị trên giao diện.

    Chấm hỏng KHÔNG được làm hỏng job: ảnh đã vẽ xong và đã tính tiền.
    """
    from apps.thumbnail.features import technical_score
    try:
        with storage.open(key) as stream:
            return technical_score(stream.read())
    except Exception:  # noqa: BLE001 — chấm điểm là phụ, sinh ảnh mới là chính
        return {"score": None, "method": "unavailable"}


def handle(params: dict, ctx=None) -> dict:
    """Sinh 1–4 thumbnail qua LTT_IMAGE, trả về danh sách khoá ảnh."""
    from platform_core.image_gen import cong_render, dieu_phoi
    from platform_core.image_gen import gia as GIA
    from platform_core.storage import get_storage

    topic = str(params.get("topic", "")).strip()
    if not topic:
        raise ValueError(_t('Chưa nhập chủ đề thumbnail.'))

    # ⛔ CHỮ TRONG ẢNH: TỪ CHỐI CÓ TÊN, không âm thầm bỏ qua.
    #    Bỏ qua im lặng thì khách gõ tiêu đề, trả tiền, rồi nhận về một tấm ảnh
    #    không có chữ nào — và không có gì trong hệ thống nói cho họ vì sao.
    for khoa in ("title", "subtitle"):
        if str(params.get(khoa) or "").strip():
            raise ValueError(_t(
                'Model nội bộ không vẽ được chữ trong ảnh. Hãy để trống tiêu đề '
                'và phụ đề, rồi thêm chữ bằng công cụ chỉnh sửa của bạn.'))

    brand = params.get("brand") if isinstance(params.get("brand"), dict) else {}
    aspect_ratio = str(params.get("aspect_ratio", "16:9")) or "16:9"
    owner_id = str(params.get("owner_id", "")) or "unknown"
    job_id = str(getattr(ctx, "job_id", "") or "adhoc")
    try:
        count = max(1, min(int(params.get("count", 1)), 4))
    except (TypeError, ValueError):
        count = 1

    # Ảnh tham chiếu PHẢI thuộc đúng người dùng — khoá lưu trữ là chuỗi khách gửi
    # lên; không kiểm thì khách A đọc được ảnh của khách B chỉ bằng cách đoán khoá.
    ref_keys: list[str] = []
    reference_key = str(params.get("reference_key") or "")
    if reference_key:
        if not reference_key.startswith(f"thumbnail/{owner_id}/"):
            raise ValueError(_t('Ảnh tham chiếu không thuộc người dùng hiện tại.'))
        ref_keys.append(reference_key)
    if len(ref_keys) > _MAX_REFS:
        raise ValueError(_t(
            'Chỉ dùng được tối đa {n} ảnh tham chiếu.').format(n=_MAX_REFS))

    # Không ảnh tham chiếu → `t2i`. Có → `edit`: giao diện gọi việc này là *"remix
    # từ output đã chọn"*, và `edit` đúng là "biến đổi ảnh này theo mô tả kia".
    che_do = "edit" if ref_keys else "t2i"

    storage = get_storage()
    prompt = build_prompt(topic,
                          phong_cach=str(params.get("phong_cach", "")),
                          kieu_trend=str(params.get("kieu_trend", "")),
                          aspect_ratio=aspect_ratio, brand=brand)

    # 🔁 RESUME. Worker chết giữa chừng rồi job bị thu hồi: ảnh đã lưu vẫn nằm đó.
    #    `DieuPhoi` cấp khoá theo đúng khuôn `{tiền tố}/{job_id}/{i}.png`, nên
    #    đoán lại được. Đủ cả lô thì KHÔNG vẽ lần nữa — không đốt lại GPU.
    khoa_du_kien = [f"thumbnail/{owner_id}/{job_id}/{i}.png" for i in range(count)]
    if all(storage.exists(k) for k in khoa_du_kien):
        keys, prompt_da_gui, da_dich = khoa_du_kien, prompt, False
    else:
        dp = _dieu_phoi()
        if ctx is not None:
            ctx.progress(10, "đang chuẩn bị")
        try:
            kq = dp.chay(job_id=job_id, prompt=prompt, model=_MODEL, mode=che_do,
                         ref_keys=ref_keys, so_anh=count, ti_le=aspect_ratio,
                         tien_to_khoa=f"thumbnail/{owner_id}")
        except cong_render.BanError as e:
            # ⛔ Máy bận KHÔNG phải "thất bại". `DangBan` đưa job về hàng đợi
            #    (`resource_wait`): không tiêu một lượt thử, không chạm tiền.
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
        prompt_da_gui, da_dich = kq.prompt_da_gui, kq.da_dich

    if not keys:
        raise RuntimeError(_t('Không tạo được ảnh nào.'))
    if ctx is not None:
        ctx.progress(100, "xong")

    # 🔴 TÍNH TIỀN THEO ẢNH THẬT SỰ NHẬN ĐƯỢC, và theo BẢNG GIÁ CỦA MODEL NHÀ —
    #    cùng một hàm `anhnoibo` và `taoanh` gọi, nên cùng model không hai giá.
    return {"image_keys": keys, "scores": [_cham(storage, k) for k in keys],
            "count": len(keys), "prompt": prompt, "aspect_ratio": aspect_ratio,
            "prompt_da_gui": prompt_da_gui, "da_dich": da_dich,
            "phien_ban_gia": GIA.PHIEN_BAN_GIA,
            "credit_cost": GIA.tinh(so_anh=len(keys), che_do=che_do),
            "errors": [],
            costing.KHOA_GOI_PROVIDER: [{"model": _MODEL, "count": len(keys)}]}
