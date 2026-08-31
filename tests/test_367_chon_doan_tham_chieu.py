"""Chọn đoạn tham chiếu tốt nhất trong clip dài — và hai lỗi bộ chọn đã mắc.

## Vì sao bộ chọn tồn tại

SDK cắt **8 giây đầu một cách mù** (`_MAX_REF_SECONDS = 8.0`). Clip 30 giây thì
22 giây sau không bao giờ được dùng. Ta có cả clip nên chọn được.

## Hai lỗi CHÍNH BỘ CHỌN đã mắc, và cả hai chỉ lộ ra khi chạy

  1. **Đoạn dài hơn cửa sổ bị loại hẳn.** Bản đầu chỉ ghép các đoạn nguyên vẹn
     giữa hai khoảng lặng. Trên clip thử, đoạn sạch dài 9 giây > cửa sổ 8 giây
     nên bị bỏ, và ứng viên duy nhất còn lại là 6 giây **nhiễu** ở đầu. Bộ chọn
     khi đó tệ hơn cả không chọn.
  2. **Mốc so sánh bị chính phần xấu kéo lệch.** Bản đầu lấy `emb(cả clip)` làm
     mốc "đại diện". Trên một clip một phần ba nhiễu, nó chọn đúng đoạn nhiễu
     (0,8745 so với 0,8674) — vì đoạn đại diện nhất cho một clip bẩn là đoạn bẩn.

Cả hai đều là lỗi **thiết kế**, không phải lỗi gõ nhầm, và không lỗi nào ném.
Chúng chỉ hiện ra khi cho một clip có hình dạng thật đi qua và **nhìn kết quả**.
"""
from __future__ import annotations

import numpy as np
import pytest

SR = 24_000


def _tieng(giay: float, muc: float = 0.25, f0: float = 140.0, hat: int = 7):
    rng = np.random.default_rng(hat)
    t = np.arange(int(SR * giay)) / SR
    return ((np.sin(2 * np.pi * f0 * t) + 0.4 * np.sin(2 * np.pi * 3 * f0 * t)) * muc
            + rng.standard_normal(int(SR * giay)) * 0.01).astype(np.float32)


def _im(giay: float):
    return np.zeros(int(SR * giay), dtype=np.float32)


def _clip_ba_vung():
    """0–6s nhiễu · 6,6–15,6s sạch · 16,2–24,2s vỡ tiếng."""
    rng = np.random.default_rng(11)
    nhieu = (_tieng(6) + rng.standard_normal(int(SR * 6)) * 0.12).astype(np.float32)
    return np.concatenate([nhieu, _im(0.6), _tieng(9), _im(0.6),
                           np.clip(_tieng(8, muc=1.4), -1, 1)])


def _ma_hoa_gia(w, sr):
    """Đặc trưng thô: trọng tâm phổ + mức. Đủ để phân biệt ba vùng, và **không
    cần tải model 28 MB** — phép chọn phải kiểm được mà không có GPU."""
    w = np.asarray(w, dtype=np.float64)
    if not len(w):
        return np.zeros(3)
    pho = np.abs(np.fft.rfft(w * np.hanning(len(w))))
    tan = np.fft.rfftfreq(len(w), 1 / sr)
    tam = float((pho * tan).sum() / max(pho.sum(), 1e-9))
    return np.array([tam / 1000.0, float(np.sqrt((w ** 2).mean())) * 10, 1.0])


# ═══════════════════════════════════ cắt ở đáy vùng im ══════════════════════

def test_cat_tai_DAY_vung_im_chu_khong_o_ria():
    """Thuật toán `openvpi/audio-slicer`: cắt tại khung RMS thấp nhất.

    ⭐ Vì sao quan trọng: nhát cắt rơi vào chỗ yên nhất thì không cắt giữa một
       âm tiết. Trượt một lưới đều thì có — và phép cắt im hai đầu của SDK
       **không sửa được**, vì nó chỉ cắt im, không cắt chữ.
    """
    from voice_sidecar.chon_doan import ranh_gioi_im

    ban = np.concatenate([_tieng(2.0), _im(1.0), _tieng(2.0)])
    moc = ranh_gioi_im(ban, SR)
    assert len(moc) == 1, f"mong doi mot ranh gioi, duoc {len(moc)}"
    giay = moc[0] / SR
    assert 2.0 <= giay <= 3.0, (
        f"nhat cat o {giay:.2f}s — phai nam TRONG vung im (2,0–3,0s)")


