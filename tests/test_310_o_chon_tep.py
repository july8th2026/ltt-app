"""test_310 — ô chọn tệp dùng chung `.ltt-file` (đợt ổn định UI 2026-08-26).

Không mạng, không GPU.

## ⭐ CÁC PHÉP KIỂM NÀY CHỐT HÀNH VI, KHÔNG CHỐT VẺ NGOÀI

Một primitive giao diện dễ được kiểm bằng "trông có đúng không". Đó là phép kiểm
sai: nó đỏ khi ai đó đổi màu, và **xanh khi ai đó làm hỏng việc chọn tệp**.

Nên ở đây chốt đúng những thứ mà nếu mất thì sản phẩm hỏng:

  1. input native vẫn **là** input native — `name`, `accept`, `id` nguyên vẹn;
  2. `<label for>` vẫn trỏ đúng, vì đó là thứ duy nhất giữ cho ô còn bấm được;
  3. tên tệp bị **cắt bằng ellipsis** — bỏ nó là dựng lại đúng cái tràn ngang mà
     primitive này sinh ra để diệt;
  4. `chon_tep.js` có trong danh sách cache-bust.
"""
from __future__ import annotations

import io
import pathlib
import re

GOC = pathlib.Path(__file__).resolve().parent.parent


# ── Primitive trong ltt.css ──────────────────────────────────────────────────

def test_primitive_ltt_file_ton_tai_va_an_input_native():
    css = (GOC / "server" / "static" / "ltt.css").read_text(encoding="utf-8")
    assert ".ltt-file{" in css, "primitive .ltt-file da bien mat khoi ltt.css"

    an = re.search(r"\.ltt-file input\[type=file\]\{([^}]*)\}", css)
    assert an, "khong con luat an input native"
    than = an.group(1)
    for phai_co in ("position:absolute", "width:1px", "opacity:0"):
        assert phai_co in than, f"thieu `{phai_co}` — input native se hien lai"


def test_ten_tep_PHAI_bi_cat_bang_ellipsis():
    """⛔ Phép kiểm quan trọng nhất tệp này.

    Ô chọn tệp hiện tên tệp do người dùng đặt, tức một chuỗi **dài tuỳ ý**. Không
    cắt thì một tên tệp 200 ký tự đẩy rộng ô, đẩy rộng lưới, và dựng lại chính
    thanh cuộn ngang mà cả đợt này sinh ra để diệt — chỉ khác là lần này nó phụ
    thuộc vào việc khách đặt tên tệp thế nào, nên sẽ không ai tái hiện được.
    """
    css = (GOC / "server" / "static" / "ltt.css").read_text(encoding="utf-8")
    m = re.search(r"\.ltt-file-name\{([^}]*)\}", css)
    assert m, "mat luat .ltt-file-name"
    than = m.group(1)
    assert "text-overflow:ellipsis" in than
    assert "white-space:nowrap" in than
    assert "overflow:hidden" in than


def test_vong_tieu_diem_dung_token_chuan_khong_phai_mau_cung():
    """Khuôn gốc `/taovideo` chỉ đổi màu viền khi focus. Bản dùng chung phải dùng
    đúng vòng tiêu điểm của hệ, nếu không ta nhân bản một lỗ accessibility."""
    css = (GOC / "server" / "static" / "ltt.css").read_text(encoding="utf-8")
    m = re.search(r"\.ltt-file:focus-within\{([^}]*)\}", css)
    assert m, "khong co trang thai focus-within — o chon tep se vo hinh voi ban phim"
    assert "var(--focus-ring)" in m.group(1)


def test_primitive_khong_dung_mau_viet_cung():
    """316 màu cứng là nợ có sẵn. Không quét lại toàn kho, nhưng **cái mới phải
    sạch** — nếu không thì primitive dùng chung lại đi phát tán đúng vấn đề đó."""
    css = (GOC / "server" / "static" / "ltt.css").read_text(encoding="utf-8")
    khoi = re.findall(r"\.ltt-file[^{]*\{[^}]*\}", css)
    assert khoi, "khong tim thay luat nao cua .ltt-file"
    cung = [k for k in khoi if re.search(r"#[0-9a-fA-F]{3,8}\b", k)]
    assert not cung, f"primitive dung mau viet cung: {cung}"


# ── Bánh cóc cho gốc của UI-002 ──────────────────────────────────────────────

