"""
test_253 — app `anhnoibo` bán model ảnh nội bộ ra `/api/v1`. (H37/A9)

Không mạng, không GPU, không CSDL.

Mỗi test ở đây chốt một thứ mà **nếu sai thì hệ thống vẫn chạy** — và đó chính là
lý do phải có test: job vẫn chạy, tiền vẫn trừ, chỉ là trừ sai hoặc giao sai hàng.
"""
from __future__ import annotations

import os

import pytest

from platform_core import registry


def _app():
    for a in registry.discover():
        if a.slug == "anhnoibo":
            return a
    pytest.fail("khong tim thay app anhnoibo")


def _tool():
    app = _app()
    assert not app.error, f"app khong nap duoc: {app.error}"
    return app.manifest.tools[0]


def _catalog(bien_tool: str):
    """Dựng catalog công khai với đúng một biến môi trường được đặt."""
    from platform_core.public_api import catalog
    from platform_core.public_api.config import load_public_api_config

    cu = {k: os.environ.get(k) for k in ("LTT_PUBLIC_API", "LTT_PUBLIC_API_TOOLS")}
    os.environ["LTT_PUBLIC_API"] = "1"
    os.environ["LTT_PUBLIC_API_TOOLS"] = bien_tool
    try:
        return catalog.build_catalog(load_public_api_config(), registry.discover())
    finally:
        for k, v in cu.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


# ───────────────────────── app nạp được, không đụng ai ──────────────────────
def test_app_nap_duoc_va_khong_trung_gi_voi_app_dang_chay():
    app = _app()
    assert not app.error, app.error
    khac = [a for a in registry.discover() if a.slug != "anhnoibo" and not a.error]
    ten_cu = {t.name for a in khac for t in a.manifest.tools}
    assert "image.ltt" not in ten_cu
    assert "anhnoibo.generate" not in {j for a in khac for j in a.manifest.job_types}


def test_khong_doi_mot_dong_nao_cua_taoanh_va_thumbnail():
    """⛔ Ràng buộc của cả hạng mục: model nội bộ được **thêm vào**, không phải
    thay thế. `taoanh`/`thumbnail` đang phục vụ khách trả tiền qua Gemini."""
    for slug in ("taoanh", "thumbnail"):
        a = [x for x in registry.discover() if x.slug == slug][0]
        assert not a.error, f"{slug} hong: {a.error}"
        for t in a.manifest.tools:
            nha = t.params_schema.get("model", {}).get("providers")
            assert nha == ["gemini"], (
                f"{slug}/{t.name} da bi doi provider thanh {nha} — hang muc nay "
                "chi DUNG, khong doi Gemini")


# ═══════════ fail-closed: ba cổng độc lập, thiếu một là không ra ════════════
def test_bat_API_ma_khong_khai_ten_tool_thi_KHONG_ra():
    """Q92 fail-closed. Bật cờ một mình không mở tool nào."""
    assert [t for t in _catalog("") if t.name == "image.ltt"] == []


def test_khai_dung_ten_thi_moi_ra():
    assert [t for t in _catalog("image.ltt") if t.name == "image.ltt"]


def test_api_exposed_khong_tu_dong_mo_cua():
    """`api_exposed=True` là *cho phép*, không phải *đang mở*. Nhầm hai thứ này là
    tưởng đã đóng trong khi đang mở."""
    assert _tool().api_exposed is True
    assert [t for t in _catalog("") if t.name == "image.ltt"] == []


# ═════ hợp đồng công khai phải nói ĐÚNG thứ nó nhận được ════════════════════
def test_schema_cong_khai_KHONG_chua_tham_so_nhieu_anh():
    """⛔ Tầng API chỉ giải được **một** phiên tải lên cho **một** tham số
    (`invocation.promote_media`). Phơi `image_keys` ra là hứa một thứ gọi vào sẽ
    hỏng — và hỏng sau khi đã giữ credit."""
    t = [x for x in _catalog("image.ltt") if x.name == "image.ltt"][0]
    assert "image_keys" not in t.input_schema["properties"]
    assert "image_key" in t.input_schema["properties"]


