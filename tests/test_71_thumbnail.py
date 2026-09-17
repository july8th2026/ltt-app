"""
H5 — app thumbnail: handler + giá credit.

🔴 VIẾT LẠI 09/09/2026 — AI CLEAN REBUILD V2 pha 06.3. App đổi động cơ từ Gemini
   Image sang **LTT_IMAGE**, nên ba nhóm phép kiểm cũ mất tiền đề:

     gỡ       `test_reference_duoc_gui_inline_va_brand_vao_prompt` chốt việc nhét
              ảnh **inline base64** vào thân yêu cầu — cơ chế ấy đã xoá; đường mới
              đưa ảnh bằng **presigned GET**. Viết lại nó cho đường mới sẽ là một
              phép kiểm KHÁC đội tên cũ.
     gỡ       `test_handle_dung_key_tu_engine` và
              `test_gemini_loi_thi_nem_va_che_khoa` chốt việc app **tự cầm khoá
              API**. Nay app không cầm khoá nào, nên không có gì để rò.
     viết lại phần còn lại: mỗi cái giữ nguyên MỆNH ĐỀ, đổi CƠ CHẾ.

⭐ Và một mệnh đề MỚI, quan trọng nhất của pha này: **tiêu đề/phụ đề bị TỪ CHỐI
   CÓ TÊN**. Model nhà không vẽ được chữ đọc được; im lặng bỏ qua thì khách gõ
   tiêu đề, trả tiền, rồi nhận về một tấm ảnh trắng chữ mà không ai giải thích.
"""
from __future__ import annotations

import io

import pytest


@pytest.fixture()
def storage(tmp_path):
    from platform_core.storage import LocalStorage, set_storage
    st = LocalStorage(str(tmp_path / "store"))
    set_storage(st)
    try:
        yield st
    finally:
        set_storage(None)


class _Ctx:
    def __init__(self, job_id):
        self.job_id = job_id

    def progress(self, *a, **k):
        pass


def _valid_png(size=(320, 180), color=(180, 30, 25)):
    from PIL import Image
    out = io.BytesIO(); Image.new("RGB", size, color).save(out, format="PNG")
    return out.getvalue()


class _KetQua:
    """Cái `DieuPhoi.chay` trả về."""

    def __init__(self, keys):
        self.image_keys = tuple(keys)
        self.prompt_da_gui = "a thumbnail"
        self.da_dich = True
        self.canh_bao = ()


def _bo_dieu_phoi(monkeypatch, keys, *, no=None, ghi_anh=None):
    """Tiêm một bộ điều phối giả; trả về sổ ghi các lượt gọi.

    `ghi_anh` là kho lưu trữ: truyền vào thì bộ điều phối giả **ghi ảnh thật**
    lên đúng những khoá nó trả về — đúng như máy B làm qua vé presigned. Cần thế
    để chấm điểm kỹ thuật có gì mà đọc.
    """
    from apps.thumbnail import jobs

    so = {"n": 0}

    class _DP:
        def chay(self, **kw):
            so["n"] += 1
            so.update(kw)
            if no is not None:
                raise no
            if ghi_anh is not None:
                for k in keys:
                    ghi_anh.put(k, io.BytesIO(_valid_png()), content_type="image/png")
            return _KetQua(keys)

    monkeypatch.setattr(jobs, "_dieu_phoi", lambda: _DP())
    return so


# ───────────────────────────────── giá ──────────────────────────────────────
def test_cost_theo_so_anh():
    """Giá là một HÀM của tham số, và nó đọc bảng giá model nhà.

    🔴 Con số đổi (5 → 3 mỗi ảnh) vì app đổi model, không vì ai chỉnh giá: model
       nhà có bảng giá riêng ở `platform_core.image_gen.gia`, và `test_1003`
       chốt rằng ba app dùng chung đúng bảng ấy.
    """
    from apps.thumbnail.manifest import MANIFEST
    from platform_core.image_gen import gia

    assert MANIFEST.credit_cost({"count": 1}) == gia.CREDIT_MOI_ANH
    assert MANIFEST.credit_cost({"count": 3}) == 3 * gia.CREDIT_MOI_ANH
    # chặn trên 4 ảnh
    assert MANIFEST.credit_cost({"count": 99}) == 4 * gia.CREDIT_MOI_ANH
    assert MANIFEST.credit_cost({}) == gia.CREDIT_MOI_ANH


