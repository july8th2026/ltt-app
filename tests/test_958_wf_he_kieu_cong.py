"""LTT WORKFLOW V2 · Đợt 4.1 + 4.2 — hệ kiểu cổng, cardinality, MỘT nguồn luật.

Nguồn thiết kế: `25_26 §7` (`WF-701` `G37`, `WF-702` `G38`, `G39`).

🔴 Khiếm khuyết hôm nay, đo được: 13 kiểu tham số gộp còn **9** kiểu cổng, và
   `int` · `number` · `bool` · `dict` **đều thành `json`** ⇒ validator **không
   phân biệt được cổng số với cổng object**. Nối một cổng trả số vào một cổng
   nhận object là hợp lệ với nó.

⭐ `M9` là ngưỡng khó nhất của đợt: *luật nối dây client và server trùng khớp
   **100 %***. Cách duy nhất đạt được không phải là "viết cẩn thận hai lần" mà
   là **một nguồn luật** mà cả hai cùng đọc.
"""
from __future__ import annotations


# ── 15 kiểu ───────────────────────────────────────────────────────────────────

def test_du_15_kieu_va_KHONG_gop_so_voi_object():
    """`int`/`number`/`bool`/`dict` gộp hết vào `json` là khiếm khuyết đang có."""
    from platform_core.workflow.he_kieu import KIEU_CO_BAN

    assert KIEU_CO_BAN >= {
        "text", "number", "integer", "boolean", "json", "file",
        "image", "video", "audio", "document",
        "model_ref", "connection_ref", "artifact_ref", "workflow_ref",
        "secret_ref",
    }
    # 17, khong phai 15: `any` va `event` them CO CHU DICH o `75cca2cb` theo
    # spec 4.7 (`any` cho cong nhan moi kieu; `event` cho trigger/waitpoint).
    # Con so nay ghim de mot kieu moi phai di qua REVIEW, khong phai de dong bang
    # he kieu — doi no la mot quyet dinh, va day la lan doi thu nhat.
    assert len(KIEU_CO_BAN) == 17
    assert {"any", "event"} <= KIEU_CO_BAN
    # Ba cai nay PHAI khac nhau — do la toan bo diem cua G37.
    assert len({"number", "integer", "json"} & KIEU_CO_BAN) == 3


def test_kieu_tap_hop_la_T_ngoac_vuong():
    from platform_core.workflow.he_kieu import hop_le, la_tap_hop, kieu_phan_tu

    assert hop_le("image[]") and la_tap_hop("image[]")
    assert kieu_phan_tu("image[]") == "image"
    assert not la_tap_hop("image")


def test_kieu_bia_dat_bi_TU_CHOI():
    from platform_core.workflow.he_kieu import hop_le

    assert not hop_le("anh")
    assert not hop_le("image[][]")     # tap hop long nhau: khong co trong khai
    assert not hop_le("")


# ── Ép kiểu: ĐÚNG MỘT luật ───────────────────────────────────────────────────

def test_ep_kieu_CHI_co_T_thanh_T_mang():
    from platform_core.workflow.he_kieu import ep_duoc

    assert ep_duoc("image", "image[]") is True
    assert ep_duoc("text", "text[]") is True


def test_MOI_ep_kieu_khac_bi_TU_CHOI():
    """⛔ `number -> text` phải đặt một node chuyển đổi — nó HIỆN trên đồ thị.

    Ép ngầm là một phép biến đổi **vô hình**: người đọc đồ thị không thấy nó,
    nhưng nó vẫn đổi dữ liệu. Bắt nó thành một node là làm cho thứ đang xảy ra
    trở nên nhìn thấy được.
    """
    from platform_core.workflow.he_kieu import ep_duoc

    assert ep_duoc("number", "text") is False
    assert ep_duoc("integer", "number") is False   # ke ca huong "an toan"
    assert ep_duoc("image[]", "image") is False    # khong tu mo goi
    assert ep_duoc("json", "number") is False


def test_cung_kieu_thi_luon_noi_duoc():
    from platform_core.workflow.he_kieu import ep_duoc

    for k in ("text", "image[]", "model_ref"):
        assert ep_duoc(k, k) is True


# ── Cardinality ──────────────────────────────────────────────────────────────