def test_mo_ta_KHONG_hua_nhieu_anh_hon_thu_schema_nhan():
    """Mô tả nói "up to two reference images" trong khi schema nhận một là mâu
    thuẫn khách đọc thấy — và họ sẽ viết code theo mô tả."""
    t = [x for x in _catalog("image.ltt") if x.name == "image.ltt"][0]
    mo_ta = " ".join([t.description] + [
        str(p.get("description", "")) for p in t.input_schema["properties"].values()])
    assert "two reference" not in mo_ta.lower()


def test_tham_so_AN_phai_co_MAC_DINH():
    """Tham số `hidden` mà không có `default` thì tầng API bỏ trống, và handler tự
    chọn một thứ khác. Đã có tiền lệ thật: tool storyboard chạy — và **tính tiền** —
    sai nhánh vì đúng lỗi này."""
    t = _tool()
    for ten in t.api_contract.get("hidden", ()):
        spec = t.params_schema.get(ten)
        assert spec is not None, f"hidden nhac tham so khong ton tai: {ten}"
        if ten == "image_keys":
            continue        # tham so media: khong dat mac dinh duoc, va vang la dung
        assert "default" in spec, f"tham so an {ten!r} thieu default"


def test_moi_tham_so_cong_khai_deu_co_mo_ta():
    t = _tool()
    an = set(t.api_contract.get("hidden", ()))
    tai_lieu = t.api_contract.get("params", {})
    thieu = [p for p in t.params_schema if p not in an and p not in tai_lieu]
    assert thieu == [], f"tham so cong khai khong co mo ta: {thieu}"


# ═════════════════════════ giá — chỗ sai thì mất tiền ═══════════════════════
def test_gia_nhan_theo_so_anh():
    gia = _app().manifest.credit_cost
    assert gia({"count": 3}) == 3 * gia({"count": 1})


def test_che_do_dung_anh_tham_chieu_DAT_HON():
    """Đo thật: có ảnh tham chiếu tốn ~190 giây, không có ~58 giây. Tính cùng giá
    là bán một thứ gấp ba lần thời gian máy với giá của thứ rẻ."""
    gia = _app().manifest.credit_cost
    for che_do in ("edit", "subject"):
        assert gia({"count": 1, "mode": che_do}) > gia({"count": 1, "mode": "t2i"})


def test_gia_khong_bao_gio_bang_KHONG_va_khong_am():
    """Giá 0 là tool miễn phí — mở đường cho một người dùng chiếm GPU vô hạn."""
    gia = _app().manifest.credit_cost
    for p in ({}, {"count": 0}, {"count": -5}, {"count": "bay"}, {"count": None},
              {"count": 99}, {"mode": None}, {"count": 2, "mode": "la"}):
        assert gia(p) > 0, f"gia sai voi {p}: {gia(p)}"


def test_gia_bi_CHAN_TREN_dung_bang_tran_cua_schema():
    """Khai `max: 4` mà hàm giá không chặn thì `count=1000` được tính tiền cho 1000
    ảnh — hoặc tệ hơn, chạy 1000 ảnh."""
    gia = _app().manifest.credit_cost
    assert gia({"count": 1000}) == gia({"count": 4})


# ═══════════ handler: kiểm tham số TRƯỚC khi tiêu một giây GPU ══════════════
def _goi(**p):
    from apps.anhnoibo import jobs
    return jobs.handle(p, ctx=None)


def test_anh_tham_chieu_cua_NGUOI_KHAC_bi_TU_CHOI():
    """⛔ Khoá lưu trữ là **chuỗi khách gửi lên**. Không kiểm thì khách A đọc được
    ảnh của khách B chỉ bằng cách đoán khoá. Kiểm **đoạn thứ hai** chứ không phải
    tiền tố app, vì ảnh tham chiếu hợp lệ có thể là artifact của một job trước ở
    app khác của cùng người dùng đó."""
    from apps.anhnoibo import jobs
    with pytest.raises(jobs.LoiTaoAnh):
        _goi(prompt="A cat", mode="edit", owner_id="u1",
             image_key="anhnoibo/u2/j9/0.png")


def test_anh_tham_chieu_cua_CHINH_MINH_qua_duoc_vong_kiem_quyen():
    """Không được chặn nhầm: một artifact của app khác, cùng người dùng, là hợp lệ."""
    # Quy tắc này đã chuyển từ `jobs.py` sang `features.py` (H37/L6): nó là
    # nghiệp vụ, và nghiệp vụ nằm trong một cánh cửa thì cửa thứ hai phải chép.
    from apps.anhnoibo import features
    features._kiem_chu_so_huu("taoanh/u1/j3/0.png", "u1")