def test_remix_dat_hon_vi_may_ve_lau_hon():
    """Ảnh có tham chiếu đắt gấp 3 — trần giữ chỗ phải BIẾT điều đó.

    Giữ chỗ theo giá ảnh thường rồi quyết toán theo giá tham chiếu là thu quá
    số đã giữ: một bút toán lệch, không phải một sai số làm tròn.
    """
    from apps.thumbnail.manifest import MANIFEST
    from platform_core.image_gen import gia

    thuong = MANIFEST.credit_cost({"count": 1})
    remix = MANIFEST.credit_cost({"count": 1, "reference_key": "thumbnail/u1/x"})
    assert remix == thuong * gia.HE_SO_THAM_CHIEU


# ───────────────────────── tính năng thuần (không đổi) ──────────────────────
def test_reference_brand_va_score_ky_thuat_la_du_lieu_that():
    from apps.thumbnail.features import (brand_directive, clean_brand,
                                         technical_score, validate_reference)
    data = _valid_png()
    assert validate_reference(data, "image/png") == ("image/png", (320, 180))
    with pytest.raises(ValueError, match="MIME"):
        validate_reference(data, "image/jpeg")
    brand = clean_brand({"name": " LTT ", "primary_color": "#aa1122",
                         "secondary_color": "khong-hop-le", "font": "Barlow"})
    assert brand["primary_color"] == "#AA1122" and brand["secondary_color"] == "#111111"
    assert "brand=LTT" in brand_directive(brand)
    score = technical_score(data)
    assert score["method"] == "technical-v1" and score["width"] == 320
    assert 0 <= score["score"] <= 100


# ─────────────────────────── chữ trong ảnh đã gỡ ────────────────────────────
@pytest.mark.parametrize("khoa", ["title", "subtitle"])
def test_tieu_de_bi_TU_CHOI_CO_TEN_chu_khong_bi_bo_qua_im_lang(storage, monkeypatch,
                                                               khoa):
    """⛔ Mệnh đề chính của pha 06.3.

    Bỏ qua im lặng là loại hỏng đắt nhất: job chạy, tiền bị trừ, ảnh trả về —
    và không có gì nói cho khách biết vì sao chữ họ gõ không xuất hiện.
    """
    from apps.thumbnail import jobs

    so = _bo_dieu_phoi(monkeypatch, ["thumbnail/u1/j/0.png"])
    with pytest.raises(ValueError, match="chữ"):
        jobs.handle({"topic": "dau tu", "owner_id": "u1", khoa: "GIAU"}, _Ctx("j"))
    assert so["n"] == 0, "tu choi PHAI xay ra truoc khi cham may B"


def test_tieu_de_RONG_thi_van_chay_binh_thuong(storage, monkeypatch):
    """Giao diện cũ vẫn gửi `title=""` — chuỗi rỗng không phải một yêu cầu."""
    from apps.thumbnail import jobs

    _bo_dieu_phoi(monkeypatch, ["thumbnail/u1/j/0.png"])
    out = jobs.handle({"topic": "x", "owner_id": "u1", "title": "", "subtitle": "  "},
                      _Ctx("j"))
    assert out["count"] == 1


# ─────────────────────────────── đường chạy ─────────────────────────────────
def test_thieu_topic_thi_nem(storage):
    from apps.thumbnail import jobs
    with pytest.raises(ValueError):
        jobs.handle({"topic": "  "})


def test_chua_cau_hinh_cong_render_thi_NEM(storage, monkeypatch):
    """🔴 Thay `test_thieu_khoa_thi_nem`. Mệnh đề y nguyên — *thiếu cấu hình thì
    NÉM để nền tảng hoàn credit, không âm thầm nuốt* — chỉ đổi thứ còn thiếu:
    app không cần khoá API nữa, nó cần địa chỉ cổng render.
    """
    import types

    from platform_core import providers

    from apps.thumbnail import jobs

    # `Provider` là dataclass frozen — không vá thuộc tính được, nên vá cửa TRA.
    monkeypatch.setattr(providers, "get",
                        lambda pid: types.SimpleNamespace(base_url=""))
    with pytest.raises(RuntimeError, match="LTT_RENDER_BASE_URL"):
        jobs.handle({"topic": "abc", "owner_id": "u1"}, _Ctx("j"))


