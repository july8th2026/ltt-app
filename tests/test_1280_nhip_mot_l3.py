"""test_1280 — nhịp MỘT L3 mỗi phiên (hợp đồng vận hành §4.1–§4.6, chốt 16/09/2026).

## Chuyện đã xảy ra

133 bản ghi `test-results/gates/*.json` (04/09 → 15/09): **114** lượt L3, **100**
nằm trong chuỗi chạy lại cách nhau < 45 phút, chuỗi dài nhất **7 lượt = 170
phút**. Luật chữ *"chạy lại đúng phép đã đỏ"* đã có từ 08/09 và không ngăn được.

⇒ Hai chốt CƠ HỌC trong `tools/gate.py`, và tệp này canh chúng:

1. đỏ thì gate **in sẵn** lệnh chạy lại đúng phép đỏ + lệnh khép;
2. L3 gõ tay ngay sau một L3 đỏ trên cùng nhánh bị **từ chối**.

Cộng một chốt nguồn: nhịp chỉ được định nghĩa ở hợp đồng.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC / "tools"))

import gate  # noqa: E402
import ho_so_cay as hsc  # noqa: E402

HOP_DONG = GOC / "docs" / "00_LTT_OPERATING_CONTRACT.md"


def _buoc(ten: str, argv: list[str], *, ok: bool, tail: str = "",
          tep_loi: str = "") -> gate.Step:
    s = gate.Step(ten, argv, GOC, nhom="nang" if ten.startswith("bo test") else "tinh")
    s.ok = ok
    s.tail = tail
    s.tep_loi = tep_loi
    return s


# ── 1. Đỏ thì in đúng lệnh chạy lại ────────────────────────────────────────

def test_bo_test_do_cho_ra_pytest_DUNG_cac_tep_do(tmp_path, monkeypatch):
    """Đọc TRỌN đầu ra (`tep_loi`), không chỉ 40 dòng: danh sách FAILED của một
    lượt dài trôi khỏi `tail` — đúng ca 06/09 ghi trong `gate._run`."""
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    (tmp_path / "loi.log").write_text(
        "FAILED tests/test_12_a.py::test_x - AssertionError\n"
        "FAILED tests/test_12_a.py::test_y - AssertionError\n"
        "ERROR tests\\test_34_b.py - ImportError\n"
        "1 failed, 400 passed\n", encoding="utf-8")
    s = _buoc("bo test (song song)", [sys.executable, "tools/test_nhanh.py"],
              ok=False, tail="(40 dong cuoi khong co ten tep)", tep_loi="loi.log")
    assert gate.lenh_chay_lai([s]) == [
        "python -m pytest -q tests/test_12_a.py tests/test_34_b.py"]


def test_ba_tep_tro_len_thi_mang_tran_n6():
    tail = "\n".join(f"FAILED tests/test_{i}_x.py::t - E" for i in (1, 2, 3))
    s = _buoc("bo test (pham vi)", [sys.executable, "tools/test_nhanh.py"],
              ok=False, tail=tail)
    assert gate.lenh_chay_lai([s]) == [
        "python -m pytest -n 6 -q tests/test_1_x.py tests/test_2_x.py tests/test_3_x.py"]


def test_buoc_tinh_do_cho_ra_DUNG_lenh_cua_buoc_va_bo_qua_buoc_dat():
    do = _buoc("mypy", [sys.executable, "tools/check_mypy.py"], ok=False)
    dat = _buoc("ruff", [sys.executable, "tools/check_ruff.py"], ok=True)
    chua = _buoc("i18n", [sys.executable, "tools/check_i18n.py"], ok=None)  # type: ignore[arg-type]
    assert gate.lenh_chay_lai([do, dat, chua]) == ["python tools/check_mypy.py"]


def test_bo_test_khong_tach_duoc_tep_thi_van_tra_lenh_cua_buoc():
    """Đối chứng: pytest chết trước khi thu thập ⇒ không có dòng FAILED. Trả rỗng
    ở đây là im lặng đúng lúc người ta cần một lối đi hẹp hơn cả gate."""
    s = _buoc("bo test (song song)", [sys.executable, "tools/test_nhanh.py"],
              ok=False, tail="INTERNALERROR> boom")
    assert gate.lenh_chay_lai([s]) == ["python tools/test_nhanh.py"]


# ── 2. L3 lần hai ngay sau L3 đỏ bị từ chối ────────────────────────────────

def _ghi(thu_muc: Path, ten: str, **kv) -> None:
    ban_ghi = {"id": ten, "luc": "2026-09-16T08:00:00+00:00", "ho_so": "day-du",
               "ket_qua": "FAIL (1/33)", "nhanh": "phien/x", "sha": "abc123",
               "cay_da_doi_giua_chung": False,
               "buoc": [{"ten": "mypy", "ket": "FAIL", "giay": 120.0}],
               "lenh_chay_lai": ["python tools/check_mypy.py"]}
    ban_ghi.update(kv)
    (thu_muc / f"{ten}.json").write_text(json.dumps(ban_ghi), encoding="utf-8")


#: 09:00Z cùng ngày — một giờ sau bản ghi mặc định.
MOT_GIO_SAU = 1789549200.0


def test_L3_do_gan_day_thi_TU_CHOI_va_in_lenh_chay_lai_va_khep(tmp_path):
    _ghi(tmp_path, "a")
    ly_do = gate.l3_lai_bi_chan(tmp_path, "phien/x", bay_gio=MOT_GIO_SAU)
    assert "TU CHOI" in ly_do
    assert "python tools/check_mypy.py" in ly_do
    assert "--doi --tu abc123" in ly_do
    assert "--l3-lai" in ly_do
    assert all(ord(c) < 128 for c in ly_do), "dong in ra phai ASCII (cp1252)"


def test_L3_XANH_roi_van_TU_CHOI_L3_thu_hai(tmp_path):
    """🔴 Lỗ hổng chủ dự án chỉ ra 16/09: chốt đầu tiên chỉ chặn sau L3 ĐỎ, nên
    "pha 1 → L3 xanh, pha 2 → L3 xanh" vẫn lọt — đúng nhịp L3-mỗi-pha bị cấm.
    MỘT L3 mỗi nhánh; thay đổi sau đó khép bằng `--doi --tu <sha>`."""
    _ghi(tmp_path, "a", ket_qua="PASS")
    ly_do = gate.l3_lai_bi_chan(tmp_path, "phien/x", bay_gio=MOT_GIO_SAU)
    assert "TU CHOI" in ly_do
    assert "--doi --tu abc123" in ly_do
    assert "check_mypy" not in ly_do, "luot XANH khong co phep do nao de chay lai"
    assert all(ord(c) < 128 for c in ly_do)


@pytest.mark.parametrize("thay_doi, ly_do", [
    ({"cay_da_doi_giua_chung": True}, "luot truoc khong phai phan quyet"),
    ({"nhanh": "phien/khac"}, "nhanh khac"),
    ({"ho_so": "doi"}, "khong phai L3"),
    ({"luc": "2026-09-15T08:00:00+00:00"}, "qua cua so"),
])
def test_cac_truong_hop_DUOC_chay(tmp_path, thay_doi, ly_do):
    _ghi(tmp_path, "a", **thay_doi)
    assert gate.l3_lai_bi_chan(tmp_path, "phien/x", bay_gio=MOT_GIO_SAU) == "", ly_do


def test_luot_CAY_DA_DOI_khong_che_mot_phan_quyet_cu_hon(tmp_path):
    """Đỏ lúc 07:00, rồi một lượt cây-đổi lúc 08:00. Lượt sau không phải phán
    quyết, nên phán quyết đang đứng vẫn là lượt đỏ ⇒ vẫn chặn. Một bộ đọc lấy
    "bản ghi mới nhất" trần sẽ cho qua."""
    _ghi(tmp_path, "cu", luc="2026-09-16T07:00:00+00:00")
    _ghi(tmp_path, "moi", luc="2026-09-16T08:00:00+00:00",
         cay_da_doi_giua_chung=True)
    assert gate.l3_lai_bi_chan(tmp_path, "phien/x", bay_gio=MOT_GIO_SAU)


def test_chi_ban_ghi_MOI_NHAT_quyet_dinh_noi_dung(tmp_path):
    """Đỏ rồi xanh ⇒ thông điệp là của lượt XANH (không bảo chạy lại mypy đã
    xanh). Một bộ đọc lấy bản ghi ĐẦU TIÊN sẽ in lệnh chạy lại sai."""
    _ghi(tmp_path, "cu", luc="2026-09-16T07:00:00+00:00")
    _ghi(tmp_path, "moi", luc="2026-09-16T08:00:00+00:00", ket_qua="PASS", sha="xanh1")
    ly_do = gate.l3_lai_bi_chan(tmp_path, "phien/x", bay_gio=MOT_GIO_SAU)
    assert "--tu xanh1" in ly_do and "check_mypy" not in ly_do


def test_ban_ghi_hong_hoac_thu_muc_khong_co_thi_CHO_QUA(tmp_path):
    """Một cổng từ chối vì chính nó hỏng là một cổng người ta sẽ tắt."""
    (tmp_path / "hong.json").write_text("{khong phai json", encoding="utf-8")
    assert gate.l3_lai_bi_chan(tmp_path, "phien/x", bay_gio=MOT_GIO_SAU) == ""
    assert gate.l3_lai_bi_chan(tmp_path / "khong_co", "phien/x") == ""


def test_co_l3_lai_ton_tai_tren_dong_lenh():
    r = subprocess.run([sys.executable, "tools/gate.py", "--help"], cwd=GOC,
                       capture_output=True, text=True, timeout=60)
    assert "--l3-lai" in r.stdout


# ── 3. Bản ghi phân biệt được `--doi` tự nâng với L3 gõ tay ────────────────

def test_ban_ghi_mang_ha_cap_tu_va_lenh_chay_lai(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    s = _buoc("mypy", [sys.executable, "tools/check_mypy.py"], ok=False)
    gate._ghi_ket_qua("day-du", [s], "FAIL (1/1)", 1.0, object(), False,
                      chay_lai=["python tools/check_mypy.py"], ha_cap_tu="doi",
                      ly_do_ha_cap="cham tep DUNG CHUNG", sha="abc123")
    tep = next((tmp_path / "test-results" / "gates").glob("*.json"))
    ban_ghi = json.loads(tep.read_text(encoding="utf-8"))
    assert ban_ghi["ha_cap_tu"] == "doi"
    assert ban_ghi["sha"] == "abc123", "sha phai la sha LUC BAT DAU cua luot"
    assert ban_ghi["lenh_chay_lai"] == ["python tools/check_mypy.py"]
    assert ban_ghi["l3_lai"] is False


# ── 3b. L1/L2 KHÔNG BAO GIỜ tự nâng lên L3 (chủ dự án chốt 24/09) ─────────
#
# 🔴 ĐỔI LUẬT 24/09. Bản 17/09 cho phép nâng cấp khi nhánh đã có L3 trong cửa sổ,
#    và TỪ CHỐI thẳng (return 2) khi chưa có. Cả hai đều sai theo luật mới:
#    từ chối thì người dùng không có gate nào chạy được; nâng cấp thì đó là một
#    L3 nằm giữa phiên. Nay: **hạ cấp xuống `nhanh`**, không bao giờ nâng.
#
# ⛔ Và L3 chỉ chạy ở KẾT THÚC PHIÊN — hết phiên làm việc, KHÔNG phải hết một
#    phase, một task hay một nhánh.

def test_khong_thu_hep_duoc_thi_HA_CAP_chu_khong_nang_cap():
    """Thông điệp phải nói rõ ba điều: đã hạ cấp, bộ test KHÔNG được phủ, và
    không tự nâng lên L3."""
    van = gate.canh_bao_khong_phu_bo_test("doi")
    assert "HA CAP" in van
    assert "KHONG tu nang len L3" in van
    assert "Bo test KHONG duoc phu" in van, "im lang ve cho khong nhin toi la te hon khong do"
    assert "thanh_phan.py --test" in van, "phai chi duong chay test nham"
    assert all(ord(c) < 128 for c in van), "dong in ra phai ASCII (cp1252)"


def test_diff_RONG_thi_TU_CHOI_chu_khong_ha_cap(monkeypatch):
    """🔴 HỒI QUY 24/09 (phiên ASV đo được): bản vá hạ cấp gộp BA ca `return None`
    làm một, trong đó hai ca **không phải** vấn đề phạm vi:

        `KhongBiet` — không đọc được cây (ví dụ `--tu <sha bịa>`)
        `not duong` — diff RỖNG so với mốc

    Cả hai nghĩa là **"ta chưa đo gì cả"**. Hạ cấp chúng xuống `nhanh` là biến một
    câu *"tôi không biết"* thành một chữ *"ĐẠT"*.

    ⛔ Và đó là đường MẶC ĐỊNH: hợp đồng viết "commit hết → gate", mà commit hết
       thì cây SẠCH, mà `--doi` không `--tu` thì trần diff với HEAD ⇒ **luôn rỗng**.
    """
    import argparse
    monkeypatch.setattr(gate, "loi_cho_bo_test", lambda **_: 4)
    import thanh_phan as tp_mod
    monkeypatch.setattr(tp_mod, "duong_da_doi", lambda *a, **k: [])
    ra, ghi_chu = gate._thu_hep(gate._steps(False),
                                argparse.Namespace(pham_vi=[], tu=""), "doi")
    assert ra is None
    assert gate.CHUA_DO_DUOC in ghi_chu, (
        "diff rong phai duoc DANH DAU la 'chua do duoc', khong lan voi 'pham vi rong'")


def test_khong_doc_duoc_cay_CUNG_la_chua_do_duoc(monkeypatch):
    """`--tu <sha bịa>` — ca tôi vấp thật 24/09."""
    import argparse
    monkeypatch.setattr(gate, "loi_cho_bo_test", lambda **_: 4)
    import thanh_phan as tp_mod

    def _no(*a, **k):
        raise tp_mod.KhongBiet("git tra 128")
    monkeypatch.setattr(tp_mod, "duong_da_doi", _no)
    ra, ghi_chu = gate._thu_hep(gate._steps(False),
                                argparse.Namespace(pham_vi=[], tu="xxx"), "doi")
    assert ra is None and gate.CHUA_DO_DUOC in ghi_chu


def test_HAI_thong_diep_noi_HAI_dieu_khac_nhau():
    """🔑 Vế đối chứng: nếu hai ca dùng chung một câu thì việc tách là vô nghĩa."""
    tu_choi = gate.tu_choi_vi_chua_do_duoc("doi", "x")
    ha_cap = gate.canh_bao_khong_phu_bo_test("doi")
    assert "TU CHOI" in tu_choi and "MOC SO SANH sai" in tu_choi
    assert "--tu" in tu_choi, "phai chi duong ra: truyen moc that"
    assert "HA CAP" in ha_cap and "TU CHOI" not in ha_cap
    for v in (tu_choi, ha_cap):
        assert all(ord(c) < 128 for c in v), "dong in ra phai ASCII (cp1252)"


def test_nhanh_CHUA_DO_DUOC_phai_dung_TRUOC_nhanh_ha_cap():
    """Thứ tự quyết định kết quả: đặt sau thì ca 'chưa đo được' rơi vào hạ cấp."""
    ma = (GOC / "tools" / "gate.py").read_text(encoding="utf-8")
    i_tu_choi = ma.index("if steps is None and CHUA_DO_DUOC in ghi_chu_pham_vi:")
    i_ha_cap = ma.index('ho_so = "nhanh"')
    assert i_tu_choi < i_ha_cap


def test_ma_KHONG_con_duong_nao_nang_len_day_du_tu_luot_hep():
    """🔑 Bánh cóc: chặn đường quay lại. Một bản vá vô tình dựng lại nhánh nâng
    cấp sẽ làm bài này đỏ."""
    ma = (GOC / "tools" / "gate.py").read_text(encoding="utf-8")
    i_hep = ma.index("steps, ghi_chu_pham_vi = _thu_hep(")
    khoi = ma[i_hep:i_hep + 2000]
    assert 'ho_so = "day-du"' not in khoi, (
        "luot hep KHONG duoc nang len day du - do la L3 giua phien")
    assert 'ho_so = "nhanh"' in khoi, "phai ha cap xuong `nhanh`"
    assert "nang_cap_giua_phien_bi_chan" not in ma, (
        "ham chan cu da bi thay bang `canh_bao_khong_phu_bo_test`")


# ── 4. Một nguồn luật ──────────────────────────────────────────────────────

def test_hop_dong_giu_nhip_mot_L3():
    van = HOP_DONG.read_text(encoding="utf-8")
    khoi = van[van.index("# 4. "):van.index("# 5. ")]
    for dau in ("MỘT lần", "test nhắm", "--doi --tu", "KHÔNG chạy L3 lần hai"):
        assert dau.lower() in khoi.lower(), f"hop dong §4 mat `{dau}`"


@pytest.mark.parametrize("tep", ["CLAUDE.md", "AGENTS.md",
                                 "docs/DEVELOPMENT_WORKFLOW.md",
                                 "docs/16_CAP_NHAT_VA_DEPLOY.md"])
def test_khong_tep_nao_con_goi_gate_doi_la_vong_lap(tep):
    """Luật 08/09 *"vòng lặp là `gate --doi`"* bị chép ở bốn tệp; đo 16/09 nó
    được dùng đúng MỘT lần trong 133 lượt. Còn một bản chép là còn một luật
    cạnh tranh với hợp đồng."""
    van = (GOC / tep).read_text(encoding="utf-8")
    assert "Mặc định của vòng lặp là `python tools\\gate.py --doi`" not in van
    assert "sửa  →  gate --doi  →  sửa" not in van
    assert "python tools/gate.py --doi             # mốc xuất phát" not in van


# ── 5. ho_so_cay: trunk thật, kế hoạch chứng nhận một L3 ───────────────────

def test_trunk_mac_dinh_la_nhanh_CON_TON_TAI(monkeypatch):
    """Trước 16/09 mặc định `admin-mvp-v3` đã bị xoá ⇒ mọi cây báo "khop trunk"."""
    assert hsc.TRUNK == "main" or "LTT_TRUNK" in __import__("os").environ
    monkeypatch.setattr(hsc, "TRUNK", "nhanh-khong-ton-tai-1280")
    assert hsc.trunk_ton_tai() is False
    monkeypatch.setattr(hsc, "TRUNK", "HEAD")
    assert hsc.trunk_ton_tai() is True


def test_ke_hoach_CERTIFYING_khong_chay_gate_truoc_L3():
    ma = (GOC / "tools" / "ho_so_cay.py").read_text(encoding="utf-8")
    khoi = ma[ma.index("KE HOACH CHUNG NHAN"):ma.index("def main(")]
    dong_in = [d for d in khoi.splitlines() if "print(" in d]
    assert not any("gate.py --quick" in d for d in dong_in)
    assert sum("python tools/gate.py\")" in d for d in dong_in) == 1, (
        "ke hoach phai co DUNG MOT luot L3")