def test_khong_biet_chu_so_huu_thi_TU_CHOI_chu_khong_cho_qua():
    """Thiếu `owner_id` mà vẫn nhận ảnh tham chiếu là bỏ hẳn vòng kiểm quyền."""
    from apps.anhnoibo import jobs
    with pytest.raises(jobs.LoiTaoAnh):
        _goi(prompt="A cat", mode="edit", image_key="anhnoibo/u2/j9/0.png")


#: Đúng những gì `platform_core.job_runner.JobContext` thật sự cấp.
CTX_CO_THAT = {"job_id", "gpu_uuid", "worker_id", "attempt", "app_slug",
               "job_type", "progress", "has_gpu", "gpu_env"}


def _thuoc_tinh_ctx_duoc_doc(mo_dun):
    """Đọc bằng AST chứ không so chuỗi — so chuỗi bắt nhầm cả chú thích."""
    import ast
    import inspect

    cay = ast.parse(inspect.getsource(mo_dun))
    return {n.attr for n in ast.walk(cay)
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
            and n.value.id == "ctx"}


def test_handler_chi_doc_nhung_thuoc_tinh_ctx_CO_THAT():
    """`JobContext` chỉ có `job_id`/`gpu_uuid`/`progress()`… — nó **không** mang
    `db`, `storage` hay `owner_id`. Đọc chúng từ `ctx` là `AttributeError` lúc chạy
    thật, và một test dùng ctx giả sẽ không bao giờ bắt được."""
    from apps.anhnoibo import jobs

    la = _thuoc_tinh_ctx_duoc_doc(jobs) - CTX_CO_THAT
    assert la == set(), f"JobContext khong co: {sorted(la)}"


def test_dinh_nghia_CTX_CO_THAT_van_khop_voi_JobContext_that():
    """Bánh cóc cho chính test trên: nếu `JobContext` mất một thuộc tính thì danh
    sách ở đây thành lời hứa cũ, và test trên sẽ cho qua một lỗi thật."""
    from platform_core.job_runner import JobContext

    that = set(dir(JobContext("j1"))) | set(vars(JobContext))
    thieu = CTX_CO_THAT - that
    assert thieu == set(), f"JobContext khong con: {sorted(thieu)}"


def test_khong_giu_phien_CSDL_qua_mot_luot_goi_mang():
    """Một lượt vẽ có thể mất 15 phút. Giữ transaction mở suốt thời gian đó là giữ
    khoá CSDL trong lúc chờ mạng."""
    import inspect

    from apps.anhnoibo import http_cong
    ma = inspect.getsource(http_cong.goi_http)
    vi_tri_dong = ma.index("_voi_db(")
    vi_tri_goi = ma.index("httpx.request")
    assert vi_tri_dong < vi_tri_goi, "phai dong phien CSDL TRUOC khi goi mang"
    # Và lời gọi mạng KHÔNG được nằm bên trong hàm chạy dưới phiên CSDL.
    than_lay = ma[ma.index("def lay("):ma.index("da_hong: list")]
    assert "httpx" not in than_lay, "goi mang ben trong phien CSDL"


def test_429_KHONG_bi_danh_dau_loi():
    """⛔ Cảnh báo thường trực của dự án: `danh_dau_loi` cho 429 nghĩa là cooldown
    rồi `disable` sau 5 lần — một tối chạy video bên dự án kia sẽ **tự tắt vĩnh
    viễn** model nhà."""
    import inspect

    from apps.anhnoibo import http_cong
    ma = inspect.getsource(http_cong.goi_http)
    assert "429" in ma and "!= 429" in ma


def test_thieu_prompt_thi_hong_ngay_khong_cham_may_B():
    from apps.anhnoibo import jobs
    with pytest.raises(jobs.LoiTaoAnh):
        _goi(prompt="   ")


def test_che_do_can_anh_ma_khong_co_anh_thi_bao_ro():
    from apps.anhnoibo import jobs
    for che_do in ("edit", "subject"):
        with pytest.raises(jobs.LoiTaoAnh):
            _goi(prompt="A cat", mode=che_do)


