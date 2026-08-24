"""
test_247 — bộ so mù của H37 (`tools/cham_mu.py`).

Bộ này quyết định model nào được chọn, nên nó phải đúng trước khi có một tấm ảnh
nào được sinh ra. Mỗi test dưới đây chốt một luật ở
`docs/ANH_NOI_BO/KE_HOACH_THI_HANH.md` §1.5.
"""
from __future__ import annotations

import json
import random

import pytest

from tools.cham_mu import (SO_CAP_TOI_THIEU, TEN_ANH, TEN_KHOA, TEN_MAN,
                           TEN_PHIEU, Cap, ghi_lo, ghi_man, main, tao_lo, tinh,
                           wilson)


def _caps(n_that: int, n_bay: int = 0) -> list[Cap]:
    caps = [Cap(f"c{i}", "l.png", "r.png", "A", "B", False) for i in range(n_that)]
    caps += [Cap(f"b{i}", "l.png", "r.png", "A", "A", True) for i in range(n_bay)]
    return caps


def _phieu(caps, *, a_thang=0, b_thang=0, hoa=0, bay_quyet=0, bay_trai=None):
    """Dựng phiếu theo số lượng mong muốn. `bay_trai` mặc định chia đều."""
    ra: dict[str, str] = {}
    that = [c for c in caps if not c.la_bay]
    i = 0
    for _ in range(a_thang):
        ra[that[i].ma] = "trai" if that[i].nguon_trai == "A" else "phai"
        i += 1
    for _ in range(b_thang):
        ra[that[i].ma] = "trai" if that[i].nguon_trai == "B" else "phai"
        i += 1
    for _ in range(hoa):
        ra[that[i].ma] = "hoa"
        i += 1
    bay = [c for c in caps if c.la_bay]
    if bay_trai is None:
        bay_trai = bay_quyet // 2
    for j, c in enumerate(bay):
        if j < bay_quyet:
            ra[c.ma] = "trai" if j < bay_trai else "phai"
        else:
            ra[c.ma] = "hoa"
    return ra


# ───────────────────────── dựng lô ──────────────────────────────────────────
def test_lo_co_du_cap_that_va_cap_bay():
    caps = tao_lo([f"a{i}.png" for i in range(20)],
                  [f"b{i}.png" for i in range(20)],
                  ty_le_bay=0.1, rng=random.Random(1))
    assert sum(1 for c in caps if not c.la_bay) == 20
    assert sum(1 for c in caps if c.la_bay) == 2


def test_cap_bay_ghep_hai_anh_CUNG_nguon():
    caps = tao_lo([f"a{i}.png" for i in range(10)], [f"b{i}.png" for i in range(10)],
                  ty_le_bay=0.4, rng=random.Random(2))
    bay = [c for c in caps if c.la_bay]
    assert bay and all(c.nguon_trai == c.nguon_phai for c in bay)
    # Và hai ảnh phải KHÁC nhau — ghép một ảnh với chính nó thì người chấm nhìn ra ngay.
    assert all(c.trai != c.phai for c in bay)


def test_trai_phai_duoc_xao_khong_ben_nao_co_dinh():
    caps = tao_lo([f"a{i}.png" for i in range(60)], [f"b{i}.png" for i in range(60)],
                  ty_le_bay=0.0, rng=random.Random(3))
    a_ben_trai = sum(1 for c in caps if c.nguon_trai == "A")
    assert 15 < a_ben_trai < 45      # không phải lúc nào A cũng nằm một phía


def test_ghi_lo_doi_ten_anh_va_KHONG_de_lo_nguon(tmp_path):
    """Một chữ 'hidream' sót trong tên tệp là đủ huỷ tính mù của cả lô."""
    src_a, src_b = tmp_path / "hidream_o1", tmp_path / "gemini_3_pro"
    for d in (src_a, src_b):
        d.mkdir()
        for i in range(3):
            (d / f"{d.name}_{i}.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    caps = tao_lo([str(p) for p in sorted(src_a.iterdir())],
                  [str(p) for p in sorted(src_b.iterdir())],
                  ty_le_bay=0.0, rng=random.Random(4))
    lo = tmp_path / "lo1"
    ghi_lo(caps, lo, nhan_a="hidream_o1", nhan_b="gemini_3_pro")

    ten = [p.name for p in (lo / TEN_ANH).iterdir()]
    assert ten and all("hidream" not in t and "gemini" not in t for t in ten)
    # Phiếu cũng không được lộ nhãn.
    assert "hidream" not in (lo / TEN_PHIEU).read_text(encoding="utf-8")
    # Nhãn chỉ nằm trong tệp khoá, và tệp khoá có cảnh báo.
    khoa = json.loads((lo / TEN_KHOA).read_text(encoding="utf-8"))
    assert khoa["nhan"]["A"] == "hidream_o1"


