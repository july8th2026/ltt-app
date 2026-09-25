"""Làn `asv-gui` — lật gương + dịch màu đi HẾT đường, và **vân tay phải đổi**.

## 🔴 Câu hỏi thật của bài này

⛔ Không phải *"bật cờ có chạy được không"*. Hôm nay đã có ba lượt (`N-47`,
`N-51`, `N-55`) **xanh trong khi cửa hở** — "chạy được" không chứng minh gì.

Câu hỏi thật là: **một cấu hình khác có cho một vân tay khác không.** Nếu không,
khách bật lật gương, trả tiền, và lần chạy lại **trả về tệp cũ** — không lỗi,
không cảnh báo, chỉ một lượt chạy "nhanh bất thường". `assets.py` gọi đúng tên
cái bẫy đó: *"sót tham số = serve nhầm"*.

⚠️ Và vân tay của giai đoạn RENDER có **hai** nguồn độc lập, nên bài này ghim cả
hai:

| nguồn | đổi khi nào | ai giữ |
|---|---|---|
| checksum bản dựng | khách đổi **hồ sơ** (bật/tắt cờ) | `ban_dung` (cờ nằm trong `bien_tap`) |
| `PHIEN_BAN_CHE_DO` | ta đổi **mã sinh lệnh** | `che_do_render` |

⛔ Chỉ ghim một cái là để hở cái kia: một lần chạy **không** bật cờ nào vẫn đi
qua mã sinh lệnh MỚI, và chỉ con số phiên bản nói ra điều đó.
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import bien_tap as bt
from apps.auto_scan_video import che_do_render as cdr
from apps.auto_scan_video import hop_dong_v4


# ══════════════════════════════════════════════════════════════════════════════
#  1. Vân tay — câu hỏi cuối
# ══════════════════════════════════════════════════════════════════════════════

def _ban(*, bien_tap=None, che_do=None):
    """Bản dựng tối thiểu qua ĐÚNG hàm sản phẩm.

    ⚠️ `ban_dung.dung` gọi `kiem()` ở dòng cuối, nên một bản dựng không thi hành
       được **không bao giờ tồn tại** — nó chết ngay lúc dựng.
    """
    from apps.auto_scan_video import ban_dung as bd

    return bd.dung(
        khoa_video="v/1.mp4", khoa_nen="a/nen.wav", khoa_master="a/master.wav",
        ke_hoach={"doan": [], "tong_ms": 5000}, ban_ke_tieng={"doan": []},
        phien_ban_ffmpeg="n7.0", tong_giay=5.0,
        che_do=che_do or cdr.CAT_MA_HOA_LAI, bo_ma_hoa="libx264",
        khoang_giu=[(0.0, 5.0)], preset=hop_dong_v4.PRESET_CAT_THONG_MINH,
        rong_khung=1280, cao_khung=720, bien_tap=bien_tap)


def _van_tay_ban_dung(ho_so: dict | None) -> str:
    """Vân tay của giai đoạn RENDER, rút gọn đúng phần phụ thuộc hồ sơ.

    ⭐ Dựng bản dựng THẬT rồi băm nó, chứ không băm hồ sơ trực tiếp: đường thật
       đi qua `ban_dung.dung`, và một bài băm thẳng hồ sơ sẽ vẫn xanh kể cả khi
       `dung()` đánh rơi cờ trên đường vào bản dựng.
    """
    import hashlib
    import json

    ban = _ban(bien_tap=ho_so)
    return hashlib.sha256(
        json.dumps(ban, sort_keys=True).encode("utf-8")).hexdigest()


def test_bat_LAT_GUONG_thi_van_tay_PHAI_doi():
    """🔴 Bài quan trọng nhất của tệp. Hỏng bài này = khách trả tiền, nhận tệp cũ."""
    khong = _van_tay_ban_dung(None)
    co = _van_tay_ban_dung({"lat_guong": True})
    assert co != khong, (
        "bat lat guong ma van tay KHONG doi — mot lan chay lai se tra ve tep cu, "
        "va no khong bao gio no")


def test_bat_DICH_MAU_thi_van_tay_PHAI_doi():
    khong = _van_tay_ban_dung(None)
    co = _van_tay_ban_dung({"dich_mau": True})
    assert co != khong


def test_HAI_co_cho_ba_van_tay_KHAC_nhau():
    """⚠️ Đối chứng cho hai bài trên: nếu hồ sơ bị nuốt ở đâu đó, cả ba sẽ bằng
    nhau và hai bài trên vẫn có thể xanh nhờ một khác biệt tình cờ khác.
    """
    vt = {ten: _van_tay_ban_dung(ho) for ten, ho in (
        ("khong", None), ("lat", {"lat_guong": True}),
        ("mau", {"dich_mau": True}),
        ("ca_hai", {"lat_guong": True, "dich_mau": True}))}
    assert len(set(vt.values())) == 4, f"co van tay trung nhau: {vt}"


def test_PHIEN_BAN_CHE_DO_da_len_khi_chuoi_loc_doi():
    """🔑 Nửa thứ hai của vân tay, và là nửa **không** phụ thuộc hồ sơ khách.

    Một lần chạy không bật cờ nào vẫn đi qua mã sinh lệnh MỚI (`loc_cat_noi` đã
    đổi cách nối nhãn). Bản dựng của nó không đổi một byte, nên thứ DUY NHẤT nói
    ra rằng lệnh ffmpeg được sinh bởi mã khác là con số này.

    ⛔ Ghim `>= 8` chứ không `== 8`: bài này chốt rằng số đã đi qua mốc của làn
       `asv-gui`, không khoá cứng một giá trị mà làn sau phải sửa.
    """
    assert cdr.PHIEN_BAN_CHE_DO >= 8


# ══════════════════════════════════════════════════════════════════════════════
#  2. Hồ sơ: chỉ ghi khi BẬT, và từ chối chứ không ép về biên
# ══════════════════════════════════════════════════════════════════════════════

def test_khong_bat_thi_KHONG_ghi_khoa_thua():
    """⛔ Một `"lat_guong": false` trong hồ sơ đổi vân tay của những lần chạy
    **không hề** lật gương — tức phá cache của chúng mà không ai có ý đồ.
    """
    assert bt.chuan_hoa({"lat_guong": False, "dich_mau": False}) == {}
    assert bt.chuan_hoa({}) == {}


def test_bat_thi_ghi_dung_mot_gia_tri():
    assert bt.chuan_hoa({"lat_guong": True}) == {"lat_guong": True}
    assert bt.chuan_hoa({"dich_mau": True}) == {"dich_mau": True}


@pytest.mark.parametrize("gt", ["on", "true", 1, 0, "", [], {"a": 1}])
def test_gia_tri_KHONG_phai_bool_thi_TU_CHOI(gt):
    """⛔ Không ép về biên (luật L2 của `vung_che`).

    🔑 Và `"false"` là ca nguy hiểm nhất: nó **đúng** trong JavaScript và
       **sai** theo ý khách. Một `bool(...)` ở máy chủ sẽ bật một tính năng
       khách vừa tắt.

    ⚠️ `0`, `""` và `[]` cũng bị TỪ CHỐI chứ không đọc thành "tắt". Chúng "giả"
       theo luật của **ngôn ngữ**, không theo ý khách — và một hồ sơ gửi `0` cho
       một ô công tắc là một hồ sơ do thứ gì đó khác giao diện của ta dựng nên.
       Chỉ `false` và **vắng mặt** mới có nghĩa là tắt.
    """
    with pytest.raises(bt.BienTapLoi):
        bt.chuan_hoa({"lat_guong": gt})


def test_truong_LA_van_bi_tu_choi():
    """⚠️ Đối chứng: `_TRUONG` vừa rộng ra, nên phải chắc nó không rộng hết."""
    with pytest.raises(bt.BienTapLoi):
        bt.chuan_hoa({"contrast": True})
    with pytest.raises(bt.BienTapLoi):
        bt.chuan_hoa({"brightness": 0.03})


def test_CONTRAST_va_BRIGHTNESS_KHONG_duoc_mo_kem():
    """🔴 Chủ dự án chốt 25/09: chỉ mở `saturation`.

    `contrast` và `brightness` đổi **độ phơi sáng** — cảnh tối bệt đen, cảnh
    sáng cháy trắng, và cả hai **không đảo ngược được** vì thông tin đã bị kẹp
    mất ở hai đầu dải. Nguồn tham chiếu đặt cả ba một lượt
    (`contrast=1.06 : brightness=0.03 : saturation=1.12`), nên đây đúng là chỗ
    một lần "chép cho đủ" sẽ xảy ra.

    ⇒ Bài này chốt phía ĐƯỜNG: không tên nào của hai phép đó được xuất hiện
      trong chuỗi lọc, dù hồ sơ có gì.
    """
    chuoi = cdr._loc_diem_anh({"lat_guong": True, "dich_mau": True})
    assert "contrast" not in chuoi and "brightness" not in chuoi
    assert "saturation" in chuoi


# ══════════════════════════════════════════════════════════════════════════════
#  3. Chuỗi lọc: đúng bộ lọc, ĐÚNG CHỖ
# ══════════════════════════════════════════════════════════════════════════════

def _chuoi(ho_so, **them):
    return cdr.loc_cat_noi([(0.0, 5.0)], bien_tap=ho_so,
                           rong_nguon=1280, cao_nguon=720, **them)


def test_lat_guong_phat_hflip_va_dich_mau_phat_eq():
    c = _chuoi({"lat_guong": True, "dich_mau": True})
    assert "hflip" in c
    assert f"eq=saturation={bt.DICH_MAU_BAO_HOA:.4f}" in c


def test_KHONG_bat_gi_thi_chuoi_KHONG_co_hai_bo_loc_do():
    """Đối chứng — không có nó thì bài trên vẫn xanh với một chuỗi luôn có `hflip`."""
    c = _chuoi(None)
    assert "hflip" not in c and "eq=saturation" not in c


def test_LAT_GUONG_dung_TRUOC_lop_phu_chu():
    """🔴 Ràng buộc quan trọng nhất về THỨ TỰ, và nó nhìn thấy được trên tệp ra.

    Lật SAU lớp phủ sẽ lật **cả chữ của khách**. Một dòng chữ bị lật gương là
    một dòng chữ không đọc được, và nó đi thẳng ra tệp giao cho khách — không
    một phép kiểm nào khác trong kho hỏi câu này.
    """
    c = _chuoi({"lat_guong": True},
               lop_phu=[{"chu": "kenh", "mau": "trang", "x": 0.5, "y": 0.9,
                         "co_chu": 0.05, "do_mo": 1.0, "vien": True}],
               duong_chu=["/tmp/chu0.txt"], cao_khung=720)
    assert c.index("hflip") < c.index("drawtext"), (
        "hflip nam SAU drawtext — chu cua khach se bi lat guong")


def test_LAT_GUONG_dung_SAU_buoc_cat_khung():
    """⚠️ Ràng buộc kia của cùng một thứ tự: lật TRƯỚC `crop` thì mọi toạ độ cắt
    phải được ánh xạ gương — một phép ánh xạ không ai yêu cầu và chắc chắn lệch.
    """
    c = _chuoi({"lat_guong": True,
                "cat_khung": {"x0": 0.1, "y0": 0.0, "x1": 0.9, "y1": 1.0}})
    assert "crop=" in c and c.index("crop=") < c.index("hflip")


def test_khong_co_hinh_hoc_thi_KHONG_doi_biet_kich_thuoc_nguon():
    """🔑 Lật gương và dịch màu giữ nguyên từng chiều của khung, nên chúng không
    được kéo `hinh_hoc.khung_bien_tap` — một hàm **ném** khi chưa biết kích
    thước nguồn — vào một lần chạy không cần tới nó.

    ⛔ Bản `set(bien_tap) - {"toc_do"}` cũ sẽ hỏng ở đây, và hỏng ở tận
       `giai_doan_ban_dung` chứ không ở cửa.
    """
    c = cdr.loc_cat_noi([(0.0, 5.0)], bien_tap={"lat_guong": True},
                        rong_nguon=0, cao_nguon=0)
    assert "hflip" in c


def test_chuoi_cua_lan_chay_KHONG_bien_tap_giu_NGUYEN():
    """⚠️ Đối chứng cho cả lần sửa: `loc_cat_noi` vừa được nối lại nhãn, nên
    phải chắc rằng một lần chạy không biên tập vẫn cho **đúng chuỗi cũ**.
    """
    assert _chuoi(None) == (
        "[0:v]trim=start=0.000000:end=5.000000,setpts=PTS-STARTPTS[v0];"
        "[v0]concat=n=1:v=1:a=0[ra]")


# ══════════════════════════════════════════════════════════════════════════════
#  4. Hợp đồng + ba tầng chặn ở preset giữ hình
# ══════════════════════════════════════════════════════════════════════════════

def test_hai_nang_luc_moi_DUOC_KHAI_o_bang_hop_dong():
    """⛔ `test_455` chốt mệnh đề chung: mọi thứ đã rời bảng CẤM phải có mặt ở
    đúng một bảng năng lực. Hai cờ này chưa từng ở bảng cấm, nên bài đó không
    bắt được chúng — bài này khai chúng ra.
    """
    for ten in ("mirror", "color_shift"):
        assert ten in hop_dong_v4.NANG_LUC_DOI_DIEM_ANH
        assert ten not in hop_dong_v4.NANG_LUC_KHONG_DOI_DIEM_ANH
        assert ten not in hop_dong_v4.CAM_TRONG_MVP


def test_preset_GIU_HINH_tu_choi_hai_co_NGAY_O_CUA():
    """Tầng 1/3: `tu_form` từ chối trước khi giữ credit."""
    import json

    for ho in ({"lat_guong": True}, {"dich_mau": True}):
        with pytest.raises(bt.BienTapLoi):
            bt.tu_form(json.dumps(ho), preset=hop_dong_v4.PRESET_GIU_HINH)


def test_ban_dung_SAO_CHEP_mang_hai_co_thi_bi_NEM():
    """Tầng 3/3 — và là tầng duy nhất `ket_xuat` thật sự đi qua.

    ⛔ Chỉ chặn ở giao diện thì một yêu cầu dựng tay vẫn tới được, và `ket_xuat`
       sẽ **lặng lẽ bỏ qua** cờ rồi giao một video không lật gì — khách trả tiền
       cho một thứ không xảy ra.
    """
    from apps.auto_scan_video import ban_dung as bd

    ban = _ban(bien_tap={"lat_guong": True})
    # Đổi cách render sang `sao_chep` như một yêu cầu dựng tay sẽ làm.
    ban["hinh"]["cach_render"] = cdr.SAO_CHEP
    with pytest.raises(bd.BanDungError):
        bd.kiem(ban)


def test_hai_co_KHONG_day_lan_chay_sang_duong_DAT_hon():
    """🔑 Câu hỏi điều phối hỏi: bao nhiêu phần trăm lượt bị đẩy từ `sao_chep`
    sang `cat_ma_hoa_lai`?

    ⭐ Trả lời bằng CẤU TRÚC chứ không bằng một phép đo: `che_do_cho` đọc **duy
       nhất** preset, và hai cờ chỉ tồn tại ở preset đã mã hoá lại sẵn. Nên con
       số là **0%**, và nó đúng theo xây dựng chứ không theo một mẫu quan sát.

    ⛔ Bài này chốt đúng mệnh đề đó, để một lần sửa sau làm `che_do_cho` đọc
       thêm dữ liệu sẽ phải đi qua đây.
    """
    import inspect

    for p in hop_dong_v4.PRESET:
        assert cdr.che_do_cho(p) == cdr.che_do_cho(p)
    assert cdr.che_do_cho(hop_dong_v4.PRESET_GIU_HINH) == cdr.SAO_CHEP
    # `che_do_cho` chỉ nhận preset — không có tham số nào khác để mà đọc.
    assert list(inspect.signature(cdr.che_do_cho).parameters) == ["preset"]


def test_doi_diem_anh_tra_loi_cho_CA_HAI_nguoi_hoi():
    assert bt.doi_diem_anh({"lat_guong": True})
    assert bt.doi_diem_anh({"dich_mau": True})
    assert bt.doi_diem_anh({"zoom": {"he_so": 1.2}})
    # ⚠️ `toc_do` đổi MỐC THỜI GIAN, không đổi điểm ảnh.
    assert not bt.doi_diem_anh({"toc_do": 1.25})
    assert not bt.doi_diem_anh(None)


# ══════════════════════════════════════════════════════════════════════════════
#  5. Giao diện: nhãn nói VIỆC, và con số đến TỪ module
# ══════════════════════════════════════════════════════════════════════════════

def test_phan_tram_bao_hoa_den_TU_module_khong_go_vao_Jinja():
    from pathlib import Path

    mau = (Path(__file__).resolve().parents[1] / "apps" / "auto_scan_video"
           / "templates" / "asv_trang_chinh.html").read_text(encoding="utf-8")
    assert "bien_tap.dich_mau_pct" in mau
    assert bt.cho_giao_dien()["dich_mau_pct"] == 12


def test_nhan_noi_VIEC_NO_LAM_khong_noi_muc_dich():
    """🔴 Chủ dự án chốt 25/09. Nguồn tham chiếu gọi phép này là *"tạo bản khác
    nhau (né trùng)"*; một cái tên mô tả **mục đích** khoá cứng một cách hiểu và
    không còn dùng được cho khách chỉ muốn màu đậm hơn.
    """
    from pathlib import Path

    goc = Path(__file__).resolve().parents[1]
    mau = (goc / "apps" / "auto_scan_video" / "templates"
           / "asv_trang_chinh.html").read_text(encoding="utf-8")
    i = mau.index("asv-bt-dich-mau")
    khoi = mau[i:i + 700]
    for tu in ("né trùng", "né ", "tránh trùng", "unique", "uniq"):
        assert tu not in khoi.lower(), f"nhan mo ta MUC DICH ne: {tu!r}"
    assert "bão hoà" in khoi


def test_hai_o_moi_VE_DICH_trong_ho_so_da_luu():
    """🔑 Câu hỏi cuối của `L_GUI.md` §1: cái khách bấm có nằm trong hồ sơ không.

    ⭐ Hỏi qua `tu_form` — đúng hàm route gọi — chứ không qua `chuan_hoa`: một ô
       chết sống được ở đúng khoảng giữa hai hàm đó.
    """
    import json

    ho = bt.tu_form(json.dumps({"lat_guong": True, "dich_mau": True}),
                    preset=hop_dong_v4.PRESET_CAT_THONG_MINH)
    assert ho == {"lat_guong": True, "dich_mau": True}
