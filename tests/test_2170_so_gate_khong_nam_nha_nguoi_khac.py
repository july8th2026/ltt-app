"""Sổ phán quyết gate phải nằm ở `.gate/`, KHÔNG nằm trong `test-results/`.

🔴 **Vì sao tệp này tồn tại.** Đêm 23–24/09/2026 sổ phán quyết của một lô gate
   **biến mất** khỏi `test-results/gates/` giữa hai lượt chạy. Ba giả thuyết đã
   bị loại **bằng đo**, không bằng tranh luận:

   · `git clean -fdX` — lệnh trong tài liệu có phạm vi `apps/`; và `tmp/` sống
     trong khi `test-results/` mất, dù hai dòng nằm sát nhau trong `.gitignore`.
   · quét toàn máy — bản ghi 22/09 ở hai cây khác còn nguyên.
   · Playwright MCP/CLI — một mốc hy sinh đặt lúc 00:12 **sống sót** qua hai lượt
     Playwright CLI có dấu vết lúc 00:14 và 00:21.

⛔ **Thủ phạm tới giờ vẫn chưa biết — và đó chính là lý do phải dời.** Điều không
   phụ thuộc vào thủ phạm là CHỖ ĐỨNG: `.gitignore` xếp `/test-results/` ngay
   dưới tiêu đề `# Playwright CLI temp`, tức đó là thư mục RA của một công cụ
   khác; và bộ CHẠY TEST của Playwright *dọn sạch `outputDir` ở đầu mỗi lượt*
   theo đúng tài liệu của nó. Một sổ phán quyết không được nằm trong nhà người
   khác, dù hôm nay chưa ai dọn nó.

⛔ **Và mất sổ thì KHÔNG bao giờ đỏ:** `l3_lai_bi_chan` **cố ý** cho qua khi
   không đọc được bản ghi (một cổng từ chối vì chính nó hỏng là một cổng người ta
   sẽ tắt). Nên cái cửa "MỘT L3 mỗi nhánh" mở ra **im lặng**.

⭐ Mọi phép kiểm dưới đây chạy trên `tmp_path`, ⛔ không đụng kho thật — nên
   chúng không đổi kết quả theo việc hôm nay cây có sổ hay không.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]


@pytest.fixture()
def g():
    spec = importlib.util.spec_from_file_location(
        "_gate_so", GOC / "tools" / "gate.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["_gate_so"] = m
    spec.loader.exec_module(m)
    return m


def _ban_ghi(thu_muc: Path, *, nhanh: str, gio_truoc: float,
             ket: str = "FAIL 2/34") -> Path:
    """Một bản ghi L3 `gio_truoc` giờ trước, đúng hình dạng `gate.py` ghi."""
    thu_muc.mkdir(parents=True, exist_ok=True)
    luc = datetime.now(timezone.utc) - timedelta(hours=gio_truoc)
    ma = luc.strftime("%Y%m%dT%H%M%SZ")
    r = {"id": f"{ma}-1234", "luc": luc.isoformat(timespec="seconds"),
         "ho_so": "day-du", "ket_qua": ket, "nhanh": nhanh,
         "cay_da_doi_giua_chung": False, "sha": "deadbeef"}
    tep = thu_muc / f"{ma}-1234.json"
    tep.write_text(json.dumps(r), encoding="utf-8")
    return tep


# ══════════════════════════════════════════════════════════════════════════
# 1. CHỖ GHI
# ══════════════════════════════════════════════════════════════════════════

def test_ghi_vao_gate_KHONG_vao_test_results(g, tmp_path):
    """Chốt cơ học chỗ ghi — đây là cả mục đích của lần dời."""
    assert g.thu_muc_so(tmp_path) == tmp_path / ".gate"
    assert "test-results" not in str(g.thu_muc_so(tmp_path))


def test_khong_con_duong_test_results_go_tay_trong_ma(g):
    """Đối chứng cơ học: không còn ai gõ tay `test-results`/`gates` làm chỗ ghi.

    ⚠️ Chuỗi vẫn được phép xuất hiện trong chú thích và trong `TEN_THU_MUC_SO_CU`
       (đường đọc chuyển giao), nên phép kiểm chốt đúng **dạng gõ tay đường dẫn**.
    """
    van = (GOC / "tools" / "gate.py").read_text(encoding="utf-8")
    assert 'ROOT / "test-results" / "gates"' not in van, \
        "van con go tay duong cu lam cho ghi"


# ══════════════════════════════════════════════════════════════════════════
# 2. CHỖ ĐỌC — phải đọc CẢ HAI, nếu không thì cửa mở ra đúng lúc dời
# ══════════════════════════════════════════════════════════════════════════

def test_ban_ghi_o_cho_MOI_van_chan(g, tmp_path):
    _ban_ghi(g.thu_muc_so(tmp_path), nhanh="phien/x", gio_truoc=1.0)
    assert g.l3_lai_bi_chan(g.moi_cho_doc_so(tmp_path), "phien/x")


def test_ban_ghi_o_cho_CU_van_chan(g, tmp_path):
    """🔴 Đối chứng của cả lần dời.

    Nếu chỉ đọc chỗ mới, thì đúng lúc dời, mọi nhánh đã L3 trong 12 giờ qua
    **được thêm một L3 miễn phí** — tức lần dời tự tay mở cái cửa mà nó đang
    bảo vệ.
    """
    _ban_ghi(g.thu_muc_so_cu(tmp_path), nhanh="phien/y", gio_truoc=1.0)
    assert g.l3_lai_bi_chan(g.moi_cho_doc_so(tmp_path), "phien/y"), \
        "ban ghi o cho CU khong con chan — cua mo ra dung luc dời"


def test_duong_doc_cu_TU_HET_HAN_theo_cua_so(g, tmp_path):
    """⭐ Đường đọc cũ không cần ai nhớ ngày xoá.

    Nó hết hạn bằng **một mệnh đề**, không bằng lời hứa của người viết: một bản
    ghi quá `CUA_SO_L3_LAI_GIO` thì tự hết hiệu lực phán quyết, nên chỗ cũ không
    còn đóng góp gì. Đổi hằng thì hai thứ vẫn khớp.
    """
    _ban_ghi(g.thu_muc_so_cu(tmp_path), nhanh="phien/z",
             gio_truoc=g.CUA_SO_L3_LAI_GIO + 1.0)
    assert not g.l3_lai_bi_chan(g.moi_cho_doc_so(tmp_path), "phien/z")


def test_thu_muc_vang_mat_KHONG_phai_loi(g, tmp_path):
    """Cây chưa chạy gate lần nào thì chưa có sổ — không được nổ, không được chặn."""
    assert g.l3_lai_bi_chan(g.moi_cho_doc_so(tmp_path), "phien/moi") == ""


def test_van_nhan_MOT_Path_nhu_truoc(g, tmp_path):
    """Tương thích ngược: các phép kiểm cũ truyền MỘT `Path`, không phải danh sách."""
    d = tmp_path / ".gate"
    _ban_ghi(d, nhanh="phien/w", gio_truoc=0.5)
    assert g.l3_lai_bi_chan(d, "phien/w")


def test_lay_ban_ghi_MOI_NHAT_qua_ca_hai_cho(g, tmp_path):
    """Hai chỗ cùng có bản ghi ⇒ phán quyết là cái MỚI NHẤT, không phải cái đọc trước."""
    _ban_ghi(g.thu_muc_so_cu(tmp_path), nhanh="phien/v", gio_truoc=5.0,
             ket="FAIL 9/34")
    _ban_ghi(g.thu_muc_so(tmp_path), nhanh="phien/v", gio_truoc=0.5,
             ket="PASS 34/34")
    moi_nhat, gio = g._l3_trong_cua_so(g.moi_cho_doc_so(tmp_path), "phien/v")
    assert moi_nhat is not None and moi_nhat["ket_qua"] == "PASS 34/34", \
        f"lay sai ban ghi: {moi_nhat}"
    assert gio < 1.0


# ══════════════════════════════════════════════════════════════════════════
# 3. `.gate/` phải ở CẢ HAI danh sách — chốt ở MỘT chỗ khác
# ══════════════════════════════════════════════════════════════════════════
#
# 🔴 `.codex` dính lần một, `.superpowers` dính lần hai (23/09): một thư mục
#    được thêm vào danh sách bỏ qua của git nhưng KHÔNG vào `/XD` của đường lui
#    `robocopy` — mà đường đó chép CẢ CÂY sống lên production, kể cả tệp chưa
#    theo dõi. `.gate/` là ứng viên thứ ba.
#
# ⭐ Luật đó được chốt ở ĐÚNG MỘT chỗ, và `.gate` đã được thêm vào đó:
#      `test_394_nen_da_phien.py::test_kho_ket_qua_nam_ngoai_git_va_ngoai_deploy`
#    ⛔ Đừng nhân bản nó về đây. Hai chỗ khai cùng một điều thì không ai bắt
#    khớp chúng, và cái ở dưới sẽ mục — thêm một thư mục công cụ mới thì chỉ
#    một trong hai chỗ được cập nhật, và cái còn lại nói dối.

def test_moc_thoi_gian_dung_time_time_khong_lech_mui(g, tmp_path):
    """Bản ghi ghi giờ UTC; cửa sổ đo bằng `time.time()`. Lệch múi thì cửa sổ sai 7 giờ."""
    _ban_ghi(g.thu_muc_so(tmp_path), nhanh="phien/tz", gio_truoc=0.0)
    _, gio = g._l3_trong_cua_so(g.moi_cho_doc_so(tmp_path), "phien/tz",
                                bay_gio=time.time())
    assert abs(gio) < 0.1, f"lech mui gio: {gio:.2f} gio thay vi ~0"
