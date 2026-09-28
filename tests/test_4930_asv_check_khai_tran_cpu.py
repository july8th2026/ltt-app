"""B13 việc C4 — bánh cóc cho lớp lỗi "gọi engine NẶNG mà không bọc khai trần
CPU" (`tools/check_khai_tran_cpu.py`).

## Bối cảnh

Máy treo HAI lần 28/09 vì RapidOCR mặc định ăn 15,2/20 lõi và ⛔ không ai khai
trần. Cùng lớp lỗi đã xảy ra 25 ngày trước với demucs (03/09).

## 🔴 AST cấu trúc, ⛔ KHÔNG grep chuỗi — và tại sao bộ kiểm ở đây có HAI chiều

Người điều phối chỉnh lại đặc tả giữa chừng: một bánh cóc đếm CHUỖI (`import
onnxruntime` và `chan_loi(` cùng có mặt trong tệp) sẽ XANH GIẢ trên một tệp
gọi engine NGOÀI `with chan_loi():` — vì "có mặt" ⛔ không chứng minh "bọc
đúng chỗ". `tools/check_khai_tran_cpu.py` neo vào CHỖ GỌI ENGINE rồi hỏi CẤU
TRÚC (nằm trong with-block đã xác minh, hay đạt tới được từ một with-block
qua chuỗi gọi hàm trong CÙNG tệp).

⇒ Phép kiểm ở đây có HAI chiều bắt buộc, và chiều thứ hai mới là chiều PHÂN
   BIỆT "đo cách gõ" với "đo tính chất":

   1. **Tiêm DƯƠNG** (dễ): một tệp giả nhập engine, ⛔ không khai trần gì ⇒
      phải ĐỎ. Bỏ ra ⇒ XANH.
   2. 🔑 **Tiêm NGHỊCH** (khó, bắt buộc): lấy `do_vung_ocr.py` **đã vá THẬT**,
      bỏ **đúng** dòng `with chan_loi():`, **GIỮ NGUYÊN** `CPU_TRAN_LOI = 6`,
      `def chan_loi`, và mọi `import` ⇒ phải ĐỎ. Một bộ dò grep chuỗi sẽ XANH
      ở phép này vì mọi chuỗi cần thiết vẫn còn nguyên trong tệp.
"""
from __future__ import annotations

import json

from tools import check_khai_tran_cpu as k


# ══════════════════════════════════════════════════════════════════════════════
#  1. Tiêm DƯƠNG — bộ dò THẬT SỰ bắt được, có vế đối chứng
# ══════════════════════════════════════════════════════════════════════════════

def test_goi_engine_KHONG_boc_thi_BI_bat():
    xau = ("import onnxruntime\n\n"
           "def f():\n    return onnxruntime.InferenceSession('x')\n")
    assert k._vi_pham_mot_tep(xau, "t.py") == ["onnxruntime"]


def test_goi_engine_BOC_dung_with_thi_SACH():
    """Vế đối chứng — Tầng A: with-block xác thực (wrapper thật, cùng hàm)."""
    xau = ("import contextlib\n"
           "import onnxruntime\n\n"
           "@contextlib.contextmanager\n"
           "def chan_loi():\n"
           "    import psutil\n"
           "    psutil.Process().cpu_affinity([0, 1])\n"
           "    yield\n\n"
           "def f():\n"
           "    with chan_loi():\n"
           "        return onnxruntime.InferenceSession('x')\n")
    assert k._vi_pham_mot_tep(xau, "t.py") is None


def test_tep_KHONG_dung_thu_vien_nang_thi_sach():
    assert k._vi_pham_mot_tep("import json\nimport os\n", "t.py") is None


def test_moi_anchor_trong_nguyen_mau_deu_bi_bat_khi_KHONG_boc():
    ca = [
        ("RapidOCR('x')", "rapidocr"),
        ("onnxruntime.InferenceSession('x')", "onnxruntime"),
        ("WhisperModel('base')", "faster_whisper"),
        ("YOLO('x.pt')", "ultralytics"),
        ("cv2.VideoCapture('x.mp4')", "cv2"),
        ("whisperx.load_model('x')", "whisperx"),
        ("Pipeline.from_pretrained('x')", "pyannote"),
        ("torch.load('x.pt')", "torch"),
    ]
    for bieu_thuc, nhan in ca:
        xau = f"def f():\n    return {bieu_thuc}\n"
        assert k._vi_pham_mot_tep(xau, "t.py") == [nhan], bieu_thuc


# ══════════════════════════════════════════════════════════════════════════════
#  2. Tầng B — cùng TỆP, qua BIÊN HÀM (đúng hình dạng do_vung_ocr.py thật)
# ══════════════════════════════════════════════════════════════════════════════

