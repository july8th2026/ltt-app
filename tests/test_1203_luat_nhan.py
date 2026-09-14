"""multijob Task 4 — `luat_nhan.xet()`: hàm thuần quyết định nhận một lượt vào model nhà.

Mỗi luật một ca. Hàm thuần nên không cần CSDL, không đồng hồ, không mạng.
Spec §5: `docs/superpowers/specs/2026-09-11-ltt-llm-multijob-design.md`.
"""
from __future__ import annotations

import pytest

from platform_core.llm import luat_nhan as L

POOL = 204_800
TS4 = L.ThamSo(so_slot=4, pool=POOL, cho_whale_toi_da_s=30.0, lao_hoa_s=300.0)


def luot(id_, user="u", lop=L.TUONG_TAC, tok=10_000, whale=False, tuoi=0.0):
    return L.Luot(id=id_, user_id=user, lop=lop, token_dat_truoc=tok,
                  la_whale=whale, tuoi_s=tuoi)


# ── 1. slot ──────────────────────────────────────────────────────────────────

def test_het_slot_thi_cho_slot():
    giu = [luot(f"g{i}", user=f"u{i}") for i in range(4)]
    assert L.xet(luot("y", user="moi"), giu, [], TS4) == L.PhanXu(False, L.CHO_SLOT)


def test_con_slot_va_ngan_sach_thi_nhan():
    assert L.xet(luot("y"), [luot("g", user="khac")], [], TS4).nhan


# ── 2. ngân sách KV ──────────────────────────────────────────────────────────

def test_vuot_pool_thi_cho_ngan_sach():
    """Phiên 170K đang chạy + lượt 60K = 230K > 204.800 ⇒ CHỜ (đúng ý D-02)."""
    giu = [luot("dai", user="a", tok=170_000)]
    px = L.xet(luot("y", user="b", tok=60_000), giu, [], TS4)
    assert px == L.PhanXu(False, L.CHO_NGAN_SACH)


def test_vua_khit_pool_thi_nhan():
    giu = [luot("dai", user="a", tok=POOL - 10_000)]
    assert L.xet(luot("y", user="b", tok=10_000), giu, [], TS4).nhan


def test_pool_0_la_hanh_vi_cu_chi_dem_slot():
    ts = L.ThamSo(so_slot=4, pool=0)
    giu = [luot("dai", user="a", tok=10**9)]
    assert L.xet(luot("y", user="b", tok=10**9), giu, [], ts).nhan


# ── 3. nền / nội bộ ──────────────────────────────────────────────────────────

def test_nen_dung_HET_slot_khi_khong_chua_suat_nao():
    """Chốt 14/09/2026: một lô job thuần phải lấp ĐẦY card, không dừng ở N−1.

    ⛔ Ca này thay ca cũ `test_nen_chi_duoc_toi_da_n_tru_1_slot`, và nó thay vì
       sửa vì hai ca ấy khẳng định hai điều NGƯỢC nhau — giữ cả hai là giữ một
       phép kiểm luôn đỏ. Hành vi cũ không mất: nó còn nguyên ở ca
       `test_chua_slot_tuong_tac_1_thi_nen_dung_o_n_tru_1` ngay dưới, nay là một
       LỰA CHỌN khai ra chứ không phải hằng số nằm chết trong hàm.

    Đo được trước khi sửa (job thơ 3.8, 14/09): ba job nộp cùng lúc trên card 3
    slot chỉ chạy hai; lượt thứ ba chờ 30,6 giây trong khi GPU còn một suất
    trống — 3090 tụt về 0 % đúng 1,5 giây ở nhịp bàn giao.
    """
    giu = [luot(f"n{i}", user=f"u{i}", lop=L.NEN) for i in range(3)]
    assert L.xet(luot("y", user="moi", lop=L.NEN), giu, [], TS4).nhan
    # ...và chỉ dừng khi HẾT slot thật.
    giu4 = giu + [luot("n3", user="u3", lop=L.NEN)]
    assert L.xet(luot("y", user="moi", lop=L.NEN), giu4, [], TS4) == L.PhanXu(
        False, L.CHO_SLOT)


def test_chua_slot_tuong_tac_1_thi_nen_dung_o_n_tru_1():
    """Đối chứng: cùng dữ liệu, chỉ đổi MỘT tham số, kết quả phải đảo.

    Thiếu ca này thì ca trên không chứng minh được gì — một `xet()` luôn trả
    `nhan=True` cho lớp NEN cũng làm nó xanh (memory "số 0 cần đối chứng").
    """
    ts = L.ThamSo(so_slot=4, pool=POOL, chua_slot_tuong_tac=1)
    giu = [luot(f"n{i}", user=f"u{i}", lop=L.NEN) for i in range(3)]
    assert L.xet(luot("y", user="moi", lop=L.NEN), giu, [], ts) == L.PhanXu(
        False, L.CHO_SLOT)
    # ...và TƯƠNG TÁC vẫn vào được suất chừa.
    assert L.xet(luot("y", user="moi"), giu, [], ts).nhan


def test_nen_nhuong_nguoi_tuong_tac_dang_cho():
    cho = [luot("c", user="khach")]
    px = L.xet(luot("y", user="job", lop=L.NEN), [], cho, TS4)
    assert px == L.PhanXu(False, L.NEN_NHUONG)


