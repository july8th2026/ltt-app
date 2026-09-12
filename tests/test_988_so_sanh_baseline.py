"""test_988 — phép so BASELINE vs CANDIDATE phải bắt được hồi quy, và phải
từ chối so hai thứ không so được.

Dải **980–989** của chương trình MASTER UPGRADE (`docs/LLM_UPGRADE_MASTER_PLAN.md`).

═══════════════════════════════════════════════════════════════════════════
 KHOẢNG TRỐNG W3: CÓ PHÉP ĐO, KHÔNG CÓ HỢP ĐỒNG BASELINE
═══════════════════════════════════════════════════════════════════════════

`tools/bench_llm_hieu_nang.py` **đã** rất tốt: chụp `nvidia-smi` + `/health`
quanh mỗi lượt, dùng **trung vị** thay vì trung bình, tách nguội khỏi ấm, và
docstring của nó cấm chọn lượt đẹp.

Nhưng nó sinh ra một **kết quả**, không sinh ra một **baseline**. Nên câu *"bản
này có chậm hơn bản trước không"* chỉ trả lời được bằng cách mở hai tệp JSON ra
đọc bằng mắt — đúng chỗ người ta vô tình chọn lượt đẹp, tức đúng thứ chính công
cụ ấy cấm.

⇒ `tools/so_sanh_bench_llm.py` là phần còn thiếu, và tệp này chốt ba tính chất
  mà một phép so **sai** vẫn có thể trông đúng nếu không ai kiểm.
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "so_sanh_bench_llm", GOC / "tools" / "so_sanh_bench_llm.py")
SS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(SS)


def _luot(loai: str, ttfb: float, tong: float, decode: float, n: int = 3) -> list:
    return [{"loai": loai, "ttfb_s": ttfb, "tong_s": tong,
             "decode_tok_s": decode} for _ in range(n)]


def _bo(ttfb=1.0, tong=10.0, decode=60.0, model="qwen38-api", tien_trinh=3) -> dict:
    return {
        "model": model,
        "luot": (_luot("nguoi", ttfb, tong, decode)
                 + _luot("am_ngan", ttfb, tong, decode)),
        "ngu_canh_sau": {"smi": {"vram_mb": 21_979}, "tien_trinh_gpu": tien_trinh},
    }


# ── Bắt được hồi quy ───────────────────────────────────────────────────────

def test_khong_doi_thi_PASS():
    _, hoi_quy = SS.so(_bo(), _bo())
    assert hoi_quy is False


def test_TTFT_tang_20_phan_tram_la_hoi_quy():
    _, hoi_quy = SS.so(_bo(ttfb=1.0), _bo(ttfb=1.20))
    assert hoi_quy is True


def test_TTFT_tang_10_phan_tram_CHUA_la_hoi_quy():
    """Ngưỡng §22 là 15 %. Dưới ngưỡng thì im — nếu không, mọi lượt đo đều đỏ
    vì nhiễu, và người ta sẽ tắt phép so."""
    _, hoi_quy = SS.so(_bo(ttfb=1.0), _bo(ttfb=1.10))
    assert hoi_quy is False


def test_decode_GIAM_la_hoi_quy_con_TANG_thi_khong():
    """⛔ Chiều của từng chỉ số khác nhau, và nhầm chiều là lỗi tệ nhất:

    một phép so nhầm chiều sẽ **ăn mừng** đúng lúc hệ đang chậm đi.
    """
    _, xau = SS.so(_bo(decode=60.0), _bo(decode=50.0))     # cham hon 17 %
    assert xau is True
    _, tot = SS.so(_bo(decode=60.0), _bo(decode=75.0))     # nhanh hon
    assert tot is False


def test_ttft_giam_KHONG_bi_coi_la_hoi_quy():
    _, hoi_quy = SS.so(_bo(ttfb=2.0), _bo(ttfb=1.0))
    assert hoi_quy is False


# ── Từ chối so những thứ không so được ─────────────────────────────────────

def test_khac_model_thi_TU_CHOI_so():
    """⛔ §22: apple-to-apple. So `qwen38-api` với `qwen38-vision` rồi gọi chênh
    lệch là "hồi quy" là đo hai thứ khác nhau."""
    assert SS.kiem_cung_cau_hinh(_bo(model="qwen38-api"),
                                 _bo(model="qwen38-vision"))


def test_cung_model_thi_khong_chan():
    assert SS.kiem_cung_cau_hinh(_bo(), _bo()) == []


def test_canh_bao_khi_may_dang_ban_khac_han():
    """Máy B là **một máy để bàn đang dùng**: đo 31/08 có 23 tiến trình trên card.

    Một con số tok/s đo lúc ai đó đang cuộn trình duyệt không so được với con số
    đo lúc máy rảnh. Không chặn — nhưng phải nói ra, vì nếu không thì chênh lệch
    do hàng xóm sẽ bị đọc thành hồi quy của ta.
    """
    assert SS.canh_bao_nhieu(_bo(tien_trinh=3), _bo(tien_trinh=23))
    assert SS.canh_bao_nhieu(_bo(tien_trinh=3), _bo(tien_trinh=4)) == []


# ── Baseline rỗng: cái bẫy nguy hiểm nhất ──────────────────────────────────

def test_baseline_RONG_khong_duoc_doc_thanh_KHONG_HOI_QUY():
    """🔴 Đây là bất biến quan trọng nhất của cả tệp.

    Một baseline rỗng cho ra **0 dòng so sánh**, và `hoi_quy = False`. Nếu công
    cụ in "PASS" ở đó thì nó đang biến *"tôi không biết gì"* thành *"mọi thứ
    ổn"* — kết luận nguy hiểm nhất có thể rút ra từ việc không biết.

    Bộ nhớ dự án gọi đúng tên: *"không đối chứng thì số 0 không phải phát hiện"*.
    """
    rong = {"model": "qwen38-api", "luot": []}
    assert SS.gom(rong) == {}
    dong, hoi_quy = SS.so(rong, _bo())
    assert dong == [] and hoi_quy is False, "tien de cua phep kiem nay da doi"

    # Va `main()` phai TU CHOI, khong duoc in PASS.
    import io
    import json
    import sys
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        a, b = pathlib.Path(t) / "nen.json", pathlib.Path(t) / "moi.json"
        a.write_text(json.dumps(rong), encoding="utf-8")
        b.write_text(json.dumps(_bo()), encoding="utf-8")
        cu_argv, cu_out = sys.argv, sys.stdout
        sys.argv = ["x", "--nen", str(a), "--moi", str(b)]
        sys.stdout = io.StringIO()
        try:
            ma = SS.main()
            ra = sys.stdout.getvalue()
        finally:
            sys.argv, sys.stdout = cu_argv, cu_out
    assert ma == 2, "baseline rong ma tra 0 (PASS) — do la xanh-rong"
    assert "PASS" not in ra


def test_khong_co_loai_luot_chung_thi_cung_TU_CHOI():
    """Hai lượt đo không có loại nào trùng nhau cũng là 0 dòng so sánh."""
    chi_nguoi = {"model": "qwen38-api", "luot": _luot("nguoi", 1, 10, 60)}
    chi_dai = {"model": "qwen38-api", "luot": _luot("am_dai", 1, 10, 60)}
    dong, _ = SS.so(chi_nguoi, chi_dai)
    assert dong == []


# ── Ngưỡng phải khớp §22 ───────────────────────────────────────────────────

@pytest.mark.parametrize("chi_so,chieu,nguong", [
    ("ttft_s", "tang", 0.15),
    ("decode_tok_s", "giam", 0.10),
    ("tong_s", "tang", 0.15),
])
def test_nguong_khop_dieu_22(chi_so, chieu, nguong):
    assert SS.NGUONG[chi_so] == (chieu, nguong)


def test_gom_dung_TRUNG_VI_khong_phai_trung_binh():
    """⛔ `bench_llm_hieu_nang.py` chọn trung vị có lý do: một lượt nhanh bất
    thường thường là cache, một lượt chậm bất thường thường là hàng xóm. Phép so
    mà đổi sang trung bình sẽ **thừa hưởng đúng hai thứ nhiễu ấy**.
    """
    d = {"model": "m", "luot": [
        {"loai": "nguoi", "ttfb_s": 1.0, "tong_s": 1.0, "decode_tok_s": 1.0},
        {"loai": "nguoi", "ttfb_s": 2.0, "tong_s": 2.0, "decode_tok_s": 2.0},
        {"loai": "nguoi", "ttfb_s": 99.0, "tong_s": 99.0, "decode_tok_s": 99.0},
    ]}
    assert SS.gom(d)["nguoi"]["ttft_s"] == 2.0, "dang dung trung binh"


def test_luot_LOI_bi_bo_khong_lam_hong_trung_vi():
    d = {"model": "m", "luot": _luot("nguoi", 1, 10, 60) + [
        {"loai": "nguoi", "loi": "timeout"}]}
    assert SS.gom(d)["nguoi"]["n"] == 3
