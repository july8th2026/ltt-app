"""Trang tham chiếu của một công cụ — thứ khách đọc trước khi gọi lần đầu.

🔴 VÌ SAO TỆP NÀY TỒN TẠI, VÀ NÓ BẮT ĐẦU BẰNG MỘT LỖI CỦA CHÍNH TÔI.

   Bản audit giao diện 25/08 chấm trang này **🔴 chưa sinh bảng từ `input_schema`**
   và **🟡 chưa có bảng lỗi**. Cả hai đều SAI: cả hai đã có từ trước (EXT-06), và
   có tốt. Tôi chấm bằng cách nhìn kích thước tệp template rồi **suy ra**, thay
   vì render trang và **đo**.

⛔ Bài học đắt hơn cái sai: một phán đoán viết vào ô điểm trông y hệt một số đo,
   và không ai đọc bảng điểm mà hỏi "con số này đo hay đoán".

⭐ Nên tệp này chốt bằng **HTML render thật**, không chốt bằng template.

Ba tính chất được giữ ở đây, mỗi cái từ một lỗi có thật:

1. Bảng tham số sinh từ hợp đồng — gõ tay là bản sao thứ hai và nó sẽ lệch.
2. Ví dụ phải **tự nhất quán** — xem `test_vi_du_KHONG_tu_mau_thuan`.
3. Trang dài phải có mục lục — mục thứ tư trở đi coi như không tồn tại nếu không.
"""
from __future__ import annotations

import os
import pathlib
import re
import tempfile

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def khach():
    """Một tài khoản đã xác thực, đã đăng nhập — khu `/developers` cần nó.

    ⚠️ `/developers/*` nằm **sau đăng nhập** theo chốt chủ sản phẩm 25/08: hệ
       thống API phải đăng nhập mới kích hoạt được, nên đây là khu của một tài
       khoản chứ không phải trang bán hàng. Đừng "sửa" test này thành ẩn danh.
    """
    tmp = pathlib.Path(tempfile.mkdtemp())
    os.environ["LTT_DATABASE_URL"] = f"sqlite:///{tmp / 'a.db'}"
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine, get_session

    Base.metadata.create_all(get_engine())
    from fastapi.testclient import TestClient

    from server.app import create_app
    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_SESSION_SECRET": "trang-cong-cu-secret-1234",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp / "config.json"),
        "LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": "text.chat,image.ltt"})
    with TestClient(app, base_url="https://testserver") as c:
        from platform_core import credit
        from platform_core.users import tao_nguoi_dung
        gen = get_session()
        db = next(gen)
        try:
            u = tao_nguoi_dung(db, email="cc@x.test", password="a-good-password-12")
            u.is_verified = True
            db.flush()
            credit.cap_tay(db, u.id, 500, by="test")
            db.commit()
        finally:
            try: next(gen)
            except StopIteration: pass
        page = c.get("/login")
        tok = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        c.post("/login", data={"username": "cc@x.test",
                               "password": "a-good-password-12",
                               "csrf_token": tok}, follow_redirects=False)
        yield c
    dbmod.reset_engine()


def _than(html: str) -> str:
    m = re.search(r"<main[^>]*>(.*)</main>", html, re.S)
    return m.group(1) if m else html


# ── Bảng tham số đến TỪ HỢP ĐỒNG, không từ template ─────────────────────────

@pytest.mark.parametrize("ten", ["text.chat", "image.ltt"])
def test_moi_tham_so_trong_schema_deu_co_mat_tren_trang(khach, ten):
    """Thiếu một tham số trên trang = một tính năng khách không biết mình có."""
    from platform_core.public_api.catalog import build_catalog
    from platform_core.public_api.config import load_public_api_config

    cfg = load_public_api_config({"LTT_PUBLIC_API": "1",
                                  "LTT_PUBLIC_API_TOOLS": "text.chat,image.ltt"})
    tool = [t for t in build_catalog(cfg) if t.name == ten][0].to_public_dict()
    html = khach.get(f"/developers/tools/{ten}").text
    thieu = [k for k in tool["input_schema"]["properties"] if k not in html]
    assert not thieu, f"{ten}: tham so co trong hop dong ma khong co tren trang: {thieu}"


def test_dau_van_tay_hop_dong_hien_tren_trang(khach):
    """Khách lưu được nó và biết hợp đồng đã đổi mà không cần diff schema tay."""
    from platform_core.public_api.catalog import build_catalog
    from platform_core.public_api.config import load_public_api_config

    cfg = load_public_api_config({"LTT_PUBLIC_API": "1",
                                  "LTT_PUBLIC_API_TOOLS": "text.chat"})
    bam = build_catalog(cfg)[0].to_public_dict()["contract_hash"]
    assert bam in khach.get("/developers/tools/text.chat").text