def test_ghi_lo_ghi_utf8_khong_bom(tmp_path):
    """Quy tắc 1 của CLAUDE.md — BOM đã từng làm sập production dự án này."""
    src = tmp_path / "s"
    src.mkdir()
    for i in range(2):
        (src / f"x{i}.png").write_bytes(b"\x89PNG")
    caps = tao_lo([str(src / "x0.png")], [str(src / "x1.png")],
                  ty_le_bay=0.0, rng=random.Random(5))
    lo = tmp_path / "lo"
    ghi_lo(caps, lo, nhan_a="A", nhan_b="B")
    assert not (lo / TEN_PHIEU).read_bytes().startswith(b"\xef\xbb\xbf")


# ───────────────────────── thống kê ─────────────────────────────────────────
def test_wilson_khong_bao_gio_ra_ngoai_0_1():
    for k, n in ((0, 1), (1, 1), (0, 10), (10, 10), (3, 7)):
        lo, hi = wilson(k, n)
        assert 0.0 <= lo <= hi <= 1.0


def test_thieu_mau_thi_KHONG_KET_LUAN_du_chenh_lech_lon():
    """30 cặp với 70/30 nhìn rất 'rõ ràng' — nhưng luật nói chưa đủ."""
    caps = _caps(30)
    kq = tinh(caps, _phieu(caps, a_thang=21, b_thang=9))
    assert kq.ket_luan == "chua phan biet duoc"
    assert any("cap that" in l for l in kq.ly_do)


def test_du_mau_va_chenh_lech_ro_thi_ket_luan_duoc():
    caps = _caps(60, n_bay=6)
    kq = tinh(caps, _phieu(caps, a_thang=42, b_thang=18, bay_quyet=2))
    assert kq.ket_luan == "A thang"
    assert kq.khoang_tin_thap > 0.5


def test_du_mau_nhung_sat_nhau_thi_chua_phan_biet_duoc():
    caps = _caps(60, n_bay=6)
    kq = tinh(caps, _phieu(caps, a_thang=32, b_thang=28, bay_quyet=2))
    assert kq.ket_luan == "chua phan biet duoc"
    assert any("khoang tin cay" in l for l in kq.ly_do)


def test_san_nhieu_cao_hon_quyet_doan_that_thi_ket_qua_vo_nghia():
    """⭐ Luật quan trọng nhất của tệp này.

    Người chấm quyết đoán trên 100 % cặp bẫy (hai ảnh cùng model, khác seed) nhưng
    trên cặp thật lại hoà quá nửa ⇒ khác biệt giữa hai model NHỎ HƠN khác biệt giữa
    hai lần chạy cùng một model. Mọi con số thắng-thua khi đó là vô nghĩa.
    """
    caps = _caps(60, n_bay=10)
    kq = tinh(caps, _phieu(caps, a_thang=20, b_thang=5, hoa=35, bay_quyet=10))
    assert kq.san_nhieu == 1.0 and kq.quyet_doan_that < 1.0
    assert kq.ket_luan == "chua phan biet duoc"
    assert any("san nhieu" in l for l in kq.ly_do)


def test_bat_lech_vi_tri_khi_nguoi_cham_luon_chon_mot_ben():
    caps = _caps(60, n_bay=10)
    kq = tinh(caps, _phieu(caps, a_thang=40, b_thang=20,
                           bay_quyet=10, bay_trai=10))
    assert kq.lech_vi_tri == 1.0
    assert any("LECH VI TRI" in l for l in kq.ly_do)