def test_tao_anh_thanh_cong_tra_khoa_va_cham_diem(storage, monkeypatch):
    from apps.thumbnail import jobs

    keys = [f"thumbnail/u1/job123/{i}.png" for i in range(2)]
    so = _bo_dieu_phoi(monkeypatch, keys, ghi_anh=storage)

    out = jobs.handle({"topic": "dau tu", "count": 2, "aspect_ratio": "16:9",
                       "owner_id": "u1"}, _Ctx("job123"))
    assert out["count"] == 2 and out["image_keys"] == keys
    assert so["mode"] == "t2i" and so["ti_le"] == "16:9" and so["so_anh"] == 2
    assert so["tien_to_khoa"] == "thumbnail/u1"
    assert all(s["method"] == "technical-v1" for s in out["scores"])


def test_cham_diem_hong_KHONG_lam_hong_job(storage, monkeypatch):
    """Ảnh đã vẽ xong và đã tính tiền — chấm điểm là việc phụ."""
    from apps.thumbnail import jobs

    _bo_dieu_phoi(monkeypatch, ["thumbnail/u1/jS/0.png"])   # không có trong storage
    out = jobs.handle({"topic": "x", "owner_id": "u1"}, _Ctx("jS"))
    assert out["scores"][0]["method"] == "unavailable"
    assert out["count"] == 1


def test_anh_tham_chieu_di_bang_KHOA_va_bat_che_do_edit(storage, monkeypatch):
    """🔴 Thay phép kiểm "gửi inline base64".

    Bất biến còn sống: ảnh tham chiếu **tới được model**, và nó đi kèm chế độ
    đúng. Cơ chế thì đổi hẳn — máy B tự tải bằng vé presigned (Q102), nền tảng
    không nhét bytes vào thân yêu cầu nữa.
    """
    from apps.thumbnail import jobs

    ref = "thumbnail/u1/refs/r1"
    storage.put(ref, io.BytesIO(_valid_png((128, 128))), content_type="image/png")
    so = _bo_dieu_phoi(monkeypatch, ["thumbnail/u1/job-ref/0.png"])

    out = jobs.handle({"topic": "x", "owner_id": "u1", "reference_key": ref,
                       "brand": {"name": "LTT", "font": "Barlow"}}, _Ctx("job-ref"))
    assert so["ref_keys"] == [ref] and so["mode"] == "edit"
    assert "brand=LTT" in out["prompt"]


def test_anh_tham_chieu_CUA_NGUOI_KHAC_bi_chan_TRUOC_khi_cham_may(storage,
                                                                  monkeypatch):
    """Bất biến BẢO MẬT — khoá lưu trữ là chuỗi khách gửi lên."""
    from apps.thumbnail import jobs

    so = _bo_dieu_phoi(monkeypatch, ["thumbnail/u1/j/0.png"])
    with pytest.raises(ValueError, match="không thuộc"):
        jobs.handle({"topic": "x", "owner_id": "u2",
                     "reference_key": "thumbnail/u1/refs/r1"}, _Ctx("j"))
    assert so["n"] == 0, "anh cua nguoi khac da di ra khoi nen tang"


def test_thieu_anh_thi_tinh_tien_theo_so_anh_THAT(storage, monkeypatch):
    """W1.1 giữ nguyên: xin 3, nhận 2 thì trả tiền 2.

    Cơ chế đổi — trước là vòng lặp từng ảnh ở app, nay cổng render trả về đúng
    số ảnh tải lên được (`runner.py: image_keys[:so]`). Mệnh đề thì y nguyên.
    """
    from apps.thumbnail import jobs
    from platform_core.image_gen import gia

    _bo_dieu_phoi(monkeypatch, [f"thumbnail/u1/jobP/{i}.png" for i in range(2)])
    out = jobs.handle({"topic": "x", "count": 3, "owner_id": "u1"}, _Ctx("jobP"))
    assert out["count"] == 2
    assert out["credit_cost"] == gia.tinh(so_anh=2, che_do="t2i")


