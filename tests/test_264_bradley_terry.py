"""
test_264 — xếp hạng nhiều model bằng Bradley-Terry. (H37/G6b)

Không mạng, không GPU.

⭐ VÌ SAO TỆP NÀY TỒN TẠI

   `cham_mu.tinh()` dùng khoảng Wilson trên tỉ lệ thắng — **đúng cho hai model**.
   G6b có **ba đối thủ**, và ở đó tỉ lệ thắng theo cặp **không cộng lại thành một
   bảng xếp hạng nhất quán**: A thắng B, B thắng C, C thắng A là chuyện bình
   thường trong dữ liệu thật.

   Chạy G6b bằng bộ chấm cũ sẽ ra một bảng **trông có vẻ đúng** và không ai phát
   hiện được là nó vô nghĩa. Đó là lý do phải làm việc này **trước** phiên GPU.
"""
from __future__ import annotations

import random

import pytest

from tools import bradley_terry as BT


def _tran(cap, lan):
    """`cap` = (a, b, ai_thang); lặp `lan` lần."""
    return [cap] * lan


# ═══════════ đúng thứ tự khi dữ liệu rõ ràng ════════════════════════════════
def test_xep_dung_thu_tu_khi_A_hon_B_hon_C():
    phieu = (_tran(("A", "B", "A"), 30) + _tran(("B", "C", "B"), 30)
             + _tran(("A", "C", "A"), 30))
    kq = BT.xep_hang(phieu, so_vong=40)
    assert [h.ten for h in kq.hang] == ["A", "B", "C"]


def test_thang_sach_thi_xac_suat_thang_cao():
    phieu = _tran(("A", "B", "A"), 40) + _tran(("B", "C", "B"), 40) + \
            _tran(("A", "C", "A"), 40)
    kq = BT.xep_hang(phieu, so_vong=40)
    assert kq.hang[0].xac_suat_thang > kq.hang[-1].xac_suat_thang


def test_hai_model_ngang_nhau_thi_khong_phan_biet_duoc():
    """⛔ Hai khoảng tin chồng nhau nghĩa là **chưa đủ dữ liệu để phân biệt** —
    không phải "hoà", và càng không phải "gần bằng nhau"."""
    r = random.Random(7)
    phieu = [("A", "B", "A" if r.random() < 0.5 else "B") for _ in range(60)]
    kq = BT.xep_hang(phieu, so_vong=60)
    assert not kq.phan_biet_duoc("A", "B")


def test_chenh_lech_LON_thi_phan_biet_duoc():
    phieu = _tran(("A", "B", "A"), 55) + _tran(("A", "B", "B"), 5)
    kq = BT.xep_hang(phieu, so_vong=80)
    assert kq.phan_biet_duoc("A", "B")


# ═══════════ ⛔ vòng tròn: đúng thứ Wilson KHÔNG xử lý được ═════════════════
def test_VONG_TRON_van_ra_mot_bang_nhat_quan():
    """A thắng B, B thắng C, C thắng A — cân bằng hoàn hảo.

    Tỉ lệ thắng theo cặp ở đây nói *"mỗi model thắng 100 % một đối thủ"*, và cộng
    lại thì **không có thứ tự nào**. Bradley-Terry khớp toàn bộ cùng lúc nên nó ra
    ba sức mạnh **bằng nhau** — câu trả lời đúng, và là câu trả lời có ích."""
    phieu = (_tran(("A", "B", "A"), 20) + _tran(("B", "C", "B"), 20)
             + _tran(("C", "A", "C"), 20))
    kq = BT.xep_hang(phieu, so_vong=40)
    suc = [h.suc_manh for h in kq.hang]
    assert max(suc) - min(suc) < 0.05, f"vong tron ma suc manh lech: {suc}"


def test_khong_phan_biet_duoc_ai_trong_vong_tron():
    phieu = (_tran(("A", "B", "A"), 20) + _tran(("B", "C", "B"), 20)
             + _tran(("C", "A", "C"), 20))
    kq = BT.xep_hang(phieu, so_vong=60)
    for x, y in (("A", "B"), ("B", "C"), ("A", "C")):
        assert not kq.phan_biet_duoc(x, y)


# ═══════════ ⛔ không phụ thuộc THỨ TỰ phiếu ═══════════════════════════════
def test_XAO_LAI_PHIEU_van_ra_dung_ket_qua():
    """⛔ Đây là lý do LMArena bỏ Elo tuần tự: Elo cập nhật sau từng trận nên xáo
    lại cùng một bộ phiếu ra một bảng khác. Một phép đo phụ thuộc thứ tự thì hai
    người cùng dữ liệu sẽ cãi nhau mà không ai sai."""
    phieu = (_tran(("A", "B", "A"), 25) + _tran(("B", "C", "hoa"), 25)
             + _tran(("A", "C", "A"), 25))
    mot = BT.xep_hang(phieu, so_vong=30)
    r = random.Random(99)
    xao = list(phieu)
    r.shuffle(xao)
    hai = BT.xep_hang(xao, so_vong=30)
    for a, b in zip(mot.hang, hai.hang):
        assert a.ten == b.ten
        assert abs(a.suc_manh - b.suc_manh) < 1e-6