def test_ba_panel_dieu_khien_chi_cuon_DOC():
    """`overflow:auto` mở **cả hai** trục. Ba app sao chép nguyên văn cùng một
    luật, nên đây là một lỗi ở ba nơi chứ không phải ba lỗi.

    ⛔ Cách sửa SAI mà phép kiểm này chặn: `overflow-x:hidden`. Nó cắt phần thừa
       đi và làm cái tràn **biến mất khỏi mắt** trong khi vẫn còn đó — tức xoá
       mất chính tín hiệu mà ta cần để biết layout đang sai.
    """
    css = (GOC / "server" / "static" / "ltt.css").read_text(encoding="utf-8")
    for ten in (".th-controls", ".im-controls", ".clip-controls"):
        m = re.search(re.escape(ten) + r"\{max-height:calc\(100vh - 130px\);([^}]*)\}", css)
        assert m, f"{ten}: mat luat panel"
        than = m.group(1)
        assert "overflow-y:auto" in than, f"{ten} quay lai `overflow` hai truc"
        assert "overflow-x:hidden" not in than, (
            f"{ten} dung overflow-x:hidden — do la che loi, khong phai sua loi")


# ── Cache-bust (quy tắc 6 của CLAUDE.md) ─────────────────────────────────────

def test_chon_tep_js_co_trong_danh_sach_cache_bust():
    from server import templating
    assert "chon_tep.js" in templating.TAI_SAN_CO_VERSION, (
        "them tai san tinh moi ma quen dinh version: Cloudflare se phuc vu ban cu "
        "toi khi het TTL — dung cai bay quy tac 6 cua CLAUDE.md")


# ── Trang tham chiếu: hành vi native phải nguyên vẹn ────────────────────────

def test_taoanh_giu_NGUYEN_hop_dong_upload_sau_khi_di_tru(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path/'ui310.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-ui-310")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung

    set_storage(LocalStorage(str(tmp_path / "store")))
    gen = dbmod.get_session(); db = next(gen)
    try:
        tao_nguoi_dung(db, email="ui310@test.com", password="matkhau-tot-12",
                       is_verified=True)
        db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    from fastapi.testclient import TestClient

    from server.app import create_app
    client = TestClient(create_app(), base_url="https://testserver",
                        follow_redirects=False)
    try:
        login = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"', login.text).group(1)
        client.post("/login", data={"username": "ui310@test.com",
                                    "password": "matkhau-tot-12",
                                    "csrf_token": token})
        page = client.get("/taoanh")
        assert page.status_code == 200
        html = page.text

        assert "ltt-file" in html, "trang tham chieu chua dung primitive"

        # ⛔ Hop dong voi backend PHAI khong doi. Doi mot loi hien thi lay mot loi
        #    chuc nang la mot cuoc doi te hon nhieu.
        for ten, ma in (("source_image", "im-source"), ("style_image", "im-style")):
            assert f'name="{ten}"' in html, f"mat truong upload `{ten}`"
            assert f'id="{ma}"' in html, f"mat id `{ma}`"
            assert f'for="{ma}"' in html, (
                f"mat lien ket <label for={ma}> — o chon tep se KHONG bam duoc, "
                f"va do la cach hong im lang nhat cua khuon nay")
        assert 'accept="image/png,image/jpeg,image/webp"' in html

        assert "chon_tep.js" in html, "trang khong nap script tang cuong dan"
    finally:
        client.close(); set_storage(None); dbmod.reset_engine()


def test_o_chon_tep_khong_dung_innerHTML_cho_ten_tep():
    """Tên tệp là dữ liệu người dùng đặt. Một tệp tên `<img onerror=…>` không được
    trở thành thẻ HTML.

    ⛔ PHẢI BỎ CHÚ THÍCH TRƯỚC KHI TÌM. Bản đầu của phép kiểm này chỉ làm
       `"innerHTML" not in js` và **đỏ ngay** — vì nó bắt trúng dòng chú thích
       *giải thích vì sao không dùng `innerHTML`*.

    ⭐ Một phép kiểm bảo mật báo động giả sẽ bị người ta tắt, và khi nó bị tắt thì
       nó không còn canh gì nữa. Báo động giả không phải phiền toái — nó là cách
       một phép kiểm chết.
    """
    js = (GOC / "server" / "static" / "chon_tep.js").read_text(encoding="utf-8")
    ma = re.sub(r"/\*.*?\*/", "", js, flags=re.S)          # chu thich khoi
    ma = re.sub(r"(?m)^\s*//.*$", "", ma)                  # chu thich dong
    ma = re.sub(r"(?m)\s+//.*$", "", ma)                   # chu thich cuoi dong

    assert "textContent" in ma, "khong con dat ten tep bang textContent"
    assert "innerHTML" not in ma, (
        "chon_tep.js dat ten tep bang innerHTML — ten tep la du lieu nguoi dung")
