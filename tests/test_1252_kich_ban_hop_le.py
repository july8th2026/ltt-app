"""test_1252 — ma tran kich ban la DU LIEU, va du lieu phai tu nhat quan.

⭐ Nguyen tac: **moi kich ban phai CO KHA NANG HONG theo mot cach noi len dieu
   gi do.** Mot kich ban khong the do thi khong chung minh gi — dung lop "cua
   gia" trong so tay du an.

## ⚠️ Mot khang dinh cua plan da bi SO DO BAC

Plan khai `assert can_tai_khoan_hai == ["X2"]` — *"chi X2 can tai khoan thu
hai"*. Do 13/09 tren production noi khac: tran tai khoan (`ceil(3/2)=2`) **chi
bat khi co TAI KHOAN KHAC dang cho**:

    nguoi_khac_cho = any(c.user_id != l.user_id for c in dang_cho ...)
    if not nguoi_khac_cho: return False      # khong ai khac cho => KHONG ap tran

Nen J7 (cong bang) va J10 (whale) deu **phai** co >= 2 tai khoan; chay mot tai
khoan thi tran khong bat va ta do ra mot con so khong thuoc kich ban nao.

⇒ Ve nay bo danh sach cung, thay bang mot BAT BIEN: kich ban nao khai ky vong
  ve CONG BANG thi bat buoc phai danh dau `can_tai_khoan_hai`.
"""
from tools.nghiem_thu_van_hanh import kich_ban as kb

#: Khoa `mong_doi` chi mot ky vong ve CONG BANG giua cac tai khoan.
KHOA_CONG_BANG = ("tran_tai_khoan", "moi_tai_khoan_toi_da", "khong_cho_trang")


def test_du_16_kich_ban():
    assert len(kb.MA_TRAN) == 16


def test_ma_KHONG_trung():
    ma = [k.ma for k in kb.MA_TRAN]
    assert len(ma) == len(set(ma)), f"ma trung: {ma}"


def test_moi_kich_ban_co_MONG_DOI_kiem_duoc():
    """Khong mong doi = khong the do. Mot dong khai suong."""
    for k in kb.MA_TRAN:
        assert k.mong_doi, f"{k.ma} khong khai mong doi"


def test_tai_vuot_tran_thi_phai_khai_SO_LUOT_XEP_HANG():
    """Tran la 3 moi model. Vuot thi phai noi ro bao nhieu luot PHAI cho."""
    for k in kb.MA_TRAN:
        tong = {}
        for model, n in k.tai:
            tong[model] = tong.get(model, 0) + n
        for model, n in tong.items():
            if n > kb.TRAN_MOI_MODEL:
                assert "queued" in k.mong_doi, (
                    f"{k.ma} nop {n} luot cho {model} (tran {kb.TRAN_MOI_MODEL}) "
                    "ma khong khai so luot phai xep hang — khong the do duoc")


def test_ky_vong_CONG_BANG_thi_bat_buoc_hai_tai_khoan():
    """🔴 Ve thay cho danh sach cung cua plan.

    Chay mot kich ban cong bang bang MOT tai khoan thi tran khong bat, va con
    so do duoc khong thuoc kich ban nao ca.
    """
    for k in kb.MA_TRAN:
        if any(x in k.mong_doi for x in KHOA_CONG_BANG):
            assert k.can_tai_khoan_hai, (
                f"{k.ma} khai ky vong ve cong bang nhung khong danh dau "
                "`can_tai_khoan_hai` — tran tai khoan chi bat khi co TAI KHOAN "
                "KHAC dang cho, nen chay mot tai khoan se do nham.")


def test_kiem_hop_le_KHONG_bao_loi_tren_ma_tran_that():
    assert kb.kiem_hop_le(kb.MA_TRAN) == []


def test_kiem_hop_le_BAT_duoc_ky_vong_cong_bang_THIEU_DANH_DAU():
    """🔴 Vế này thêm sau khi một ĐỐI CHỨNG không đỏ.

    Ban đầu chỉ có `test_ky_vong_CONG_BANG_...` — nhưng nó soi **dữ liệu**
    `MA_TRAN`, không soi **hàm** `kiem_hop_le`. Gỡ hẳn luật công bằng ra khỏi
    hàm thì cả bộ vẫn XANH: luật nằm trong mã mà không phép kiểm nào phủ.

    ⛔ Đúng lớp *"bánh cóc chỉ bảo vệ thứ nó nhìn thấy"*. Vế này soi chính hàm.
    """
    hong = kb.KichBan("YY", "khai cong bang ma quen danh dau", "stream",
                      (("ltt-3.8", 2),), {"tran_tai_khoan": 2})
    loi = kb.kiem_hop_le([hong])
    assert any("YY" in x and "can_tai_khoan_hai" in x for x in loi), (
        f"`kiem_hop_le` khong bat duoc ky vong cong bang thieu danh dau: {loi}")


def test_kiem_hop_le_BAT_duoc_kich_ban_hong():
    """⛔ Doi chung cho chinh bo kiem: no phai DO duoc, khong chi luon tra []."""
    hong = kb.KichBan("ZZ", "khong khai mong doi", "stream",
                      (("ltt-3.8", 9),), {})
    loi = kb.kiem_hop_le([hong])
    assert loi, "kiem_hop_le khong bat duoc mot kich ban ro rang la hong"
    assert any("ZZ" in x for x in loi)


def test_moi_kich_ban_tro_dung_MOT_cua_hop_le():
    for k in kb.MA_TRAN:
        assert k.cua in ("job", "stream", "dong_bo"), f"{k.ma}: cua={k.cua!r}"


def test_TRAN_lay_tu_ban_khai_chu_khong_go_tay():
    """Hai cho khai cung mot dieu ma khong ai bat khop — khuon da can du an nay."""
    from platform_core.runtime_noi_bo.luong import tim_tool

    _m, tool = tim_tool("text.chat")
    that = {tool.admission_cho(m).slots for m in ("ltt-3.8", "ltt-3.5")}
    assert that == {kb.TRAN_MOI_MODEL}, (
        f"ban khai noi {that}, kich_ban.py go tay {kb.TRAN_MOI_MODEL}")