def test_resume_khong_ve_lai_anh_da_co(storage, monkeypatch):
    """W1.1: worker chết rồi job bị thu hồi — ảnh cũ được DÙNG LẠI, không đốt
    lại GPU và không thu tiền hai lần."""
    from apps.thumbnail import jobs

    keys = [f"thumbnail/u1/jobR/{i}.png" for i in range(2)]
    for k in keys:
        storage.put(k, io.BytesIO(_valid_png()), content_type="image/png")
    so = _bo_dieu_phoi(monkeypatch, keys)

    out = jobs.handle({"topic": "x", "count": 2, "owner_id": "u1"}, _Ctx("jobR"))
    assert out["count"] == 2 and so["n"] == 0, "da ve lai mot lo anh da co"


def test_moi_MOT_anh_co_san_thi_VAN_chay_lai(storage, monkeypatch):
    """Đối chứng cho phép kiểm trên: resume chỉ đúng khi **đủ cả lô**.

    Thiếu một tấm mà bỏ qua là giao thiếu hàng; cổng render idempotent theo
    `job_id` nên gửi lại không đốt GPU hai lần.
    """
    from apps.thumbnail import jobs

    storage.put("thumbnail/u1/jobH/0.png", io.BytesIO(_valid_png()),
                content_type="image/png")
    so = _bo_dieu_phoi(monkeypatch, [f"thumbnail/u1/jobH/{i}.png" for i in range(2)])
    jobs.handle({"topic": "x", "count": 2, "owner_id": "u1"}, _Ctx("jobH"))
    assert so["n"] == 1


def test_khong_tao_duoc_anh_nao_thi_nem(storage, monkeypatch):
    """W1.1: không ảnh nào → NÉM để nền tảng hoàn toàn bộ credit + cho retry."""
    from apps.thumbnail import jobs
    from platform_core.image_gen import dieu_phoi

    _bo_dieu_phoi(monkeypatch, [], no=dieu_phoi.DieuPhoiError("may bao loi"))
    with pytest.raises(RuntimeError):
        jobs.handle({"topic": "x", "count": 2, "owner_id": "u1"}, _Ctx("jobF"))


def test_may_BAN_thi_xep_lai_chu_khong_bao_hong(storage, monkeypatch):
    """⛔ BẬN ≠ HỎNG. `DangBan` đưa job về `resource_wait`: không tiêu một lượt
    thử, không chạm tiền. Ném `RuntimeError` ở đây sẽ tiêu ba lượt rồi hỏng job
    kèm hoàn tiền cho một việc CHƯA TỪNG CHẠY."""
    from apps.thumbnail import jobs
    from platform_core.image_gen import cong_render
    from platform_core.jobs import DangBan

    _bo_dieu_phoi(monkeypatch, [], no=cong_render.BanError("ban", eta_s=600))
    with pytest.raises(DangBan) as ei:
        jobs.handle({"topic": "x", "owner_id": "u1"}, _Ctx("jobB"))
    assert getattr(ei.value, "retry_after_s", None) == 600