def test_hoa_tinh_nua_diem_cho_moi_ben():
    caps = _caps(60)
    kq = tinh(caps, _phieu(caps, a_thang=20, b_thang=20, hoa=20))
    assert kq.diem_a == pytest.approx(0.5)
    assert kq.ket_luan == "chua phan biet duoc"


def test_cap_chua_cham_bi_bo_qua_khong_tinh_la_hoa():
    """Bỏ trống ≠ hoà. Tính nhầm là làm loãng kết quả một cách im lặng."""
    caps = _caps(60)
    p = _phieu(caps, a_thang=55, b_thang=5)
    for c in caps[:10]:
        p.pop(c.ma, None)
    kq = tinh(caps, p)
    assert kq.n_that == 50


def test_lua_chon_la_bi_bo_qua():
    caps = _caps(60)
    p = _phieu(caps, a_thang=55, b_thang=5)
    p[caps[0].ma] = "khong-biet"
    assert tinh(caps, p).n_that == 59


def test_nguon_duoc_doc_theo_PHIA_da_xao_khong_theo_gia_dinh():
    """Sau khi xáo trái/phải, "chọn trái" có thể là chọn B. Đọc sai chỗ này là đảo
    ngược toàn bộ kết luận mà không ai nhận ra."""
    caps = [Cap("c1", "l.png", "r.png", "B", "A", False)]
    kq = tinh(caps, {"c1": "trai"})
    assert kq.thang_b == 1 and kq.thang_a == 0


def test_khong_co_cap_bay_thi_van_tinh_duoc_nhung_khong_co_san_nhieu():
    caps = _caps(60)
    kq = tinh(caps, _phieu(caps, a_thang=45, b_thang=15))
    assert kq.n_bay == 0 and kq.san_nhieu == 0.0 and kq.ket_luan == "A thang"


def test_so_cap_toi_thieu_dung_bang_50():
    """Con số này là hợp đồng với §1.5 — đổi nó phải đổi cả tài liệu."""
    assert SO_CAP_TOI_THIEU == 50


# ─────────────── màn chấm: nó không được làm hỏng tính mù ───────────────────
def _lo_that(tmp_path, n=3):
    """Lô thật có ảnh trên đĩa, để `ghi_lo` chép được."""
    a, b = tmp_path / "A", tmp_path / "B"
    for d in (a, b):
        d.mkdir()
        for i in range(n):
            (d / f"p{i}.png").write_bytes(b"\x89PNG" + bytes([i]))
    caps = tao_lo(_ds(a), _ds(b), ty_le_bay=0.5, rng=random.Random(7))
    lo = tmp_path / "lo"
    ghi_lo(caps, lo, nhan_a="s30", nhan_b="s90")
    ghi_man(caps, lo)
    return lo, caps


def _ds(d):
    return [str(p) for p in sorted(d.iterdir())]


def test_man_cham_KHONG_lo_nguon_trong_ma_nguon_trang(tmp_path):
    """Cạm bẫy chí mạng: nhúng cả `Cap` vào HTML thì "Xem mã nguồn trang" hiện
    thẳng `nguon_trai: "A"`. Người chấm không cần cố ý gian lận — chỉ cần bấm
    nhầm Ctrl+U một lần là cả lô mất giá trị."""
    lo, caps = _lo_that(tmp_path)
    html = (lo / TEN_MAN).read_text(encoding="utf-8")
    assert "nguon_trai" not in html and "nguon_phai" not in html
    assert "la_bay" not in html
    # Nhãn nguồn cũng không được có mặt.
    assert "s30" not in html and "s90" not in html
    # Nhưng mã cặp và tên tệp đã mã hoá thì phải có, không thì màn trống trơn.
    for c in caps:
        assert c.ma in html and c.trai in html and c.phai in html


def test_man_cham_nhung_du_lieu_chu_khong_fetch(tmp_path):
    """Màn chạy bằng `file://`. `fetch()` một tệp cạnh nó sẽ bị CORS chặn và màn
    sẽ trắng — lỗi chỉ lộ ra trên máy người chấm, không lộ ra ở test nào khác."""
    lo, _ = _lo_that(tmp_path)
    html = (lo / TEN_MAN).read_text(encoding="utf-8")
    assert "fetch(" not in html
    assert "const CAP = [" in html