def test_n_bang_1_nen_van_chay_duoc_khi_ranh():
    """Ca biên phát hiện khi viết plan: N−1 = 0 sẽ bỏ đói MỌI job ở pha 1."""
    ts1 = L.ThamSo(so_slot=1, pool=POOL)
    assert L.xet(luot("y", lop=L.NEN), [], [], ts1).nhan
    assert L.xet(luot("y", lop=L.NOI_BO), [], [], ts1).nhan
    # ...và vẫn nhường người tương tác đang chờ.
    assert not L.xet(luot("y", user="job", lop=L.NEN), [],
                     [luot("c", user="khach")], ts1).nhan


# ── 4. trần tài khoản (work-conserving) ──────────────────────────────────────

def test_mot_tai_khoan_toi_da_nua_so_slot_khi_co_nguoi_khac_cho():
    giu = [luot("a1", user="A"), luot("a2", user="A")]
    cho = [luot("b", user="B", tuoi=1.0)]
    px = L.xet(luot("a3", user="A", tuoi=2.0), giu, cho + [luot("a3", user="A", tuoi=2.0)], TS4)
    assert px == L.PhanXu(False, L.TRAN_TAI_KHOAN)


def test_mot_minh_thi_dung_het_khong_bi_phat():
    giu = [luot("a1", user="A"), luot("a2", user="A")]
    assert L.xet(luot("a3", user="A"), giu, [], TS4).nhan


# ── 5. whale ─────────────────────────────────────────────────────────────────

def test_toi_da_mot_whale():
    giu = [luot("w1", user="a", whale=True)]
    px = L.xet(luot("w2", user="b", whale=True, tuoi=100), giu, [], TS4)
    assert px == L.PhanXu(False, L.WHALE_NHUONG)


def test_whale_nhuong_luot_tuong_tac_dang_chay_roi_moi_vao():
    giu = [luot("t", user="a")]
    assert L.xet(luot("w", user="b", whale=True, tuoi=5), giu, [], TS4) == L.PhanXu(
        False, L.WHALE_NHUONG)
    assert L.xet(luot("w", user="b", whale=True, tuoi=31), giu, [], TS4).nhan


def test_whale_cho_qua_han_thanh_chan():
    cho = [luot("w", user="b", whale=True, tuoi=31, tok=150_000)]
    giu = [luot("t", user="a", tok=100_000)]   # whale chưa vừa ngân sách
    px = L.xet(luot("y", user="c", tuoi=1), giu, cho, TS4)
    assert px == L.PhanXu(False, L.WHALE_CHAN)


def test_whale_con_tre_thi_nguoi_nho_duoc_vuot():
    cho = [luot("w", user="b", whale=True, tuoi=5)]
    assert L.xet(luot("y", user="c", tuoi=1), [luot("t", user="a")],
                 cho + [luot("y", user="c", tuoi=1)], TS4).nhan


# ── 6. FCFS chặt ─────────────────────────────────────────────────────────────

def test_nguoi_dung_truoc_chua_vua_thi_nguoi_sau_cho():
    """Chống bỏ đói phiên dài: lượt nhỏ không được chen mãi qua lượt lớn."""
    giu = [luot("g", user="x", tok=120_000)]
    lon = luot("lon", user="a", tok=100_000, tuoi=10)   # 220K > pool: chưa vừa
    nho = luot("nho", user="b", tok=5_000, tuoi=1)
    assert L.xet(nho, giu, [lon, nho], TS4) == L.PhanXu(False, L.XEP_SAU)


def test_nguoi_truoc_chi_vuong_tran_tai_khoan_thi_khong_chan():
    giu = [luot("a1", user="A"), luot("a2", user="A")]
    a3 = luot("a3", user="A", tuoi=10)
    b = luot("b", user="B", tuoi=1)
    assert L.xet(b, giu, [a3, b], TS4).nhan


def test_lao_hoa_day_nguoi_cho_lau_len_truoc():
    moi = luot("moi", user="A", tuoi=1)
    gia = luot("gia", user="B", tuoi=301)
    thu_tu = L.sap_xep_cho([moi, gia], [luot("g1", user="B")], TS4)
    assert [c.id for c in thu_tu] == ["gia", "moi"]


def test_tuong_tac_luon_xep_truoc_nen():
    thu_tu = L.sap_xep_cho([luot("n", lop=L.NEN, tuoi=999), luot("t", tuoi=1)], [], TS4)
    assert [c.id for c in thu_tu] == ["t", "n"]


# ── Đối chứng: phép kiểm phải ĐỎ trước một luật sai ─────────────────────────

def test_doi_chung_luat_quen_ngan_sach_se_bi_bat(monkeypatch):
    """Tiêm bản luật 'quên vế ngân sách' — ca ngân sách phải đổi kết quả.

    Một phép kiểm chưa từng đỏ trước một bản sai thì chưa chứng minh được gì
    (memory "số 0 cần đối chứng").
    """
    giu = [luot("dai", user="a", tok=170_000)]
    yc = luot("y", user="b", tok=60_000)
    assert not L.xet(yc, giu, [], TS4).nhan
    sai = L.ThamSo(so_slot=4, pool=0)            # "quên" pool
    assert L.xet(yc, giu, [], sai).nhan, "doi chung khong doi ket qua => phep kiem vo dung"


@pytest.mark.parametrize("n", [1, 2, 4, 8])
def test_tran_tai_khoan_va_tran_nen_hop_ly_moi_n(n):
    assert 1 <= L.tran_tai_khoan(n) <= n
    assert 1 <= L.tran_nen(n) <= n
    #: mặc định KHÔNG chừa suất nào ⇒ nền chạm trần slot.
    assert L.tran_nen(n) == n
    #: chừa 1 ⇒ hành vi cũ, và sàn `max(1, …)` giữ cho N = 1 vẫn chạy được nền.
    assert L.tran_nen(n, 1) == max(1, n - 1)