def test_vung_im_ngan_khong_thanh_ranh_gioi():
    """`min_interval` 300 ms: một nhịp ngắt giữa hai từ không phải chỗ cắt."""
    from voice_sidecar.chon_doan import ranh_gioi_im

    ban = np.concatenate([_tieng(2.0), _im(0.1), _tieng(2.0)])
    assert ranh_gioi_im(ban, SR) == []


# ═══════════════════════════════════ lỗi ① · đoạn quá dài ═══════════════════

def test_doan_dai_hon_cua_so_van_sinh_ra_ung_vien():
    """🔴 Lỗi ①: đoạn nói liền 9 giây từng bị loại hẳn.

    Người nói liền 9 giây không có khoảng nghỉ 300 ms thì cắt vào giữa lời là
    không tránh được — nhưng bỏ luôn cả đoạn thì tệ hơn nhiều, vì thứ còn lại có
    thể là đoạn xấu nhất của clip.
    """
    from voice_sidecar.chon_doan import ung_vien

    ban = np.concatenate([_im(0.5), _tieng(9.0), _im(0.5)])
    uv = ung_vien(ban, SR)
    assert uv, "doan 9 giay dai hon cua so 8 giay ma khong sinh ra ung vien nao"
    for a, b in uv:
        assert (b - a) / SR <= 8.05, f"ung vien {(b - a) / SR:.2f}s vuot cua so"


# ═══════════════════════════════════ lỗi ② · mốc bị kéo lệch ════════════════

def test_khong_chon_vung_NHIEU_du_no_dai_dien_cho_ca_clip():
    """🔴 Lỗi ②: mốc "cả clip" bị chính phần xấu kéo lệch.

    Đoạn đại diện nhất cho một clip bẩn chính là đoạn bẩn. Mốc phải là ước lượng
    BỀN VỮNG — nửa ứng viên có SNR cao hơn — chứ không phải trung bình thô.
    """
    from voice_sidecar.chon_doan import chon

    kq = chon(_clip_ba_vung(), SR, bo_ma_hoa=_ma_hoa_gia)
    assert kq.da_chon_that, f"khong chon duoc: {kq.ly_do}"
    assert 6.0 <= kq.bat_dau_s <= 8.5, (
        f"chon {kq.bat_dau_s}s–{kq.ket_thuc_s}s — vung SACH la 6,6–15,6s. "
        f"Chon ngoai do nghia la moc so sanh dang bi vung xau keo lech.")
    assert kq.ket_thuc_s <= 16.0


def test_khong_chon_vung_VO_TIENG():
    """Vỡ tiếng làm méo âm sắc — tức méo đúng thứ đang đo."""
    from voice_sidecar.chon_doan import chon

    kq = chon(_clip_ba_vung(), SR, bo_ma_hoa=_ma_hoa_gia)
    assert kq.bat_dau_s < 16.0, "chon vao vung vo tieng (16,2s tro di)"


# ═══════════════════════════════════ không bao giờ tệ hơn ═══════════════════

def test_clip_ngan_hon_cua_so_thi_dung_nguyen():
    from voice_sidecar.chon_doan import chon

    kq = chon(_tieng(5.0), SR, bo_ma_hoa=_ma_hoa_gia)
    assert kq.bat_dau_s == 0.0
    assert 4.9 <= kq.ket_thuc_s <= 5.1
    assert not kq.da_chon_that, "clip ngan thi khong co gi de chon"


def test_khong_ung_vien_nao_thi_LUI_ve_8_giay_dau():
    """⛔ Một bộ chọn có thể TỪ CHỐI là một bộ chọn thêm một đường hỏng mới.

    Clip toàn im: không đoạn nào qua cổng. Phải trả về đúng hành vi mặc định của
    SDK, không được ném.
    """
    from voice_sidecar.chon_doan import CUA_SO_S, chon

    kq = chon(_im(20.0), SR, bo_ma_hoa=_ma_hoa_gia)
    assert (kq.bat_dau_s, kq.ket_thuc_s) == (0.0, CUA_SO_S)
    assert not kq.da_chon_that
    assert "lui" in kq.ly_do.lower()


