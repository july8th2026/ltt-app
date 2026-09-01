r"""
K2 · kho tham chiếu nhiều cửa sổ.

## Vì sao gộp được `speaker_emb` mà không gộp được `ref_codes`

`prepare_reference` của VieNeu trả **hai** thứ khác hẳn bản chất:

  · `speaker_emb` — vector 192 chiều từ bộ mã hoá người nói. Trung bình nhiều
    lượt phát chính là cách mọi hệ nhận dạng người nói ghi danh; nó kéo điểm về
    **trọng tâm giọng** thay vì một lát cắt.
  · `ref_codes`   — chuỗi token codec của một clip. Trung bình hai chuỗi token
    là tạo ra một chuỗi **không tương ứng với âm thanh nào cả**.

⇒ Gộp embedding qua cả kho, giữ codes của cửa sổ tốt nhất. Cùng nước đi XTTS làm
  khi nhận một danh sách `speaker_wav`.

## ⛔ CHỒNG LẤN LÀ ĐIỀU KIỆN KHIẾN PHÉP GỘP CÓ NGHĨA

`ung_vien()` sinh **mọi cụm đoạn liên tiếp**, nên hai ứng viên điểm cao nhất gần
như luôn chồng lấn — chúng là cùng một chỗ tốt, cắt lệch nhau một câu. Trung bình
hai embedding của cùng một đoạn không thêm thông tin nào; nó chỉ làm ta **tưởng**
đã gộp.

Đây là phép kiểm quan trọng nhất tệp này: không có nó, `chon_kho` vẫn trả về đủ
số cửa sổ, engine vẫn gộp, mọi thứ vẫn chạy — và cả pha K2 thành một phép trung
bình của một thứ với chính nó.
"""
from __future__ import annotations

import numpy as np

from voice_sidecar import chon_doan as cd

SR = 24_000


def _tieng(giay: float, f0: float = 130.0, seed: int = 5) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(SR * giay)
    t = np.arange(n) / SR
    f = f0 + 20 * np.sin(2 * np.pi * 0.9 * t)
    pha = 2 * np.pi * np.cumsum(f) / SR
    x = sum(np.sin(k * pha) / k for k in (1, 2, 3, 5))
    bao = 0.4 + 0.6 * np.abs(np.sin(2 * np.pi * 2.1 * t + rng.random()))
    return (x * bao * 0.25).astype(np.float32)


def _im(giay: float) -> np.ndarray:
    return np.zeros(int(SR * giay), dtype=np.float32)


def _clip_nhieu_cho_tot() -> np.ndarray:
    """Clip dài, nhiều đoạn nói cách nhau bởi khoảng lặng — như một bản thu thật."""
    manh = []
    for i in range(7):
        manh.append(_tieng(3.0, f0=120 + 6 * i, seed=i))
        manh.append(_im(0.6))
    return np.concatenate(manh)


def _ma_hoa_gia(w, sr):
    """Embedding giả, phụ thuộc nội dung — hai đoạn khác nhau cho hai vector khác."""
    x = np.asarray(w, dtype=np.float64)
    if not x.size:
        return None
    ph = np.abs(np.fft.rfft(x[: 1 << 15], n=1 << 15))
    v = ph[:192]
    n = np.linalg.norm(v)
    return (v / n) if n else v


# ── phép kiểm cốt lõi ───────────────────────────────────────────────────────
def test_cac_cua_so_trong_kho_KHONG_chong_lan_nhau():
    """⛔ Nếu chúng chồng lấn, phép gộp là trung bình một thứ với chính nó."""
    kho = cd.chon_kho(_clip_nhieu_cho_tot(), SR, so_luong=5,
                      bo_ma_hoa=_ma_hoa_gia)
    assert len(kho) >= 2, f"chi chon duoc {len(kho)} cua so — khong du de gop"
    for i, a in enumerate(kho):
        for b in kho[i + 1:]:
            cl = cd._chong_lan(a.bat_dau_s, a.ket_thuc_s,
                               b.bat_dau_s, b.ket_thuc_s)
            assert cl <= cd.CHONG_LAN_TOI_DA, (
                f"[{a.bat_dau_s},{a.ket_thuc_s}] va [{b.bat_dau_s},"
                f"{b.ket_thuc_s}] chong lan {cl:.2f}")


