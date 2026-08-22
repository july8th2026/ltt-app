"""
test_248 — thước đo giữ bố cục (`tools/do_bo_cuc.py`).

Thước này sẽ được dùng để trả lời **một câu hỏi có hậu quả**: chế độ `structure`
có bán được không (D-017). Nên bản thân nó phải đúng trước, và "đúng" ở đây nghĩa
là: nó phải **phân biệt được** hai ảnh cùng bố cục với hai ảnh khác bố cục — và
phải **im lặng** khi không đủ căn cứ.
"""
from __future__ import annotations

import numpy as np
import pytest
from PIL import Image, ImageDraw

from tools.do_bo_cuc import do_mot, do_san, phan_dinh, tuong_quan


def _ve(duong, hinh, *, mau_nen=(30, 30, 30), mau_hinh=(230, 230, 230)):
    im = Image.new("RGB", (640, 360), mau_nen)
    g = ImageDraw.Draw(im)
    for h in hinh:
        g.rectangle(h, fill=mau_hinh)
    im.save(duong)
    return duong


# Bố cục A: một khối trái, một khối phải trên.  Bố cục B: đảo hẳn vị trí.
BO_CUC_A = [(40, 40, 240, 300), (380, 30, 600, 150)]
BO_CUC_B = [(400, 60, 600, 320), (40, 200, 260, 330)]


def test_cung_bo_cuc_khac_mau_van_tuong_quan_cao(tmp_path):
    """Đây chính là ca của chế độ `structure`: lệnh sửa ĐƯỢC PHÉP đổi màu, chất
    liệu, phong cách. Thước phải bỏ qua những thứ đó và chỉ nhìn bố cục."""
    a = _ve(tmp_path / "a.png", BO_CUC_A)
    b = _ve(tmp_path / "b.png", BO_CUC_A, mau_nen=(200, 40, 40), mau_hinh=(10, 60, 120))
    assert do_mot(a, b) > 0.9


def test_khac_bo_cuc_thi_tuong_quan_thap(tmp_path):
    a = _ve(tmp_path / "a.png", BO_CUC_A)
    b = _ve(tmp_path / "b.png", BO_CUC_B)
    assert do_mot(a, b) < 0.3


def test_anh_phang_li_khong_lam_no_chia_cho_khong(tmp_path):
    """Ảnh một màu không có cạnh nào. Không được ném ZeroDivisionError hay trả NaN
    — một NaN lọt vào bảng kết quả sẽ âm thầm phá mọi phép so sau đó."""
    a = _ve(tmp_path / "a.png", [])
    b = _ve(tmp_path / "b.png", BO_CUC_A)
    d = do_mot(a, b)
    assert d == 0.0 and not np.isnan(d)


def test_tuong_quan_voi_chinh_no_la_mot(tmp_path):
    a = _ve(tmp_path / "a.png", BO_CUC_A)
    assert do_mot(a, a) == pytest.approx(1.0, abs=1e-9)


# ───────────────── sàn nhiễu: phần quan trọng hơn con số ────────────────────
def test_khong_co_san_thi_KHONG_duoc_ket_luan():
    """Luật cốt lõi: một con số tương quan đứng một mình không nói lên gì. Thước
    phải từ chối phán, chứ không phán bừa rồi để người đọc tự đoán."""
    ket, chi_tiet = phan_dinh(0.95, [])
    assert ket == "khong co san de so"
    assert "vo nghia" in chi_tiet["canh_bao"]


def test_vuot_ca_san_cao_nhat_moi_goi_la_giu_bo_cuc():
    assert phan_dinh(0.80, [0.1, 0.3, 0.5])[0] == "co giu bo cuc"


def test_tren_trung_binh_nhung_duoi_dinh_san_thi_KHONG_ket_luan(tmp_path):
    """Vượt trung bình của sàn mà chưa vượt cái cao nhất thì vẫn có thể chỉ là một
    ảnh lạ tình cờ giống bố cục. Ở khoảng đó, câu trả lời đúng là 'chưa biết'."""
    assert phan_dinh(0.40, [0.1, 0.3, 0.55])[0] == "khong ket luan duoc"


def test_duoi_trung_binh_san_la_KHONG_giu():
    assert phan_dinh(0.15, [0.1, 0.3, 0.5])[0] == "KHONG giu bo cuc"


def test_san_do_dung_so_anh_da_cho(tmp_path):
    a = _ve(tmp_path / "a.png", BO_CUC_A)
    la = [_ve(tmp_path / f"l{i}.png", BO_CUC_B) for i in range(3)]
    san = do_san(a, la)
    assert len(san) == 3


def test_ca_that_cua_G5_san_phai_thap_hon_ca_cung_bo_cuc(tmp_path):
    """Dựng đúng tình huống G5 sẽ gặp và kiểm cả chuỗi: một ảnh gốc, một ảnh 'đã
    sửa nhưng giữ bố cục', và ba ảnh lạ làm sàn."""
    goc = _ve(tmp_path / "goc.png", BO_CUC_A)
    sua = _ve(tmp_path / "sua.png", BO_CUC_A, mau_nen=(90, 20, 20))
    la = [_ve(tmp_path / f"l{i}.png", BO_CUC_B, mau_nen=(10 * i, 40, 60))
          for i in range(3)]
    ket, _ = phan_dinh(do_mot(goc, sua), do_san(goc, la))
    assert ket == "co giu bo cuc"


def test_tuong_quan_khong_bao_gio_vuot_khoang(tmp_path):
    x = np.random.default_rng(0).random((64, 64))
    y = -x
    assert -1.0 <= tuong_quan(x, y) <= 1.0