def test_cung_du_lieu_thi_cung_khoang_tin():
    """Bootstrap phải tái lập được, không thì hai lần chạy ra hai kết luận."""
    phieu = _tran(("A", "B", "A"), 30) + _tran(("B", "C", "B"), 30) + \
            _tran(("A", "C", "A"), 30)
    a = BT.xep_hang(phieu, so_vong=40)
    b = BT.xep_hang(phieu, so_vong=40)
    assert [h.ci_thap for h in a.hang] == [h.ci_thap for h in b.hang]


# ═══════════ hoà ═══════════════════════════════════════════════════════════
def test_hoa_tinh_nua_thang_cho_moi_ben():
    phieu = _tran(("A", "B", "hoa"), 40)
    kq = BT.xep_hang(phieu, so_vong=30)
    assert kq.so_hoa == 40
    assert all(abs(h.so_thang - 20.0) < 1e-9 for h in kq.hang)


def test_toan_hoa_thi_CANH_BAO():
    """Người chấm không phân biệt được thì bảng xếp hạng nói rất ít — phải nói ra
    điều đó, không để một bảng trông bình thường che mất."""
    kq = BT.xep_hang(_tran(("A", "B", "hoa"), 60), so_vong=20)
    assert any("HOA" in c for c in kq.canh_bao)


# ═══════════ ⛔ từ chối khi dữ liệu không đủ để kết luận ════════════════════
def test_DO_THI_KHONG_LIEN_THONG_thi_TU_CHOI():
    """⛔ Kiểu hỏng im lặng đắt nhất của phép so cặp. A-B chưa từng gặp C-D; thuật
    vẫn chạy và vẫn ra bốn con số, nhưng so sánh giữa hai cụm là **vô nghĩa** — và
    không có gì trong bảng cho biết điều đó."""
    phieu = _tran(("A", "B", "A"), 20) + _tran(("C", "D", "C"), 20)
    with pytest.raises(BT.KhongDuDuLieu) as e:
        BT.xep_hang(phieu, so_vong=10)
    assert "lien thong" in str(e.value)


def test_mot_model_thi_TU_CHOI():
    with pytest.raises(BT.KhongDuDuLieu):
        BT.xep_hang([], so_vong=10)


def test_ket_qua_khong_hop_le_thi_TU_CHOI():
    with pytest.raises(BT.KhongDuDuLieu):
        BT.xep_hang([("A", "B", "C")], so_vong=10)


def test_duoi_50_cap_thi_CANH_BAO_chu_khong_im():
    """§1.5 của kế hoạch: dưới 50 cặp thì không kết luận. Vẫn tính, nhưng phải nói."""
    kq = BT.xep_hang(_tran(("A", "B", "A"), 10), so_vong=20)
    assert any("50" in c for c in kq.canh_bao)


def test_model_qua_it_tran_thi_CANH_BAO():
    phieu = _tran(("A", "B", "A"), 60) + [("A", "C", "A"), ("B", "C", "B")]
    kq = BT.xep_hang(phieu, so_vong=20)
    assert any("it tran" in c for c in kq.canh_bao)


# ═══════════ không thay bộ chấm cũ ═════════════════════════════════════════
def test_KHONG_dung_den_cham_mu_va_cham_mu_khong_dung_den_no():
    """Hai công cụ, hai câu hỏi. Với đúng hai model, Wilson chặt hơn và đã có 21
    test — gộp lại là đánh đổi một thứ đã chứng minh lấy một thứ tổng quát hơn."""
    import ast
    import inspect

    from tools import cham_mu

    def _nhap(mo_dun):
        """Đọc bằng AST, không so chuỗi. So chuỗi bắt nhầm cả chú thích — và tôi
        đã mắc đúng lỗi này một lần với `ctx.db` ở test_253."""
        ten = set()
        for n in ast.walk(ast.parse(inspect.getsource(mo_dun))):
            if isinstance(n, ast.Import):
                ten |= {a.name.split(".")[-1] for a in n.names}
            elif isinstance(n, ast.ImportFrom):
                if n.module:
                    ten.add(n.module.split(".")[-1])
                ten |= {a.name for a in n.names}
        return ten

    assert "bradley_terry" not in _nhap(cham_mu)
    assert "cham_mu" not in _nhap(BT)


def test_bang_van_ban_doc_duoc_ma_khong_can_giai_thich():
    kq = BT.xep_hang(_tran(("A", "B", "A"), 30) + _tran(("B", "C", "B"), 30)
                     + _tran(("A", "C", "A"), 30), so_vong=20)
    t = BT.bang_van_ban(kq)
    for phai_co in ("model", "p(thang)", "khoang tin", "A", "B", "C"):
        assert phai_co in t
