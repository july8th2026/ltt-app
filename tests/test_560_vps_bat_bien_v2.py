"""VPS V2 Pha 10 — bánh cóc: giữ những bất biến mà chín pha trước vừa dựng.

Bộ này **không** kiểm một tính năng nào. Nó kiểm rằng bốn khuôn hỏng đã sửa
không quay lại — và cả bốn đều thuộc loại **hỏng im lặng**: chúng không làm test
nào khác đỏ, không làm log nào đỏ, chỉ làm hệ thống nói dối.

| Khuôn | Sửa ở pha | Nếu quay lại |
|---|---|---|
| ghi thẳng `may.trang_thai` | 01 | hai nguồn sự thật, và chúng sẽ lệch |
| `sleep()` thay cho tính đúng | 02 | "đã xong" cho một việc chưa xong |
| POST rồi kết luận, không chờ | 02–04 | ba lỗi P0 gốc |
| nuốt ngoại lệ không có lý do | 10 | một lỗi tiền/dữ liệu biến mất |

⚠️ Mỗi phép kiểm ở đây đọc **AST**, không đọc chuỗi. Một phép kiểm đọc chuỗi sẽ
   báo động trên chính đoạn chú thích giải thích nó — và cách sửa duy nhất khi
   đó là bỏ chú thích, tức phạt đúng việc giải thích.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent
KHU = GOC / "apps" / "vps"


def _cay(p: pathlib.Path) -> ast.Module:
    return ast.parse(p.read_text(encoding="utf-8"), filename=str(p))


def _moi_tep():
    return sorted(KHU.rglob("*.py"))


# ── 1. Một đường ghi duy nhất cho trạng thái máy ────────────────────────────

def test_chi_trang_thai_may_duoc_ghi_thang_vao_may_trang_thai():
    """ADR-01: `trang_thai` là **hình chiếu**, tính ở đúng một chỗ.

    Ai gán thẳng nó ở nơi khác là đang dựng nguồn sự thật thứ hai, và hai nguồn
    thì sớm muộn lệch nhau — ở đây là lệch giữa thứ khách nhìn thấy và thứ hệ
    thống tin.

    🔴 Bảng thao tác cố ý dùng tên cột **`tinh_trang`** chứ không `trang_thai`.
       Trùng tên thì phép kiểm này không phân biệt được `op.trang_thai = XONG`
       (hợp lệ) với `may.trang_thai = "dang_chay"` (bug), và nó sẽ hoặc báo động
       giả, hoặc bị nới lỏng rồi bỏ lọt cả thật.
    """
    pham = []
    for p in _moi_tep():
        if p.name == "trang_thai_may.py":
            continue
        for n in ast.walk(_cay(p)):
            if not isinstance(n, ast.Assign):
                continue
            for dich in n.targets:
                if isinstance(dich, ast.Attribute) and dich.attr == "trang_thai":
                    pham.append(f"{p.relative_to(GOC)}:{n.lineno}")
    assert pham == [], (
        f"ghi thang `.trang_thai` ngoai `trang_thai_may.dat()`: {pham}")


def test_khong_ai_dung_setattr_de_lach_luat_tren():
    """Một phép kiểm đọc phép gán thì `setattr()` đi vòng qua được."""
    pham = []
    for p in _moi_tep():
        for n in ast.walk(_cay(p)):
            if (isinstance(n, ast.Call)
                    and getattr(n.func, "id", "") == "setattr"
                    and len(n.args) >= 2
                    and isinstance(n.args[1], ast.Constant)
                    and n.args[1].value in ("trang_thai", "vong_doi",
                                            "dien_quan_sat")):
                pham.append(f"{p.relative_to(GOC)}:{n.lineno}")
    assert pham == [], f"lach bang setattr: {pham}"


# ── 2. Không có `sleep` nào làm nhiệm vụ của một phép kiểm ──────────────────

def test_khong_co_sleep_nao_trong_khu_VPS():
    """`sleep(5)` rồi kết luận là đoán, không phải đo.

    Chờ đúng cách nằm ở `services/tac_vu.py`: hỏi lại trạng thái, có trần, có
    phân loại lỗi. Một `sleep` nằm ngoài đó nghĩa là ai đó đang đoán lại.
    """
    pham = []
    for p in _moi_tep():
        for n in ast.walk(_cay(p)):
            if isinstance(n, ast.Call):
                ten = getattr(n.func, "attr", None) or getattr(n.func, "id", None)
                if ten == "sleep":
                    pham.append(f"{p.relative_to(GOC)}:{n.lineno}")
    assert pham == [], f"con `sleep` trong khu VPS: {pham}"


# ── 3. Mỗi nơi gọi lệnh ghi của Proxmox phải BIẾT tới bộ chờ ────────────────

#: Những phương thức của `ProxmoxClient` sinh ra một tác vụ nền.
#:
#: Đọc từ chính `proxmox.py` thì tốt hơn, nhưng ở đó không có gì đánh dấu chúng —
#: nên danh sách này là chép tay, và `test_danh_sach_lenh_ghi_van_dung_thuc_te`
#: canh cho nó khỏi lệch.
LENH_GHI = frozenset({"bat", "tat_mem", "tat_cung", "clone", "tao_may",
                      "xoa", "chup_anh", "xoa_anh", "khoi_phuc_anh"})

#: Module nào được phép gọi lệnh ghi. Danh sách **cho phép**, không phải cấm:
#: một module mới gọi Proxmox mà không ai để ý là đúng cách lỗi P0 quay lại.
DUOC_GOI_LENH_GHI = frozenset({
    "jobs.py",            # provision / rebuild / destroy
    "dieu_khien.py",      # bat / tat / khoi dong lai
    "sao_luu.py",         # chup anh / khoi phuc
    "proxmox.py",         # chinh no
})


def test_chi_nhung_module_da_biet_moi_goi_lenh_ghi_cua_proxmox():
    pham = {}
    for p in _moi_tep():
        if p.name in DUOC_GOI_LENH_GHI:
            continue
        for n in ast.walk(_cay(p)):
            if (isinstance(n, ast.Call)
                    and getattr(n.func, "attr", "") in LENH_GHI
                    and getattr(getattr(n.func, "value", None), "id", "")
                    in ("client", "px", "khach")):
                pham.setdefault(p.name, []).append(n.lineno)
    assert pham == {}, f"module la goi lenh ghi cua Proxmox: {pham}"


def test_moi_module_goi_lenh_ghi_deu_NHAP_bo_cho():
    """Không chứng minh được "có chờ", nhưng chứng minh được "có biết tới bộ chờ".

    Một module gọi `client.bat()` mà **không** nhắc tới `tac_vu` ở đâu cả thì
    gần như chắc chắn đang bắn-rồi-quên — đúng hình dạng của V-02.
    """
    for ten in ("jobs.py", "dieu_khien.py", "sao_luu.py"):
        p = next(x for x in _moi_tep() if x.name == ten)
        src = p.read_text(encoding="utf-8")
        assert "tac_vu" in src, f"{ten} goi lenh ghi ma khong biet toi bo cho"


def test_danh_sach_lenh_ghi_van_dung_thuc_te():
    """Bảng chép tay ở trên phải khớp `ProxmoxClient` thật.

    Thêm một lệnh ghi mới vào driver mà quên khai ở đây thì hai phép kiểm trên
    lặng lẽ thôi bảo vệ nó — và chúng vẫn xanh.
    """
    from apps.vps.services.proxmox import ProxmoxClient
    co = {x for x in dir(ProxmoxClient) if not x.startswith("_")}
    thieu = LENH_GHI - co
    assert thieu == set(), f"LENH_GHI khai ten khong co that: {thieu}"


# ── 4. Mọi lần nuốt ngoại lệ phải có lý do viết ra ──────────────────────────

def test_moi_except_pass_deu_co_chu_thich_giai_thich():
    """Nuốt một ngoại lệ không kèm lý do là xoá một bằng chứng.

    Không cấm nuốt — có những chỗ nuốt là đúng (máy đã tắt sẵn, cầu nối
    WebSocket đóng). Cấm **nuốt im lặng**: dòng `pass` phải có một chú thích
    ngay cạnh nói vì sao, để người đọc sau không phải đoán.
    """
    pham = []
    for p in _moi_tep():
        dong = p.read_text(encoding="utf-8").splitlines()
        for n in ast.walk(_cay(p)):
            if not isinstance(n, ast.ExceptHandler):
                continue
            if len(n.body) != 1 or not isinstance(n.body[0], ast.Pass):
                continue
            i = n.body[0].lineno - 1
            co_chu_thich = "#" in dong[i] or (i and "#" in dong[i - 1])
            if not co_chu_thich:
                pham.append(f"{p.relative_to(GOC)}:{n.body[0].lineno}")
    assert pham == [], f"nuot ngoai le khong noi vi sao: {pham}"


def test_khong_co_except_TRAN_nao():
    """`except:` bắt cả `KeyboardInterrupt` và `SystemExit`.

    Một worker không tắt được là một worker phải `kill -9`, và giữa lúc đó nó
    có thể đang ở giữa một lần khôi phục dữ liệu.
    """
    pham = []
    for p in _moi_tep():
        for n in ast.walk(_cay(p)):
            if isinstance(n, ast.ExceptHandler) and n.type is None:
                pham.append(f"{p.relative_to(GOC)}:{n.lineno}")
    assert pham == [], f"except tran: {pham}"


# ── 5. Migration: một đầu, và mỗi cột thêm đều gỡ được ─────────────────────

def test_chuoi_migration_chi_co_MOT_dau():
    """Hai đầu thì `alembic upgrade head` chết trên máy chủ, không phải ở đây."""
    import re
    revs, downs = {}, set()
    for p in (GOC / "alembic" / "versions").glob("*.py"):
        src = p.read_text(encoding="utf-8", errors="replace")
        r = re.search(r'^revision\s*=\s*["\']([^"\']+)', src, re.M)
        # down_revision co the la mot chuoi HOAC mot tuple nhieu chuoi (revision
        # MERGE noi hai head, vd `down_revision = ("a", "b")`).
        d = re.search(r"^down_revision\s*=\s*(.+)$", src, re.M)
        if r:
            revs[r.group(1)] = p.name
        if d:
            for m in re.finditer(r'["\']([^"\']+)["\']', d.group(1)):
                downs.add(m.group(1))
    dau = [k for k in revs if k not in downs]
    assert len(dau) == 1, f"co {len(dau)} dau: {[revs[k] for k in dau]}"


@pytest.mark.parametrize("ten", [
    "20260909_1000_vps_v2_tach_trang_thai.py",
    "20260909_1100_vps_v2_bang_thao_tac.py",
    "20260909_1200_vps_v2_cach_ly.py",
])
def test_moi_migration_cua_VPS_V2_deu_co_downgrade_that(ten):
    """`downgrade` rỗng nghĩa là không lùi được — và người ta chỉ biết lúc cần lùi."""
    src = (GOC / "alembic" / "versions" / ten).read_text(encoding="utf-8")
    than = src.split("def downgrade")[1]
    assert "op." in than, f"{ten}: downgrade khong lam gi"


# ── 6. Hai bảng từ vựng không được lệch nhau ────────────────────────────────

def test_moi_ma_tac_vu_deu_co_nhan_va_nguoc_lai():
    from apps.vps import nhan, trang_thai_may as tt
    assert set(nhan.TAC_VU) == set(tt.TAC_VU_DOC_QUYEN)


def test_moi_buoc_ma_ma_san_pham_ghi_ra_deu_co_nhan():
    """Một mã bước không có nhãn hiện ra nguyên văn trên trang của khách."""
    from apps.vps import nhan
    from apps.vps.services import dieu_khien, sao_luu
    for b in (dieu_khien.BUOC_GUI_TAT, dieu_khien.BUOC_CHO_TAT,
              dieu_khien.BUOC_GUI_BAT, dieu_khien.BUOC_CHO_BAT,
              sao_luu.BUOC_TAT_TRUOC, sao_luu.BUOC_KHOI_PHUC,
              sao_luu.BUOC_BAT_LAI):
        assert b in nhan.BUOC, b


def test_moi_lenh_dieu_khien_deu_anh_xa_toi_mot_tac_vu_hop_le():
    from apps.vps import trang_thai_may as tt
    from apps.vps.services import dieu_khien
    for lenh, (loai, dien) in dieu_khien.LENH.items():
        assert loai in tt.TAC_VU_DOC_QUYEN, lenh
        assert dien in tt.DIEN_MONG_MUON, lenh