def test_qua_nhieu_anh_thi_TU_CHOI_chu_khong_lang_le_cat_bot():
    """Cắt bớt là lặng lẽ giao một thứ khác thứ khách yêu cầu."""
    from apps.anhnoibo import jobs
    with pytest.raises(jobs.LoiTaoAnh) as e:
        _goi(prompt="A cat", mode="subject", image_keys=["a", "b", "c"])
    assert "2" in str(e.value)


def test_t2i_kem_anh_tham_chieu_thi_TU_CHOI():
    """Nhận rồi bỏ qua là tính tiền giá t2i cho thứ khách tưởng là edit."""
    from apps.anhnoibo import jobs
    with pytest.raises(jobs.LoiTaoAnh):
        _goi(prompt="A cat", mode="t2i", image_key="u/a.png")


def test_che_do_la_thi_TU_CHOI():
    from apps.anhnoibo import jobs
    with pytest.raises(jobs.LoiTaoAnh):
        _goi(prompt="A cat", mode="inpaint")


def test_handler_chi_goi_DUNG_MOT_provider_la_model_nha():
    """D-010: đổi model sau lưng khách là đánh tráo sản phẩm. App này chỉ bán model
    nhà; hết chỗ thì báo bận, không lặng lẽ chuyển sang đám mây.

    Kiểm bằng AST: `providers.get(...)` được gọi với đúng một tên. So chuỗi
    "gemini" không dùng được ở đây — lớp **dịch prompt** gọi Gemini một cách hoàn
    toàn hợp lệ, và đó là việc khác hẳn việc sinh ảnh."""
    import ast
    import inspect

    from apps.anhnoibo import jobs

    ten = set()
    for n in ast.walk(ast.parse(inspect.getsource(jobs))):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "get"
                and isinstance(n.func.value, ast.Name)
                and n.func.value.id == "providers"):
            ten |= {a.value for a in n.args if isinstance(a, ast.Constant)}
    assert ten == {"ltt_image"}, f"goi provider khac: {sorted(ten)}"


# ═══════════ không để lại một link 404 nào trên giao diện ═══════════════════
def test_khong_hien_the_nao_tren_giao_dien_khi_CHUA_co_giao_dien():
    """⛔ Lỗi tôi đã thật sự tạo ra rồi mới bắt được: app không có `routes.py`
    nhưng vẫn hiện trong header, trỏ tới `/anhnoibo` → **404 với mọi người đã
    đăng nhập**.

    Hai cách sửa hiển nhiên đều KHÔNG chạy, và đó là lý do test này tồn tại:
      · `public=False` — `visible_on_surface` trả `authenticated or public`, nên
        nó chỉ ẩn với khách vãng lai;
      · `nav=()` — `nav_entries()` **tự sinh** lại một dòng từ `display_name`.
    Cách chạy được là `catalog_parent`, cơ chế hợp đồng đã có sẵn cho đúng việc này.
    """
    from platform_core.registry import visible_on_surface

    m = _app().manifest
    for authed in (False, True):
        for op in (False, True):
            assert visible_on_surface(m, authenticated=authed, operator=op) is False, (
                f"hien tren giao dien (authed={authed}, operator={op}) trong khi "
                "app khong co routes.py — do la mot link 404")


def test_neu_MAI_SAU_co_giao_dien_thi_test_tren_phai_duoc_go():
    """Bánh cóc hai chiều: ngày nào `routes.py` xuất hiện, test ở trên thành SAI —
    lúc đó app *nên* hiện ra. Test này bắt phải xử lý cả hai cùng lúc."""
    import pathlib

    co_ui = (pathlib.Path(__file__).parent.parent / "apps" / "anhnoibo"
             / "routes.py").exists()
    assert not co_ui, (
        "apps/anhnoibo/routes.py da ton tai: bo `catalog_parent` va sua "
        "test_khong_hien_the_nao_tren_giao_dien_khi_CHUA_co_giao_dien")


def test_duong_API_KHONG_bi_catalog_parent_chan():
    """`catalog_parent` chỉ chi phối catalog/nav. Nếu nó chặn cả API thì app này
    vô dụng — `thumbnail` là bằng chứng sống rằng nó không chặn."""
    from platform_core.public_api.catalog import app_may_be_public

    app = _app()
    assert app_may_be_public(app.manifest, error=app.error) is True
    assert [t for t in _catalog("image.ltt") if t.name == "image.ltt"]