def test_tang_B_dat_toi_qua_HAI_lop_ham_trong_cung_tep():
    """Đúng hình dạng thật: `with chan_loi():` bọc `_do_dai_chu_ocr()`, hàm đó
    gọi `_may()`, và `RapidOCR()` được dựng bên TRONG `_may()` — ba hàm, một
    tệp, một with duy nhất ở đầu chuỗi."""
    xau = (
        "import contextlib\n\n"
        "@contextlib.contextmanager\n"
        "def chan_loi():\n"
        "    import psutil\n"
        "    psutil.Process().cpu_affinity([0])\n"
        "    yield\n\n"
        "def do_dai_chu_ocr(duong):\n"
        "    with chan_loi():\n"
        "        return _do_dai_chu_ocr(duong)\n\n"
        "def _do_dai_chu_ocr(duong):\n"
        "    may = _may()\n"
        "    return may\n\n"
        "def _may():\n"
        "    from rapidocr_onnxruntime import RapidOCR\n"
        "    return RapidOCR()\n"
    )
    assert k._vi_pham_mot_tep(xau, "t.py") is None


def test_tang_B_KHONG_dat_toi_qua_module_KHAC():
    """Vế đối chứng — chuỗi gọi hàm đi RA NGOÀI tệp (hàm không định nghĩa
    trong CHÍNH tệp này) không được coi là đã chứng minh boc."""
    xau = (
        "import contextlib\n\n"
        "@contextlib.contextmanager\n"
        "def chan_loi():\n"
        "    import psutil\n"
        "    psutil.Process().cpu_affinity([0])\n"
        "    yield\n\n"
        "def do_dai_chu_ocr(duong):\n"
        "    with chan_loi():\n"
        "        return mot_module_khac.ham_ngoai(duong)\n\n"
        "def _may():\n"                       # KHONG duoc goi tu with-block
        "    from rapidocr_onnxruntime import RapidOCR\n"
        "    return RapidOCR()\n"
    )
    assert k._vi_pham_mot_tep(xau, "t.py") == ["rapidocr"]


# ══════════════════════════════════════════════════════════════════════════════
#  3. 🔑 PHÉP TIÊM NGHỊCH — trên chính do_vung_ocr.py THẬT (bắt buộc, đây là
#     phép duy nhất phân biệt "đo cách gõ" với "đo tính chất")
# ══════════════════════════════════════════════════════════════════════════════

def test_do_vung_ocr_that_XANH():
    duong = "apps/auto_scan_video/do_vung_ocr.py"
    nguon = (k.ROOT / duong).read_text(encoding="utf-8")
    assert k._vi_pham_mot_tep(nguon, duong) is None


def test_TIEM_NGHICH_bo_with_chan_loi_GIU_NGUYEN_moi_thu_khac_thi_DO():
    """🔴 Bài quan trọng nhất của cả bánh cóc.

    Xoá ĐÚNG dòng `with chan_loi():` (và un-indent dòng `return` bên trong)
    khỏi `_do_dai_chu_ocr` — GIỮ NGUYÊN `CPU_TRAN_LOI = 6`, `def chan_loi`,
    và MỌI `import`. Một bộ dò grep-chuỗi (bản đầu của tôi) sẽ XANH ở đây vì
    mọi chuỗi cần thiết vẫn còn nguyên trong tệp — chỉ có QUAN HỆ CẤU TRÚC
    (with có thật sự bọc lời gọi hay không) là thay đổi.
    """
    duong = "apps/auto_scan_video/do_vung_ocr.py"
    nguon = (k.ROOT / duong).read_text(encoding="utf-8")

    goc = ("    with chan_loi():\n"
           "        return _do_dai_chu_ocr(duong, so_khung=so_khung, tranh=tranh)\n")
    tiem_nghich = ("    return _do_dai_chu_ocr(duong, so_khung=so_khung, "
                   "tranh=tranh)\n")
    assert goc in nguon, "hinh dang ham do_dai_chu_ocr trong do_vung_ocr.py da doi"
    xau_tiem = nguon.replace(goc, tiem_nghich)
    assert xau_tiem != nguon

    # Doi chung: CPU_TRAN_LOI, def chan_loi, va import rapidocr van con nguyen.
    assert "CPU_TRAN_LOI = 6" in xau_tiem
    assert "def chan_loi(" in xau_tiem
    assert "from rapidocr_onnxruntime import RapidOCR" in xau_tiem

    assert k._vi_pham_mot_tep(xau_tiem, duong) == ["rapidocr"], (
        "bo `with chan_loi():` nhung van XANH — banh coc dang do CACH GO "
        "(chuoi co mat), khong phai TINH CHAT (co that su boc hay khong)")


# ══════════════════════════════════════════════════════════════════════════════
#  4. Ngoại lệ — mỗi dòng chỉ mở ĐÚNG một đường dẫn, ⛔ không nguyên khối, và
#     fail-closed khi thiếu lý do
# ══════════════════════════════════════════════════════════════════════════════

def test_ngoai_le_CHI_ap_dung_dung_DUONG_DAN_khai():
    xau = "def f():\n    return torch.load('x')\n"
    assert k._vi_pham_mot_tep(xau, "apps/auto_scan_video/cao_do.py") is None
    assert k._vi_pham_mot_tep(
        xau, "apps/auto_scan_video/cao_do_gia.py") == ["torch"]