def test_chong_lan_tinh_tren_khoang_NGAN_hon():
    """🔴 Chia cho khoảng ngắn hơn, KHÔNG cho hợp.

    Một cửa sổ 3 giây nằm **trọn** trong một cửa sổ 8 giây là chồng hoàn toàn —
    nó không thêm gì cả. Tính theo hợp thì ra 0,375 và lọt qua ngưỡng 0,25.
    """
    assert cd._chong_lan(0.0, 8.0, 2.0, 5.0) == 1.0
    assert cd._chong_lan(0.0, 4.0, 4.0, 8.0) == 0.0
    assert 0.24 < cd._chong_lan(0.0, 4.0, 3.0, 7.0) < 0.26


def test_cua_so_dau_tien_cua_kho_DUNG_bang_duong_mot_cua_so():
    """Kho phải là **mở rộng** của đường cũ, không phải một đường khác.

    Nếu phần tử đầu khác `chon()`, thì bật kho lên là đổi luôn cửa sổ tốt nhất —
    và phép đo A/B sẽ đo hai thay đổi cùng lúc, không tách được cái nào gây ra
    khác biệt.
    """
    w = _clip_nhieu_cho_tot()
    mot = cd.chon(w, SR, bo_ma_hoa=_ma_hoa_gia)
    kho = cd.chon_kho(w, SR, so_luong=5, bo_ma_hoa=_ma_hoa_gia)
    assert (kho[0].bat_dau_s, kho[0].ket_thuc_s) == (mot.bat_dau_s,
                                                     mot.ket_thuc_s)


def test_so_luong_1_tra_ve_dung_mot_cua_so():
    kho = cd.chon_kho(_clip_nhieu_cho_tot(), SR, so_luong=1,
                      bo_ma_hoa=_ma_hoa_gia)
    assert len(kho) == 1


def test_clip_ngheo_cho_tot_thi_kho_NGAN_LAI_chu_khong_bia_them():
    """Một clip chỉ có một chỗ dùng được thì kho phải ngắn, không được nhồi cho
    đủ số bằng những cửa sổ chồng lấn."""
    w = np.concatenate([_tieng(6.0), _im(0.5)])
    kho = cd.chon_kho(w, SR, so_luong=5, bo_ma_hoa=_ma_hoa_gia)
    assert 1 <= len(kho) <= 5
    for i, a in enumerate(kho):
        for b in kho[i + 1:]:
            assert cd._chong_lan(a.bat_dau_s, a.ket_thuc_s,
                                 b.bat_dau_s, b.ket_thuc_s) <= cd.CHONG_LAN_TOI_DA


# ── phần engine: gộp đúng cách ──────────────────────────────────────────────
def test_engine_GOP_embedding_va_CHUAN_HOA_sau_khi_cong():
    """⛔ Trung bình các vector đơn vị cho một vector **ngắn hơn 1**.

    Đưa thẳng vào model là đưa một biên độ chưa từng có trong dữ liệu huấn
    luyện. Phép kiểm đọc cây cú pháp vì chạy thật cần GPU.
    """
    import ast
    import inspect

    from voice_sidecar import engine

    cay = ast.parse(inspect.getsource(engine))
    ham = [n for n in ast.walk(cay)
           if isinstance(n, ast.FunctionDef) and n.name == "ghi_danh_kho"]
    assert ham, "khong tim thay `ghi_danh_kho`"
    than = ast.dump(ham[0])
    assert "'mean'" in than or '"mean"' in than, "khong thay phep trung binh"
    assert "norm" in than, "khong thay phep chuan hoa sau khi cong"


def test_ghi_danh_kho_KHONG_dung_chung_cua_voi_duong_cu():
    """Đường cũ phải giữ nguyên **không đổi một dòng** trong lúc còn đang đo.

    Một tham số `so_clip` thêm vào `/v1/enroll` sẽ đổi chữ ký của đường đang
    phục vụ khách, và khi ấy "A/B" không còn là A/B nữa.
    """
    import inspect

    from voice_sidecar import engine

    assert "so_clip" not in inspect.signature(engine.CongGiong.ghi_danh).parameters
    assert "so_clip" in inspect.signature(engine.CongGiong.ghi_danh_kho).parameters
