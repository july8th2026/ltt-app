"""Bộ dò của cổng G2 (`bench.py::phan_tich_dau`) có dò đúng thứ nó tuyên bố không.

Cổng G2 (Task 3.2) là một phép kiểm **sự vắng mặt**: nó nói "0 lượt lẫn slot".
Một mệnh đề vắng mặt không tự chứng minh được — bộ dò hỏng cũng cho ra số 0.
Nên tệp này là **đối chứng cho chính bộ dò**, không phải cho engine.

Vì sao nó tồn tại (chuyện thật, 2026-09-12): bản đầu của bộ dò coi **mọi** chuỗi
bắt đầu bằng `DAU-` khác dấu của chính mình là "lẫn slot". Chạy 200 lượt thật thì
nó báo hai vụ, `DAT: false` — và cả hai đều **giả**:

    lượt DAU-1-040 → thấy "DAU-1-0"
    lượt DAU-2-047 → thấy "DAU-2"

Cả hai là **mảnh vỡ tiền tố của chính dấu nó** (model chèn định dạng vào giữa
chuỗi), và cả hai lượt đều đọc lại đúng dấu mình. Không có byte nào của slot khác.

⛔ Bài học đóng gói ở đây: thu hẹp một phép kiểm cho tới khi nó xanh thì dễ. Thu
   hẹp cho nó đo **đúng thứ nó tuyên bố** mới là việc phải làm — nên mảnh vỡ vẫn
   được trả về ở trường riêng chứ không bị vứt, và lượt lẫn slot THẬT vẫn phải đỏ.
"""
import importlib.util
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]
BENCH = GOC / "docs" / "ltt_llm_dual" / "artifacts" / "bench" / "bench.py"


@pytest.fixture(scope="module")
def bench():
    """Nạp `bench.py` theo đường dẫn: nó là tạo tác đo, không nằm trong gói nào.

    Nạp bằng đường dẫn chứ không `import` để phép kiểm chết ngay nếu ai đó dời
    tệp — một `ImportError` nói thật, còn một `skip` im lặng thì không.
    """
    assert BENCH.exists(), "khong thay bench.py: " + str(BENCH)
    spec = importlib.util.spec_from_file_location("bench_g2", BENCH)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ── Hai ca THẬT đã làm cổng đỏ oan, lấy nguyên văn từ g2_20260912.jsonl ──────

@pytest.mark.parametrize("text,dau,manh", [
    ("Chuoi la **DAU-1-0** 40 va DAU-1-040", "DAU-1-040", "DAU-1-0"),
    ("DAU-2 -047 roi DAU-2-047", "DAU-2-047", "DAU-2"),
])
def test_manh_vo_tien_to_KHONG_phai_lan_slot(bench, text, dau, manh):
    r = bench.phan_tich_dau(text, dau)
    assert r["dau_slot_khac"] == [], "manh vo bi tinh nham thanh lan slot"
    assert manh in r["manh_vo"], "manh vo bi vut di thay vi bao cao rieng"
    assert r["co_dau_minh"] is True
    assert r["rong"] is False


# ── Đối chứng: dấu THẬT của slot khác PHẢI đỏ ───────────────────────────────

def test_doi_chung_dau_that_cua_slot_khac_van_bi_bat(bench):
    """Không có ca này thì hai phép kiểm trên chỉ chứng minh bộ dò luôn trả rỗng."""
    r = bench.phan_tich_dau("DAU-3-012 xen vao day, con dau toi la DAU-1-040", "DAU-1-040")
    assert r["dau_slot_khac"] == ["DAU-3-012"]
    assert r["manh_vo"] == []


def test_doi_chung_dau_slot_khac_dinh_dau_cham_van_bi_bat(bench):
    """Dấu của slot khác nằm cuối câu (dính dấu chấm) vẫn phải bị bóc ra."""
    r = bench.phan_tich_dau("Ket qua: DAU-2-007.", "DAU-0-001")
    assert r["dau_slot_khac"] == ["DAU-2-007"]


# ── Ba điều kiện còn lại của cổng ───────────────────────────────────────────

def test_tra_loi_rong_bi_bat(bench):
    r = bench.phan_tich_dau("   ", "DAU-0-000")
    assert r["rong"] is True and r["co_dau_minh"] is False


def test_dien_dat_lai_khong_phai_loi_engine(bench):
    """Model diễn đạt lại thay vì đọc nguyên văn: ghi nhận, nhưng KHÔNG lẫn slot.

    `so_thieu_dau_minh` cố ý **không** làm trượt cổng — đó là hành vi model, còn
    cổng này hỏi về engine (#27572: trả lời rỗng, và lẫn nội dung giữa các slot).
    """
    r = bench.phan_tich_dau("Chuoi dinh danh ban dua la mot ma noi bo.", "DAU-1-002")
    assert r["co_dau_minh"] is False
    assert r["dau_slot_khac"] == [] and r["rong"] is False


def test_khuon_dau_khop_voi_thu_bo_do_tim(bench):
    """`KHUON_DAU` sinh ra dấu, `phan_tich_dau` nhận dạng dấu — hai vế phải khớp.

    Hai chỗ khai cùng một điều mà không ai bắt khớp thì chúng sẽ trôi khỏi nhau:
    đổi khuôn thành 4 chữ số là bộ dò lặng lẽ thôi nhận ra mọi dấu, và cổng
    xanh vĩnh viễn.
    """
    dau_khac = bench.KHUON_DAU % (3, 7)
    cua_toi = bench.KHUON_DAU % (1, 5)
    r = bench.phan_tich_dau("noi dung " + dau_khac, cua_toi)
    assert r["dau_slot_khac"] == [dau_khac]