def test_ket_qua_luon_giai_thich_duoc_vi_sao():
    """Một phép chọn ngầm là một phép chọn không ai truy được."""
    from voice_sidecar.chon_doan import chon

    kq = chon(_clip_ba_vung(), SR, bo_ma_hoa=_ma_hoa_gia)
    assert kq.ly_do, "phai noi vi sao chon"
    assert kq.so_ung_vien > 0
    assert kq.bang_diem, "phai kem bang diem de doi chieu"


# ═══════════════════════════════════ không trôi khỏi SDK ════════════════════

def test_cua_so_doc_tu_SDK_chu_khong_go_lai():
    """⛔ Gõ cứng 8.0 thì upstream đổi `_MAX_REF_SECONDS` là ta chọn một cửa sổ
    rồi SDK vẫn cắt tiếp — im lặng."""
    import pathlib

    from voice_sidecar.chon_doan import CUA_SO_S

    ma = (pathlib.Path(__file__).resolve().parents[1]
          / "voice_sidecar" / "chon_doan.py").read_text(encoding="utf-8")
    assert "_MAX_REF_SECONDS as CUA_SO_S" in ma, (
        "`CUA_SO_S` phai NHAP tu SDK, khong duoc go lai mot hang so thu hai")
    assert CUA_SO_S == pytest.approx(8.0), (
        f"CUA_SO_S = {CUA_SO_S}. Neu upstream that su doi con so nay thi cap "
        f"nhat phep kiem; neu khong thi mot cho nao do da go cung sai.")


# ═══════════════════════════════════ nối vào đường ghi danh ═════════════════

def test_chon_hong_thi_DUNG_NGUYEN_CLIP_chu_khong_nem(tmp_path):
    """⛔ Một bước tối ưu không được thêm một đường hỏng mới.

    `_chon_doan_tham_chieu` chạy trong venv giọng và cần `soundfile`. Ở venv nền
    tảng (nơi phép kiểm này chạy) không có nó — nên đây đúng là ca "chọn hỏng",
    và nó phải lui về **nguyên tệp gốc**, không được ném lên trên.
    """
    from voice_sidecar.engine import CongGiong

    tep = tmp_path / "x.wav"
    tep.write_bytes(b"RIFF____WAVEfmt ")      # không phải wav hợp lệ
    duong, ho_so = CongGiong._chon_doan_tham_chieu(None, str(tep))

    assert duong == str(tep), "chon hong ma khong tra ve tep goc"
    assert ho_so["da_chon"] is False
    assert ho_so.get("ly_do"), "phai noi vi sao khong chon duoc"


def test_ghi_danh_luon_bao_ve_ho_so_chon():
    """Kết quả ghi danh phải mang `chon_doan` — không có nó thì phép chọn là một
    phỏng đoán chạy ngầm, đúng lớp lỗi cả app này đi sửa."""
    import inspect

    from voice_sidecar.engine import CongGiong

    ma = inspect.getsource(CongGiong.ghi_danh)
    assert '"chon_doan"' in ma, (
        "`ghi_danh` khong tra ve `chon_doan`. Khach hoi 'sao giong khong giong "
        "toi' thi khong co gi tra loi ho da lay doan nao.")
    assert "_chon_doan_tham_chieu" in ma, "chua goi bo chon truoc khi enroll"


def test_tep_tam_cua_bo_chon_duoc_don(tmp_path):
    """Đoạn đã chọn ghi ra một tệp tạm — quên xoá là rò một tệp mỗi lượt ghi danh."""
    import inspect

    from voice_sidecar.engine import CongGiong

    ma = inspect.getsource(CongGiong.ghi_danh)
    assert "finally:" in ma and "unlink" in ma, (
        "tep tam cua bo chon phai duoc xoa trong `finally` — mot lan enroll "
        "hong giua chung khong duoc de lai rac")