def test_ngoai_le_moi_dong_deu_co_ly_do_doc_duoc():
    assert k._xac_thuc_ngoai_le() == []
    for duong, ly_do in k.NGOAI_LE.items():
        assert len(ly_do.strip()) > 20, f"{duong} thieu ly do doc duoc"


def test_xac_thuc_ngoai_le_bat_duoc_muc_thieu_ly_do(monkeypatch):
    monkeypatch.setitem(k.NGOAI_LE, "x/gia.py", "qua ngan")
    assert k._xac_thuc_ngoai_le() == ["x/gia.py"]


def test_main_TU_CHOI_chay_khi_ngoai_le_thieu_ly_do(monkeypatch):
    """🔴 Một mục miễn KHÔNG lý do là một lỗ im lặng — `main()` phải trả về
    lỗi ngay, ⛔ không được chạy tiếp rồi tình cờ ra 0 vi phạm."""
    monkeypatch.setitem(k.NGOAI_LE, "x/gia.py", "qua ngan")
    monkeypatch.setattr("sys.argv", ["check_khai_tran_cpu.py"])
    assert k.main() == 1


# ══════════════════════════════════════════════════════════════════════════════
#  5. Fail-CLOSED — mốc thiếu/hỏng phải ĐỎ
# ══════════════════════════════════════════════════════════════════════════════

def test_moc_thieu_thi_am_1(tmp_path, monkeypatch):
    monkeypatch.setattr(k, "BASELINE", tmp_path / "khong_ton_tai.json")
    assert k._moc() == -1


def test_moc_hong_thi_am_1(tmp_path, monkeypatch):
    hong = tmp_path / "hong.json"
    hong.write_text("{khong phai json hop le", encoding="utf-8")
    monkeypatch.setattr(k, "BASELINE", hong)
    assert k._moc() == -1


def test_main_FAIL_khi_moc_am(tmp_path, monkeypatch):
    monkeypatch.setattr(k, "BASELINE", tmp_path / "khong_ton_tai.json")
    monkeypatch.setattr(k, "quet", lambda: ([], 0, []))
    monkeypatch.setattr("sys.argv", ["check_khai_tran_cpu.py"])
    assert k.main() == 1


def test_main_FAIL_khi_TANG_so_voi_moc(tmp_path, monkeypatch):
    moc = tmp_path / "moc.json"
    moc.write_text(json.dumps({"max": 1}), encoding="utf-8")
    monkeypatch.setattr(k, "BASELINE", moc)
    monkeypatch.setattr(
        k, "quet",
        lambda: ([("a.py", ["torch"]), ("b.py", ["cv2"])], 2, []))
    monkeypatch.setattr("sys.argv", ["check_khai_tran_cpu.py"])
    assert k.main() == 1


def test_main_PASS_khi_BANG_moc(tmp_path, monkeypatch):
    moc = tmp_path / "moc.json"
    moc.write_text(json.dumps({"max": 2}), encoding="utf-8")
    monkeypatch.setattr(k, "BASELINE", moc)
    monkeypatch.setattr(
        k, "quet",
        lambda: ([("a.py", ["torch"]), ("b.py", ["cv2"])], 2, []))
    monkeypatch.setattr("sys.argv", ["check_khai_tran_cpu.py"])
    assert k.main() == 0


# ══════════════════════════════════════════════════════════════════════════════
#  6. Quét THẬT trên cây hiện tại khớp mốc đã chốt
# ══════════════════════════════════════════════════════════════════════════════

def test_quet_that_tren_cay_khop_voi_moc_da_chot():
    """Chính phép quét thật (⛔ không stub) phải ra đúng SỐ đã chốt VÀ đúng
    ĐỐI TƯỢNG — chốt đúng số nhưng không chốt đúng tên thì một tệp bị rào
    nhầm cái khác vẫn qua (sổ tay `hai-cho-khai-cung-mot-dieu-khong-ai-bat-khop`)."""
    vi_pham, so_tep, duoc_mien = k.quet()
    ket_qua = dict(vi_pham)
    assert "apps/video_assembly/services/engine/filters/motion.py" in ket_qua
    assert ket_qua[
        "apps/video_assembly/services/engine/filters/motion.py"] == ["cv2"]
    assert "apps/auto_scan_video/do_vung_ocr.py" not in ket_qua
    assert dict(duoc_mien).get("apps/auto_scan_video/cao_do.py") == ["torch"]
    assert "apps/auto_scan_video/demucs_runner.py" not in ket_qua
    assert so_tep > 100

    moc = json.loads(k.BASELINE.read_text(encoding="utf-8"))["max"]
    assert len(vi_pham) == moc, (
        f"cay hien tai co {len(vi_pham)} vi pham nhung moc dang chot {moc} — "
        "chay `python tools/check_khai_tran_cpu.py --update` neu day la mot "
        "thay doi CO CHU Y")


def test_TEN_BUOC_phoi_ra_cong_khai_cho_gate_goi():
    """`gate.py` phai goi TEN qua `k.TEN_BUOC`, ⛔ khong go lai chuoi rieng —
    dung ly le voi `gate.TRAN_N_GO_TAY`."""
    assert isinstance(k.TEN_BUOC, str) and k.TEN_BUOC
