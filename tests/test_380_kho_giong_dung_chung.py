"""
Kho giọng **dùng chung của nền tảng** — ai đọc được, và ai KHÔNG sửa được.

Trước 01/09/2026 hệ thống có đúng hai loại giọng và không có gì ở giữa:

  · **Giọng mẫu**     — preset dựng sẵn của engine. Ai cũng dùng, nhưng ta
                        không tạo thêm được cái nào.
  · **Giọng của tôi** — nhân bản, và `giai_giong` kiểm chủ sở hữu ở **một chỗ
                        duy nhất**, nên nó không thể dùng chung.

Nghĩa là một giọng nhân bản hay tới đâu cũng chỉ phục vụ đúng một tài khoản.
`VoiceProfile.dung_chung` mở loại thứ ba: giọng nền tảng sở hữu, mọi khách đọc
được, không khách nào sửa được.

🔴 CỘT NÀY CHẠM DỮ LIỆU SINH TRẮC CỦA MỘT CON NGƯỜI, nên mọi phép kiểm ở đây
   chốt về phía ĐÓNG:

     ① mặc định `False` — một giọng mới không bao giờ tự công khai;
     ② `tim_profile` mặc định KHÔNG thấy kho chung — cửa nào muốn thấy phải
        nói ra, nên mọi lời gọi cũ giữ nguyên hành vi cũ;
     ③ "dùng được" và "sửa được" là hai phép kiểm khác nhau.

⛔ ② quan trọng hơn vẻ ngoài của nó. `tim_profile` là chỗ **duy nhất** kiểm
   quyền sở hữu giọng; nếu mặc định của nó là mở, thì mọi cửa viết sau này —
   kể cả cửa xoá — sẽ vô tình nhìn thấy giọng của người khác, và không có phép
   kiểm thứ hai nào chặn lại.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'voice-chung.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import apps.ltt_voice.tables  # noqa: F401
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    gen = dbmod.get_session()
    s = next(gen)
    try:
        yield s
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
        dbmod.reset_engine()


def _ho_so(db, owner: str, ten: str, dung_chung: bool = False,
            license_status: str | None = None):
    """Dựng một hồ sơ giọng.

    🔴 `dung_chung=True` KÉO THEO `license_status="ok"` — và đó là hợp đồng mới
       từ 08/09/2026 (U-05), không phải một tiện nghi của phép kiểm.

       "Ở kho chung" nay là **hai** điều kiện: nền tảng muốn chia sẻ nó
       (`dung_chung`) **và** xuất xứ đã được soát (`license_status == "ok"`).
       Một fixture chỉ đặt điều kiện thứ nhất rồi mong thấy giọng ấy là một
       fixture mô tả hợp đồng CŨ.

    ⚠️ Truyền `license_status=` tường minh để dựng ca ngược — xem
       `test_kho_chung_CHUA_SOAT_thi_KHONG_AI_thay`.
    """
    from apps.ltt_voice.tables import VoiceProfile

    if license_status is None:
        license_status = "ok" if dung_chung else "cho_soat"
    h = VoiceProfile(owner_id=owner, ten_hien_thi=ten, trang_thai="active",
                     dung_chung=dung_chung, license_status=license_status)
    db.add(h)
    db.flush()
    return h


def test_mac_dinh_KHONG_dung_chung(db):
    """① Một giọng mới không bao giờ tự công khai.

    Không có phép kiểm này thì một lần đổi `default=` sẽ công khai **toàn bộ**
    giọng khách đã tạo, và triệu chứng đầu tiên là một khách nhìn thấy giọng
    của người khác trong bộ chọn của mình.
    """
    h = _ho_so(db, "u1", "Giong cua khach")
    assert h.dung_chung is False


def test_tim_profile_MAC_DINH_khong_thay_kho_chung(db):
    """② Mặc định đóng: mọi lời gọi cũ giữ nguyên hành vi cũ."""
    from apps.ltt_voice import tham_chieu

    chung = _ho_so(db, "nen_tang", "Giong kho chung", dung_chung=True)
    db.commit()

    # Không khai `cho_dung_chung` -> KHÔNG thấy, dù nó là kho chung.
    assert tham_chieu.tim_profile(db, chung.public_id, owner_id="u1") is None
    # Khai rồi thì thấy.
    assert tham_chieu.tim_profile(db, chung.public_id, owner_id="u1",
                                  cho_dung_chung=True) is not None


def test_giong_RIENG_cua_nguoi_khac_van_KHONG_thay_du_da_mo_kho_chung(db):
    """⛔ Mở kho chung KHÔNG được mở luôn giọng riêng của người khác.

    Đây là phép kiểm quan trọng nhất tệp này. Một bản vá viết vội rất dễ thành
    "nếu `cho_dung_chung` thì bỏ điều kiện chủ sở hữu" — và khi đó bất kỳ ai
    biết một `public_id` đều dùng được giọng của người ta.
    """
    from apps.ltt_voice import tham_chieu

    rieng = _ho_so(db, "u2", "Giong rieng cua u2", dung_chung=False)
    db.commit()

    assert tham_chieu.tim_profile(db, rieng.public_id, owner_id="u1",
                                  cho_dung_chung=True) is None
    assert tham_chieu.tim_profile(db, rieng.public_id, owner_id="u2",
                                  cho_dung_chung=True) is not None


def test_DUNG_duoc_khong_phai_SUA_duoc(db):
    """③ Hai câu hỏi khác nhau, hai phép kiểm khác nhau.

    Gộp chúng lại là cách khách đầu tiên bấm "Tắt giọng này" tắt nó cho **toàn
    bộ nền tảng**.
    """
    from apps.ltt_voice import tham_chieu

    chung = _ho_so(db, "nen_tang", "Giong kho chung", dung_chung=True)
    db.commit()

    # DÙNG: được.
    assert tham_chieu.tim_profile(db, chung.public_id, owner_id="u1",
                                  cho_dung_chung=True) is not None
    # SỬA: không.
    assert tham_chieu.chi_chu_so_huu(chung, "u1") is False
    assert tham_chieu.chi_chu_so_huu(chung, "nen_tang") is True


def test_cua_TAT_GIONG_khong_bao_gio_mo_kho_chung():
    """Bánh cóc đọc thẳng mã nguồn của cửa tắt giọng.

    Ba phép trên chốt *cơ chế*; phép này chốt rằng **cửa thật** dùng đúng cơ
    chế ấy. Chúng khác nhau: cơ chế có thể đúng trong khi một cửa cụ thể gọi
    sai, và cửa tắt giọng là cửa mà gọi sai thì hỏng cho tất cả mọi người.
    """
    import ast
    import inspect

    from apps.ltt_voice.routes import _p_giong

    # ⛔ ĐỌC CÂY CÚ PHÁP, KHÔNG TÌM CHUỖI.
    #
    #    Bản đầu làm `assert "cho_dung_chung" not in than` trên mã nguồn thô, và
    #    nó ĐỎ ngay — vì chính lời giải thích trong hàm ấy viết *"KHÔNG
    #    `cho_dung_chung` ở đây"*. Bánh cóc khớp phải câu văn của chính nó.
    #
    # ⭐ Lần thứ ba trong ngày cùng một hình dạng (`test_353` đã dính đúng thế
    #    với `_asr`). Cách sửa bền không phải "bỏ chữ đó khỏi chú thích" — làm
    #    vậy là để phép kiểm sai điều khiển cách ta viết chú thích. Là **hỏi
    #    đúng thứ mình muốn hỏi**: lời gọi ấy truyền tham số nào.
    cay = ast.parse(inspect.getsource(_p_giong))
    ham = [n for n in ast.walk(cay)
           if isinstance(n, ast.FunctionDef) and n.name == "tat_giong"]
    assert ham, "khong tim thay cua tat giong"

    goi = [n for n in ast.walk(ham[0]) if isinstance(n, ast.Call)
           and isinstance(n.func, ast.Attribute) and n.func.attr == "tim_profile"]
    assert goi, "cua tat giong khong tra ho so?"
    for g in goi:
        khoa = {k.arg for k in g.keywords}
        assert "cho_dung_chung" not in khoa, (
            "cua TAT GIONG dang mo kho chung — mot khach se tat duoc giong cua "
            "ca nen tang")
        assert "owner_id" in khoa, "cua tat giong khong kiem chu so huu"


def test_danh_sach_MAC_DINH_khong_gom_kho_chung(db):
    """Danh sách cũng mặc định đóng, cùng lý do."""
    from apps.ltt_voice import tham_chieu

    _ho_so(db, "u1", "Cua toi")
    _ho_so(db, "nen_tang", "Kho chung", dung_chung=True)
    db.commit()

    assert len(tham_chieu.danh_sach(db, owner_id="u1")) == 1
    ca = tham_chieu.danh_sach(db, owner_id="u1", gom_dung_chung=True)
    assert len(ca) == 2
    # Giọng của chính khách đứng TRƯỚC kho chung — thứ họ tự tạo là thứ họ tìm.
    assert ca[0].dung_chung is False
# ── ⑤ U-05: `dung_chung` MỘT MÌNH không đủ ──────────────────────────────────
#
# ⭐ Mục này là vế **đối xứng** của cả tệp, và nó phải có mặt vì bốn phép kiểm
#    trên vừa được sửa fixture để đặt `license_status="ok"`. Sửa fixture cho một
#    lượt đỏ xanh lại là thao tác dễ mắc lỗi nhất trong cả kho: nó làm phép kiểm
#    **dễ xanh hơn**, và nếu chỉ có thế thì cổng U-05 sẽ không còn ai canh.
#
# ⇒ Hai phép kiểm dưới đây chốt đúng phần vừa được thêm vào hợp đồng.

def test_kho_chung_CHUA_SOAT_thi_KHONG_AI_thay(db):
    """🔴 Xuất xứ chưa soát ⇒ giọng KHÔNG ra kho chung, dù cờ `dung_chung` đã bật.

    Bản kiểm toán 07/09/2026 viết ranh giới bằng một câu: *"tải được ≠ dùng
    thương mại được"*. Đây là chỗ câu ấy thành một hành vi quan sát được.
    """
    from apps.ltt_voice import tham_chieu

    chung = _ho_so(db, "nen_tang", "Chua soat", dung_chung=True,
                   license_status="cho_soat")
    db.commit()

    assert tham_chieu.tim_profile(db, chung.public_id, owner_id="u1",
                                  cho_dung_chung=True) is None
    ca = tham_chieu.danh_sach(db, owner_id="u1", gom_dung_chung=True)
    assert chung.public_id not in {g.public_id for g in ca}


@pytest.mark.parametrize("trang_thai", ["cho_soat", "thieu_bang_chung",
                                        "tu_choi", "", "OK", "trang_thai_moi"])
def test_chi_DUNG_chuoi_ok_moi_qua_cong(db, trang_thai):
    """⛔ Danh sách CHO, không phải danh sách CẤM.

    Dòng `"trang_thai_moi"` là dòng quan trọng nhất: nó là cái sẽ tồn tại vào
    ngày có người thêm một trạng thái license và quên cổng này. Với
    danh-sách-cấm nó **lọt qua** (mở, im lặng); với danh-sách-cho nó bị chặn cho
    tới khi có người cố ý thêm vào.
    """
    from apps.ltt_voice import tham_chieu

    g = _ho_so(db, "nen_tang", f"Giong {trang_thai or 'rong'}",
               dung_chung=True, license_status=trang_thai)
    db.commit()
    assert tham_chieu.tim_profile(db, g.public_id, owner_id="u1",
                                  cho_dung_chung=True) is None


def test_SUA_van_chi_chu_so_huu_du_da_soat(db):
    """⚠️ Cổng U-05 chỉ gác đường **ĐỌC**. Nó không được nới quyền SỬA.

    Gộp hai câu ấy là cách một khách tắt mất giọng của cả nền tảng — chính là
    lỗi mà `chi_chu_so_huu` sinh ra để chặn, và một cột mới không được phép
    mở lại nó.
    """
    from apps.ltt_voice import tham_chieu

    chung = _ho_so(db, "nen_tang", "Da soat", dung_chung=True)
    db.commit()
    ho_so = tham_chieu.tim_profile(db, chung.public_id, owner_id="u1",
                                   cho_dung_chung=True)
    assert ho_so is not None, "giong da soat ma van khong doc duoc"
    assert tham_chieu.chi_chu_so_huu(ho_so, "u1") is False
    assert tham_chieu.chi_chu_so_huu(ho_so, "nen_tang") is True
