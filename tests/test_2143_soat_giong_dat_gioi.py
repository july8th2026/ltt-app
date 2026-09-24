"""`soat_giong.py dat-gioi` — ba điều kiện của một lần ghi cột `gioi`.

🔴 Phép kiểm này chốt phần **quyết định**, và nó cố ý không mở một CSDL nào:
   câu hỏi *"có được ghi không"* phải trả lời được mà không cần một CSDL sống,
   nếu không thì nó chỉ được kiểm khi ai đó nhớ chạy phép kiểm tích hợp.

Cột `gioi` mặc định `""` = KHÔNG RÕ, và `apps/ltt_voice/tables.py` ghi thẳng:
*"một cột 'giới' sai còn tệ hơn một cột trống, vì nó ĐƯỢC TIN"*. Nên mặc định
của lệnh phải là **để trống**, không phải *"lấy cái nào chắc hơn"*.
"""
from __future__ import annotations

from tools.soat_giong import _ke_hoach_gioi

NGUONG = 0.95


def _kh(**d):
    goc = {"ten": "X", "do_sinh": "nam", "do_tin_sinh": 0.99,
           "do_goc": "nam", "do_tin_goc": 0.99}
    goc.update(d)
    return _ke_hoach_gioi({"vc_x": goc}, NGUONG)[0]


def test_hai_mat_khop_va_chac_thi_ghi():
    pid, ten, gioi, vi_sao = _kh()
    assert (pid, gioi, vi_sao) == ("vc_x", "nam", "")


def test_hai_mat_lech_thi_de_trong():
    """Clip gốc nói một đằng, tiếng engine sinh nói một nẻo ⇒ không ai đúng."""
    _pid, _ten, gioi, vi_sao = _kh(do_goc="nu")
    assert gioi == ""
    assert "khong khop" in vi_sao


def test_do_tin_thap_thi_de_trong_du_hai_mat_khop():
    """Đây là ca 'giọng ở giữa' — hai mặt cùng đoán sai theo cùng một hướng."""
    _pid, _ten, gioi, vi_sao = _kh(do_tin_sinh=0.60)
    assert gioi == ""
    assert "do_tin" in vi_sao


def test_thieu_phep_do_thi_de_trong_chu_khong_lay_mat_con_lai():
    """⛔ Một mặt đo được KHÔNG phải một nửa bằng chứng. Nó là 'chưa đo'."""
    _pid, _ten, gioi, vi_sao = _kh(do_goc=None, do_tin_goc=None)
    assert gioi == ""
    assert "thieu phep do" in vi_sao


def test_gia_tri_la():
    """Nhãn lạ (`""`, `unknown`, `male`) KHÔNG được ghi — cột chỉ nhận nam/nu."""
    for la in ("", "unknown", "male", None):
        _pid, _ten, gioi, _ = _kh(do_sinh=la, do_goc=la)
        assert gioi == "", la


def test_ke_hoach_tat_dinh_va_sap_theo_ten():
    de_xuat = {
        "vc_b": {"ten": "Zulu", "do_sinh": "nu", "do_tin_sinh": 0.99,
                 "do_goc": "nu", "do_tin_goc": 0.99},
        "vc_a": {"ten": "Alpha", "do_sinh": "nam", "do_tin_sinh": 0.99,
                 "do_goc": "nam", "do_tin_goc": 0.99},
    }
    kh = _ke_hoach_gioi(de_xuat, NGUONG)
    assert [x[1] for x in kh] == ["Alpha", "Zulu"]
    assert kh == _ke_hoach_gioi(de_xuat, NGUONG)
