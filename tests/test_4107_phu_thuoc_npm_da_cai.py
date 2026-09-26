"""Bánh cóc cho `tools/check_phu_thuoc_npm.py` — chính nó phải cắn được.

## Vì sao có phép kiểm này

Công cụ ấy sinh ra sau khi **cùng một câu hỏi cắn sáu lần trong một ngày**
(25/09/2026): *"thứ này chạy được ở đây vì ở đây nó dựng từ một NGUỒN KHÁC với
production"*. Ba trong sáu ca là phụ thuộc npm đã khai mà chưa cài.

⭐ Nhưng một bộ đo mới thì **chưa biết nó bắt được gì** cho tới khi có người
   làm nó đỏ. Tệp này làm đúng việc đó — và nó chốt **tính chất**, ⛔ không
   chốt cách gõ, vì chính `test_970` đã dạy: chốt tên hàm thì đỏ oan ngày ai
   đó đổi cách hiện thực.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONG_CU = ROOT / "tools" / "check_phu_thuoc_npm.py"

def _nap():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_kiem_npm", CONG_CU)
    m = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(m)
    return m


def test_cong_cu_ton_tai_va_nap_duoc():
    assert CONG_CU.exists()
    _nap()


def test_gate_CO_goi_cong_cu_nay():
    """⛔ Một bộ đo không ai gọi thì không canh gì cả.

    ⭐ Chốt bằng cách tìm ĐƯỜNG DẪN tệp trong `gate.py`, ⛔ không tìm tên bước
       (tên bước là chữ hiển thị, đổi được mà không đổi hành vi).
    """
    van = (ROOT / "tools" / "gate.py").read_text(encoding="utf-8")
    assert "tools/check_phu_thuoc_npm.py" in van


def test_pham_vi_lay_tu_git_ls_files_khong_phai_glob():
    """🔴 `glob` sẽ quét cả `node_modules` của chính nó và cả cây tạm của phiên
    khác nằm trong kho (ca `LTTGateBaseline` 25/09: một worktree trong kho làm
    mọi bánh cóc quét-cả-cây đếm HAI LẦN).

    ⇒ Chốt **tính chất**: phạm vi không được chứa đường dẫn nào nằm dưới
    `node_modules`, và phải chứa `connector_runner` — thứ git thật có theo dõi.
    """
    m = _nap()
    thu_muc = m._thu_muc_co_lock()
    assert thu_muc, "pham vi RONG — bo do nay khong canh gi ca"
    assert not [d for d in thu_muc if "node_modules" in d]
    assert "connector_runner" in thu_muc


def test_moc_CHUA_CAI_chi_chua_thu_muc_CO_THAT():
    """Một mục trỏ tới thư mục không tồn tại là một miễn trừ che cho hư không."""
    m = _nap()
    thieu = [d for d in m.CHUA_CAI if not (ROOT / d / "package.json").exists()]
    assert thieu == [], f"`CHUA_CAI` tro toi thu muc khong co: {thieu}"


def test_TIEM_LOI_thieu_mot_goi_thi_bao_DUNG_thu_muc_va_lenh_sua(tmp_path):
    """⭐ Phép tiêm lỗi: dựng một thư mục npm **thiếu** gói, và đòi công cụ

    1. nói ra **đúng tên gói** thiếu, và
    2. in **câu lệnh sửa** — vì cái làm mất một lượt gate 21,8 phút ⛔ không
       phải việc *không phát hiện*, mà là thông điệp `Failed to resolve import`
       ⛔ không nói cho người đọc biết phải làm gì.
    """
    m = _nap()
    npm = __import__("shutil").which("npm") or __import__("shutil").which("npm.cmd")
    if npm is None:
        pytest.skip("npm khong co tren PATH — khong the do phep nay o day")

    d = tmp_path / "goi_thu"
    d.mkdir()
    (d / "package.json").write_text(json.dumps({
        "name": "goi-thu", "version": "1.0.0", "private": True,
        "dependencies": {"khong-he-ton-tai-goi-nay": "1.0.0"},
    }), encoding="utf-8")
    (d / "node_modules").mkdir()          # CÓ node_modules, nhưng RỖNG

    goc_cu = m.ROOT
    try:
        m.ROOT = d.parent
        van_de = m._thieu("goi_thu", npm)
    finally:
        m.ROOT = goc_cu

    assert van_de, "co node_modules RONG ma cong cu bao 'khong thieu gi'"
    assert any("khong-he-ton-tai-goi-nay" in str(v) for v in van_de), van_de


def test_chay_that_tren_kho_nay_PASS_hoac_noi_ro_vi_sao():
    """Chạy công cụ trên chính kho này. ⛔ Không đòi PASS mù: nếu nó FAIL thì
    thông điệp **phải** kèm câu lệnh `npm ci` cho từng thư mục."""
    # ⭐ `encoding="utf-8"` o CA HAI dau ong, dung quy uoc `gate.py:1219` da
    #    dung. Bo no ra thi luong doc giai ma bang cp1252 mac dinh, nem
    #    `UnicodeDecodeError` NGAY TRONG luong doc, va `ra.stdout` thanh `None`
    #    — mot phep do khong co cau tra loi, khong phai mot cau tra loi xau.
    #    Da can that 26/09: sua ben GHI sang UTF-8 xong thi ben DOC vo.
    ra = subprocess.run([sys.executable, str(CONG_CU)], cwd=ROOT,
                        capture_output=True, text=True,
                        encoding="utf-8", errors="replace")
    out = ra.stdout or ""
    assert "RESULT:" in out, out[-500:]
    if "RESULT: FAIL" in out:
        assert "npm ci" in out, "FAIL ma khong noi cach sua"