# ────────────────────────── cổng HTTP (không đổi) ───────────────────────────
def test_image_route_chan_cross_user(tmp_path, monkeypatch):
    """W2.6: gõ thẳng URL ảnh của người khác → 404 (kiểm sở hữu ở tầng HTTP),
    ảnh của chính mình → 200."""
    import io as _io
    import re as _re

    import platform_core.db as dbmod
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'img.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-img")
    monkeypatch.setenv("LTT_ADMIN_USERNAME", "admin")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    from platform_core.storage import LocalStorage, set_storage
    st = LocalStorage(str(tmp_path / "store")); set_storage(st)
    from platform_core.models import JOB_DONE, Job
    from platform_core.users import tao_nguoi_dung
    gen = dbmod.get_session(); db = next(gen)
    try:
        a = tao_nguoi_dung(db, email="a@img.com", password="matkhau-tot-12", is_verified=True)
        b = tao_nguoi_dung(db, email="b@img.com", password="matkhau-tot-12", is_verified=True)
        db.flush()
        # ⚠️ Job CŨ giữ nguyên `title`/`text_style` trong `params` — lịch sử không
        #    viết lại được, và trang lịch sử vẫn phải đọc được nó.
        seeded = Job(user_id=a.id, app_slug="thumbnail", job_type="thumbnail.generate",
                     status=JOB_DONE, progress=100,
                     params={"topic": "NOI_DUNG_CUA_A", "title": "TIEU_DE_CUA_A",
                             "aspect_ratio": "16:9", "count": 1,
                             "text_style": "bold_impact"},
                     result={"image_keys": [f"thumbnail/{a.id}/job2/0.png"]})
        db.add(seeded); db.commit(); a_id, b_id, seeded_id = a.id, b.id, seeded.id
    finally:
        try: next(gen)
        except StopIteration: pass

    st.put(f"thumbnail/{b_id}/job1/0.png", _io.BytesIO(b"PNGB"), content_type="image/png")
    st.put(f"thumbnail/{a_id}/job2/0.png", _io.BytesIO(b"PNGA"), content_type="image/png")

    from fastapi.testclient import TestClient
    from server.app import create_app
    c = TestClient(create_app(), base_url="https://testserver", follow_redirects=False)
    try:
        tok = _re.search(r'name="csrf_token" value="([^"]+)"', c.get("/login").text).group(1)
        c.post("/login", data={"username": "a@img.com",
                               "password": "matkhau-tot-12", "csrf_token": tok})
        # A đọc ảnh của B → 404
        r = c.get(f"/thumbnail/image/thumbnail/{b_id}/job1/0.png")
        assert r.status_code == 404
        # A đọc ảnh của CHÍNH MÌNH → 200
        r2 = c.get(f"/thumbnail/image/thumbnail/{a_id}/job2/0.png")
        assert r2.status_code == 200
        studio = c.get("/thumbnail")
        assert studio.status_code == 308
        assert studio.headers["location"] == "/taoanh/thumbnail"
        shell = c.get(studio.headers["location"])
        assert shell.status_code == 200
        assert "Tạo ảnh AI" in shell.text and "Thumbnail YouTube" in shell.text
        fragment = c.get("/thumbnail/studio-fragment")
        assert fragment.status_code == 200 and "TIEU_DE_CUA_A" in fragment.text
        assert "th-compare-pick" in fragment.text and "NOI_DUNG_CUA_A" not in fragment.text
        remix = c.get(f"/thumbnail/remix/{seeded_id}/0")
        assert remix.status_code == 308
        assert remix.headers["location"].startswith("/taoanh/thumbnail?")
        remix_fragment = c.get(
            f"/thumbnail/studio-fragment?remix_job_id={seeded_id}&image_index=0")
        assert (remix_fragment.status_code == 200 and
                "Đang phối lại từ kết quả đã chọn" in remix_fragment.text)
        assert "NOI_DUNG_CUA_A" in remix_fragment.text
        remix_csrf = _re.search(
            r'name="csrf_token" value="([^"]+)"', remix_fragment.text).group(1)
        import platform_core.job_submit as job_submit
        from platform_core.credit import ThieuCreditError
        monkeypatch.setattr(job_submit, "submit_with_credit",
                            lambda *_a, **_k: (_ for _ in ()).throw(ThieuCreditError("thiếu")))
        failed = c.post("/thumbnail/queue", data={
            "csrf_token": remix_csrf, "topic": "remix", "count": "1",
            "saved_reference_key": f"thumbnail/{a_id}/job2/0.png"})
        assert failed.status_code == 400
        assert st.exists(f"thumbnail/{a_id}/job2/0.png")  # lỗi submit không xóa output gốc
        c.cookies.clear()
        tok_b = _re.search(r'name="csrf_token" value="([^"]+)"', c.get("/login").text).group(1)
        c.post("/login", data={"username": "b@img.com",
                               "password": "matkhau-tot-12", "csrf_token": tok_b})
        assert c.get(f"/thumbnail/remix/{seeded_id}/0").status_code == 404
    finally:
        set_storage(None); dbmod.reset_engine()