def test_man_cham_khong_con_the_thay_the_nao_sot_lai(tmp_path):
    lo, _ = _lo_that(tmp_path)
    html = (lo / TEN_MAN).read_text(encoding="utf-8")
    assert "__CAP__" not in html and "__LO__" not in html


def test_lenh_tao_sinh_luon_man_cham(tmp_path):
    """`tao` phải sinh màn. Nếu phải nhớ chạy thêm một lệnh nữa thì sẽ có lần quên,
    và lần đó người chấm quay về mở File Explorer — tức là hết mù."""
    a, b = tmp_path / "A", tmp_path / "B"
    for d in (a, b):
        d.mkdir()
        for i in range(3):
            (d / f"p{i}.png").write_bytes(b"\x89PNG" + bytes([i]))
    lo = tmp_path / "lo"
    assert main(["tao", "--a", str(a), "--b", str(b), "--ra", str(lo)]) == 0
    assert (lo / TEN_MAN).exists()


# ═══════════ D-052: máy chấm thì mỗi phiếu quyết đoán phải nói ra vì sao ═════
#
# Luật cũ (§1.5.3) cấm tôi bỏ phiếu thẩm mỹ. Chủ sản phẩm đảo luật đó ngày
# 24/08 — nay máy chấm. Rủi ro "mô hình chấm sản phẩm của chính mình" **không
# biến mất** vì luật đổi, nên đổi cách chặn: buộc mỗi lá phiếu phải viết lý do.
#
# Một câu lý do buộc phải NHÌN. Không có nó thì không gì phân biệt "đã mở ảnh"
# với "đoán theo thứ tự tệp" — và D-027 cho thấy quy trình này từng chạy tám
# lượt đo mà không ai nhìn một tấm ảnh nào.

import pytest

from tools import cham_mu as CM


def _phieu_may(**kw):
    goc = {"may_cham": True, "nguoi_cham": "opus-5",
           "phieu": [{"ma": "c001", "chon": "trai", "ghi_chu": "toc net hon"}]}
    goc.update(kw)
    return goc


def test_nguoi_cham_thi_KHONG_bat_ghi_chu():
    """Luật này chỉ áp cho máy. Người chấm đã có mặt và có trách nhiệm."""
    CM.kiem_phieu_may({"may_cham": False,
                       "phieu": [{"ma": "c001", "chon": "trai", "ghi_chu": ""}]})


def test_lo_cu_khong_khai_gi_van_tinh_duoc():
    """Các lô đã chấm trước D-052 không có trường này. Đừng làm hỏng chúng."""
    CM.kiem_phieu_may({"phieu": [{"ma": "c001", "chon": "trai"}]})


def test_may_cham_ma_thieu_ghi_chu_thi_TU_CHOI_TINH():
    """🔴 Chốt chính. Từ chối tính còn hơn tính ra một con số không ai kiểm được."""
    with pytest.raises(CM.PhieuKhongHopLe) as e:
        CM.kiem_phieu_may(_phieu_may(phieu=[{"ma": "c001", "chon": "trai", "ghi_chu": ""},
                                        {"ma": "c002", "chon": "phai", "ghi_chu": " "}]))
    assert "c001" in str(e.value) and "c002" in str(e.value)


def test_hoa_KHONG_bat_buoc_ghi_chu():
    """⛔ Bắt viết lý do cho hoà là dạy người chấm né hoà.

    Mà né hoà chính là thứ làm hỏng sàn nhiễu: cặp bẫy đo *mức quyết đoán khi
    không có gì để quyết*. Ép quyết đoán thì phép đo đó mất nghĩa.
    """
    CM.kiem_phieu_may(_phieu_may(phieu=[{"ma": "c001", "chon": "hoa", "ghi_chu": ""}]))


def test_may_cham_ma_khong_ghi_TEN_thi_tu_choi():
    """Không biết model nào chấm thì không đối chiếu được hai lô chấm khác nhau."""
    with pytest.raises(CM.PhieuKhongHopLe):
        CM.kiem_phieu_may(_phieu_may(nguoi_cham="  "))