# ── Ví dụ: nhỏ nhất mà chạy được, và KHÔNG tự mâu thuẫn ─────────────────────

def test_vi_du_KHONG_tu_mau_thuan(khach):
    """🔴 Bản trước dựng ví dụ từ **mọi** thuộc tính, và cho ra thân này:

        "mode": "t2i",
        "image_key": "upl_from_POST_/api/v1/uploads"

    Trong khi chính schema nói `image_key` *"ignored for t2i"*. Một ví dụ tự mâu
    thuẫn **tệ hơn không có ví dụ**: nó chạy được, nên không ai phát hiện, và
    khách bê nguyên cấu trúc đó vào mã của họ.
    """
    html = _than(khach.get("/developers/tools/image.ltt").text)
    khoi = re.search(r"<pre[^>]*>(.*?)</pre>", html, re.S)
    assert khoi, "khong tim thay khoi vi du"
    vi_du = khoi.group(1)
    assert "t2i" in vi_du, "vi du phai neu mode mac dinh"
    assert "image_key" not in vi_du, (
        "vi du dat mode=t2i ma van gui image_key - chinh schema noi truong do bi "
        "BO QUA o t2i")


def test_vi_du_van_du_de_chay(khach):
    """Nhỏ nhất **mà chạy được** — bỏ hết thì cũng vô dụng."""
    import json
    html = _than(khach.get("/developers/tools/image.ltt").text)
    vi_du = re.search(r"<pre[^>]*>(.*?)</pre>", html, re.S).group(1)
    from html import unescape
    than = unescape(re.sub(r"<[^>]+>", "", vi_du))
    d = json.loads(than.split("-d '", 1)[1].rsplit("'", 1)[0])
    assert d["tool"] == "image.ltt"
    # `prompt` la truong BAT BUOC duy nhat; thieu no thi vi du khong the chay.
    assert d["input"].get("prompt")


# ── Trang dài phải đi tới được ──────────────────────────────────────────────

@pytest.mark.parametrize("neo", ["goi-the-nao", "bien-vao", "ket-qua",
                                 "webhook", "gioi-han", "loi"])
def test_moi_muc_deu_co_neo_va_duoc_muc_luc_tro_toi(khach, neo):
    """Bảy mục không có mục lục thì mục thứ tư trở đi coi như không tồn tại."""
    html = _than(khach.get("/developers/tools/text.chat").text)
    assert f'id="{neo}"' in html, f"thieu neo {neo}"
    assert f'href="#{neo}"' in html, f"muc luc khong tro toi {neo}"


def test_trang_noi_CACH_XAC_THUC_va_tro_toi_huong_dan(khach):
    """Cơ chế xác thực là thứ khác nhau giữa các khu API và hỏng đầu tiên."""
    html = _than(khach.get("/developers/tools/text.chat").text)
    assert "Authorization: Bearer" in html
    assert 'href="/huong-dan"' in html


def test_trang_tro_toi_BANG_GIA(khach):
    """Quyết định mua xảy ra lúc đọc endpoint, không phải lúc mở trang giá."""
    assert 'href="/gia-api"' in _than(khach.get("/developers/tools/text.chat").text)


# ── Ranh giới truy cập, theo chốt chủ sản phẩm ─────────────────────────────

def test_khu_developers_van_sau_dang_nhap():
    """⚠️ Chốt 25/08: **toàn bộ** `/developers/*` sau đăng nhập.

    Đã có một nhịp mở `quickstart` + `tools` ra công khai rồi hoàn nguyên. Test
    này giữ cho lần sau không mở lại vì "tài liệu thì nên công khai" — với hệ
    thống này, API phải đăng nhập mới kích hoạt được.
    """
    from fastapi.testclient import TestClient

    from server.app import create_app
    c = TestClient(create_app())
    for duong in ("/developers", "/developers/tools", "/developers/quickstart",
                  "/developers/tools/text.chat"):
        r = c.get(duong, follow_redirects=False)
        assert r.status_code in (302, 303), f"{duong} -> {r.status_code}"


# ── `only_when`: khai điều kiện bằng DỮ LIỆU, và điều kiện đó phải được KIỂM ──
#
# 🔴 ĐO 25/08. `image.ltt` có `mode` ba giá trị và `image_key` chỉ dùng cho hai.
#    Điều đó trước nay chỉ nằm trong một câu tiếng Anh giữa `description`, nên:
#      · trang tài liệu không lọc theo được;
#      · bộ sinh ví dụ không biết mà tránh, và đã dựng `mode=t2i` kèm `image_key`;
#      · và chính câu đó nói SAI hành vi — "ignored" trong khi máy chủ TỪ CHỐI.