def test_ghi_danh_dich_loi_HA_TANG_dung_lop():
    """🔴 Bản sửa 09b5ab6 BỎ SÓT chỗ này.

    `_ghi_danh` cũng dịch `LoiSidecar` thành `LoiGiongNoi` — tức `LoiNguoiGoi`,
    tức nền tảng **không thử lại** — trong khi thông điệp hứa "vui lòng thử lại".
    Mỗi lần deploy khởi động lại cổng giọng, mọi lượt ghi danh đang bay hỏng
    vĩnh viễn thay vì được xếp lại vài giây sau.
    """
    import inspect

    from apps.ltt_voice import jobs

    ma = inspect.getsource(jobs._ghi_danh)
    i = ma.find("except sidecar_client.LoiSidecar")
    assert i > 0, "mat nhanh xu ly LoiSidecar trong _ghi_danh"
    nhanh = "\n".join(d for d in ma[i:].splitlines()
                      if not d.lstrip().startswith("#"))[:400]
    assert "raise LoiHaTang(" in nhanh, (
        "nhanh `LoiSidecar` cua `_ghi_danh` phai nem `LoiHaTang`. Nem "
        "`LoiGiongNoi` la noi voi khach 'vui long thu lai' roi tu quyet khong "
        "thu lai.")


# ═══════════════════════════════════ DNSMOS ═════════════════════════════════

def test_ghim_dnsmos_day_du_ba_thu():
    """⛔ Ghim COMMIT + sha256 + kích thước, cả ba cùng lúc.

    `microsoft/DNS-Challenge` là kho đang sống. Tải theo `master` thì hai lần cài
    cách nhau vài tháng có thể lấy hai model khác nhau — và điểm chất lượng đổi
    mà không ai đổi một dòng mã nào.
    """
    from voice_sidecar.tai_dnsmos import COMMIT, SHA256, SO_BYTE, URL

    assert len(COMMIT) == 40 and all(c in "0123456789abcdef" for c in COMMIT), (
        f"COMMIT phai la mot SHA day du, duoc {COMMIT!r}")
    assert len(SHA256) == 64
    assert SO_BYTE == 1_157_965
    assert COMMIT in URL, "URL khong ghim theo commit — dang tai theo nhanh"
    assert "master" not in URL and "/main/" not in URL


def test_he_so_hieu_chuan_dnsmos_khop_ban_goc():
    """Đầu ra thô của model KHÔNG phải thang MOS.

    Bỏ bước hiệu chuẩn cho ra những con số nằm ngoài 1–5, và không gì báo. Ba bộ
    hệ số chép nguyên từ `dnsmos_local.py` (bản không cá nhân hoá).
    """
    from voice_sidecar.dnsmos import _HE_SO_BAK, _HE_SO_OVR, _HE_SO_SIG

    assert _HE_SO_SIG == (-0.08397278, 1.22083953, 0.0052439)
    assert _HE_SO_BAK == (-0.13166888, 1.60915514, -0.39604546)
    assert _HE_SO_OVR == (-0.06766283, 1.11546468, 0.04602535)


def test_dnsmos_thieu_model_thi_tra_None_chu_khong_nem():
    """`None` nghĩa là KHÔNG BIẾT, và người gọi phải xử lý nó khác với "điểm 0"."""
    import numpy as np

    from voice_sidecar import dnsmos

    truoc = dnsmos._PHIEN
    dnsmos._PHIEN = None
    try:
        import os
        cu = os.environ.get("LTT_DNSMOS_DIR")
        os.environ["LTT_DNSMOS_DIR"] = "/khong-co-thu-muc-nay"
        try:
            assert dnsmos.cham(np.zeros(1000, np.float32), 16000) is None
        finally:
            if cu is None:
                os.environ.pop("LTT_DNSMOS_DIR", None)
            else:
                os.environ["LTT_DNSMOS_DIR"] = cu
    finally:
        dnsmos._PHIEN = truoc


def test_diem_chat_luong_luon_NOI_RA_dang_dung_thang_nao():
    """Hai thang khác nhau không so được với nhau.

    DNSMOS OVRL nằm trong 1–5; SNR tính bằng dB và có thể âm. Trộn hai thang
    trong một cột số là một bảng nhìn được mà đọc sai.
    """
    import numpy as np

    from voice_sidecar.chon_doan import diem_chat_luong

    _, nguon = diem_chat_luong(_tieng(2.0), SR)
    assert nguon in ("dnsmos_ovrl", "snr_db"), f"nguon la {nguon!r}"