def test_lo_moi_dung_ra_co_san_cho_khai_nguoi_cham(tmp_path):
    """Trường phải có sẵn trong phiếu trống, nếu không sẽ không ai điền."""
    import json

    a = tmp_path / "a"; b = tmp_path / "b"
    for d in (a, b):
        d.mkdir()
        for i in range(3):
            (d / f"{i}.png").write_bytes(b"x")
    caps = CM.tao_lo(sorted(str(x) for x in a.glob("*.png")),
                     sorted(str(x) for x in b.glob("*.png")),
                     ty_le_bay=0.0)
    CM.ghi_lo(caps, tmp_path / "lo", nhan_a="A", nhan_b="B")
    p = json.loads((tmp_path / "lo" / CM.TEN_PHIEU).read_text(encoding="utf-8"))
    assert "nguoi_cham" in p and "may_cham" in p
    assert all("ghi_chu" in x for x in p["phieu"])


# ═══════════ Bẫy CÙNG ĐỀ BÀI, KHÁC SEED ══════════════════════════════════════
#
# 🔴 Bẫy cũ ghép hai ảnh **khác đề bài** của cùng một nguồn. Với phép so
#    *cùng-đề-bài* (36 vs 50 bước) nó vô dụng: hai ảnh khác đề bài thì khác nhau
#    hiển nhiên, nên người chấm gần như luôn chọn được một bên ⇒ sàn nhiễu ~100 %
#    ⇒ `d <= f` luôn đúng ⇒ công cụ luôn trả "chưa phân biệt được", bất kể dữ liệu.
#
#    Đã xảy ra thật: B2b đo sàn nhiễu **100 %** và D-049 phải ghi rõ là không dựa
#    vào lý do đó. Tăng số cặp bẫy kiểu cũ không cứu được — chỉ làm một tín hiệu
#    vô dụng trở nên chính xác hơn.

def test_bay_cung_de_bai_thi_HAI_BEN_deu_la_A():
    """Bẫy đúng nghĩa: cùng đề bài, cùng cấu hình, khác seed. Không bên nào thắng."""
    a = [f"s50/p{i:02d}.png" for i in range(1, 11)]
    b = [f"s36/p{i:02d}.png" for i in range(1, 11)]
    bay = [f"seed2/p{i:02d}.png" for i in range(1, 11)]
    caps = CM.tao_lo(a, b, ty_le_bay=0.3, anh_bay=bay,
                     rng=__import__("random").Random(7))
    cb = [c for c in caps if c.la_bay]
    assert cb, "phai co cap bay"
    for c in cb:
        assert c.nguon_trai == c.nguon_phai == "A"


def test_bay_cung_de_bai_ghep_DUNG_CHI_SO():
    """Lệch chỉ số là quay về bẫy cũ mà không ai biết — nên phải chốt."""
    a = [f"s50/p{i:02d}.png" for i in range(1, 11)]
    b = [f"s36/p{i:02d}.png" for i in range(1, 11)]
    bay = [f"seed2/p{i:02d}.png" for i in range(1, 11)]
    caps = CM.tao_lo(a, b, ty_le_bay=0.3, anh_bay=bay,
                     rng=__import__("random").Random(11))
    for c in (x for x in caps if x.la_bay):
        # sau khi xao trai/phai, mot ben la s50 va ben kia la seed2, CUNG so hieu
        so = {t.split("/")[-1] for t in (c.trai, c.phai)}
        assert len(so) == 1, f"bay ghep hai de bai khac nhau: {c.trai} vs {c.phai}"


def test_khong_truyen_anh_bay_thi_giu_hanh_vi_cu():
    """Các lô cũ và các phép so khác-đề-bài vẫn dùng được kiểu bẫy cũ."""
    a = [f"s50/p{i:02d}.png" for i in range(1, 11)]
    b = [f"s36/p{i:02d}.png" for i in range(1, 11)]
    caps = CM.tao_lo(a, b, ty_le_bay=0.2, rng=__import__("random").Random(3))
    cb = [c for c in caps if c.la_bay]
    assert cb and all(c.nguon_trai == c.nguon_phai for c in cb)