def test_dieu_kien_hien_thanh_NHAN_tren_dung_hang(khach):
    """Phải đập vào mắt, không phải một mệnh đề giữa đoạn văn tiếng Anh."""
    html = _than(khach.get("/developers/tools/image.ltt").text)
    # ⚠️ Phải cắt theo Ô CỦA HÀNG, không theo lần xuất hiện đầu của chuỗi:
    #    `image_key` còn nằm trong phần mô tả của `mode` ("edit and subject both
    #    need image_key…"), và bản đầu của test này cắt trúng chỗ đó rồi đỏ.
    moc = "<code>image_key</code>"
    assert moc in html, "khong tim thay hang image_key"
    hang = html.split(moc, 1)[1][:900]
    assert "chỉ dùng khi" in hang
    assert "edit" in hang and "subject" in hang


def test_dieu_kien_den_TU_HOP_DONG_chu_khong_tu_doc_van_xuoi(khach):
    from platform_core.public_api.catalog import build_catalog
    from platform_core.public_api.config import load_public_api_config

    cfg = load_public_api_config({"LTT_PUBLIC_API": "1",
                                  "LTT_PUBLIC_API_TOOLS": "image.ltt"})
    tool = build_catalog(cfg)[0].to_public_dict()
    assert tool["input_schema"]["properties"]["image_key"]["x-ltt-only-when"] == \
        {"mode": ["edit", "subject"]}


def test_mo_ta_KHONG_con_noi_sai_hanh_vi(khach):
    """🔴 Máy chủ **từ chối** `image_key` ở `t2i`, không "bỏ qua" nó.

        if che_do == "t2i" and refs:
            raise LoiTaoAnh('Chế độ t2i không nhận ảnh tham chiếu.')

    Một tài liệu nói "ignored" khiến khách gửi kèm cho tiện, rồi đi tìm nguyên
    nhân ở phía họ.
    """
    from platform_core.public_api.catalog import build_catalog
    from platform_core.public_api.config import load_public_api_config

    cfg = load_public_api_config({"LTT_PUBLIC_API": "1",
                                  "LTT_PUBLIC_API_TOOLS": "image.ltt"})
    mo_ta = (build_catalog(cfg)[0].to_public_dict()["input_schema"]
             ["properties"]["image_key"]["description"])
    assert "ignored for t2i" not in mo_ta
    assert "REJECTED" in mo_ta


# ── Bộ kiểm của registry: khai bậy thì TỪ CHỐI, không im lặng xuất bản ───────

def _tool_voi_only_when(dieu_kien):
    from platform_core.registry import ToolSpec
    return ToolSpec(
        name="thu.tool", job_type="thu", description="thu",
        params_schema={"prompt": {"type": "text", "required": True},
                       "mode": {"type": "enum", "values": ["a", "b"]},
                       "an": {"type": "text"}},
        returns={}, api_exposed=True,
        api_contract={"scopes": ("jobs:create",), "description": "thu",
                      "hidden": ("an",),
                      "params": {"prompt": {"description": "d",
                                            "only_when": dieu_kien}}})


@pytest.mark.parametrize("dieu_kien,vi_sao", [
    ({"khong_co_that": ["a"]}, "tro vao tham so khong ton tai"),
    ({"an": ["a"]}, "tro vao tham so dang an - khach khong dieu khien duoc"),
    ({"mode": ["gõ_sai"]}, "gia tri khong nam trong enum"),
    ({"mode": []}, "danh sach rong"),
    ({}, "dict rong"),
    ("khong phai dict", "khong phai dict"),
])
def test_khai_bay_thi_registry_TU_CHOI(dieu_kien, vi_sao):
    """⛔ Khai `{"mode": ["edti"]}` (gõ sai) thì điều kiện không bao giờ khớp, và
    tham số đó **biến mất** khỏi mọi chế độ — khách không bao giờ biết mình gửi
    được nó. Một điều kiện không ai kiểm thì cũng vô dụng như câu văn nó thay."""
    from platform_core.registry import AppManifest, RegistryError, _validate_param_docs

    tool = _tool_voi_only_when(dieu_kien)
    m = AppManifest.__new__(AppManifest)
    object.__setattr__(m, "slug", "thu")
    with pytest.raises(RegistryError):
        _validate_param_docs(m, tool, tool.api_contract["params"], ("an",))


def test_khai_DUNG_thi_qua():
    from platform_core.registry import AppManifest, _validate_param_docs

    tool = _tool_voi_only_when({"mode": ["a", "b"]})
    m = AppManifest.__new__(AppManifest)
    object.__setattr__(m, "slug", "thu")
    _validate_param_docs(m, tool, tool.api_contract["params"], ("an",))