def test_multiple_KHAC_hoan_toan_voi_kieu_mang():
    """⭐ `multiple` = nhận NHIỀU CẠNH. `image[]` = nhận MỘT MẢNG.

    *"Hôm nay hai thứ này không phân biệt được"* — và chúng khác nhau thật:
    một cổng `image` với `multiple=True` nhận ba cạnh, mỗi cạnh một ảnh; một
    cổng `image[]` nhận **một** cạnh mang một mảng ba ảnh.
    """
    from platform_core.workflow.he_kieu import Cong

    a = Cong(type="image", multiple=True)
    b = Cong(type="image[]", multiple=False)
    assert a.nhan_nhieu_canh() is True and a.la_tap_hop() is False
    assert b.nhan_nhieu_canh() is False and b.la_tap_hop() is True


def test_cong_KHONG_multiple_chi_nhan_MOT_canh():
    from platform_core.workflow.he_kieu import Cong, noi_duoc

    vao = Cong(type="image", multiple=False)
    ra = Cong(type="image")
    assert noi_duoc(ra, vao, so_canh_dang_co=0).duoc is True
    assert noi_duoc(ra, vao, so_canh_dang_co=1).duoc is False


def test_cong_multiple_nhan_duoc_nhieu_canh():
    from platform_core.workflow.he_kieu import Cong, noi_duoc

    vao = Cong(type="image", multiple=True)
    assert noi_duoc(Cong(type="image"), vao, so_canh_dang_co=7).duoc is True


def test_ly_do_TU_CHOI_noi_day_phai_noi_ro_kieu_nao_voi_kieu_nao():
    """Một thông báo "không nối được" không nói gì cho người đang kéo dây."""
    from platform_core.workflow.he_kieu import Cong, noi_duoc

    kq = noi_duoc(Cong(type="number"), Cong(type="text"), so_canh_dang_co=0)
    assert kq.duoc is False
    assert "number" in kq.ly_do and "text" in kq.ly_do


# ── 🔴 M9: MỘT nguồn luật ────────────────────────────────────────────────────

def test_M9_luat_XUAT_duoc_ra_du_lieu_cho_client():
    """Client dựng `connectionAllowed()` TỪ DỮ LIỆU NÀY, không hardcode."""
    from platform_core.workflow.he_kieu import xuat_luat_noi_day

    luat = xuat_luat_noi_day()
    assert set(luat["kieu"]) == set(luat["kieu"])
    assert luat["ep_kieu"] == [["T", "T[]"]], "chi dung MOT luat ep kieu"
    assert len(luat["kieu"]) == 17


def test_M9_client_va_server_TRUNG_KHOP_100_phan_tram():
    """🔴 `M9`: với MỌI cặp (cổng ra, cổng vào), hai bên cho cùng quyết định.

    ⭐ Đây là phép kiểm quan trọng nhất của đợt, và nó chỉ có nghĩa vì phía
    "client" ở đây **dựng lại quyết định TỪ dữ liệu xuất ra**, không gọi lại hàm
    của server. Nếu nó gọi `noi_duoc()` thì bài này chỉ chứng minh một hàm bằng
    chính nó.
    """
    from platform_core.workflow.he_kieu import (KIEU_CO_BAN, Cong, noi_duoc,
                                                xuat_luat_noi_day)

    luat = xuat_luat_noi_day()
    cho_phep = {tuple(c) for c in luat["cap_noi_duoc"]}

    moi_kieu = sorted(KIEU_CO_BAN) + [f"{k}[]" for k in sorted(KIEU_CO_BAN)]
    lech = []
    for ra in moi_kieu:
        for vao in moi_kieu:
            server = noi_duoc(Cong(type=ra), Cong(type=vao),
                              so_canh_dang_co=0).duoc
            client = (ra, vao) in cho_phep
            if server != client:
                lech.append((ra, vao, server, client))

    assert lech == [], f"{len(lech)}/{len(moi_kieu)**2} cap lech: {lech[:5]}"


def test_M9_bang_luat_khong_RONG_va_khong_cho_TAT_CA():
    """Đối chứng cho bài trên: hai bên cũng "trùng khớp 100 %" nếu cả hai đều
    nói *không* với mọi cặp, hoặc *có* với mọi cặp. Bài đó một mình là **xanh
    được vì lý do rỗng**.
    """
    from platform_core.workflow.he_kieu import KIEU_CO_BAN, xuat_luat_noi_day

    cap = xuat_luat_noi_day()["cap_noi_duoc"]
    tong = (len(KIEU_CO_BAN) * 2) ** 2
    assert 0 < len(cap) < tong, (
        f"{len(cap)}/{tong} — bang luat rong hoac cho tat ca thi bai M9 vo nghia")
