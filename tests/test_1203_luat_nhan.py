"""multijob Task 4 — `luat_nhan.xet()`: hàm thuần quyết định nhận một lượt vào model nhà.

Mỗi luật một ca. Hàm thuần nên không cần CSDL, không đồng hồ, không mạng.
Spec §5: `docs/superpowers/specs/2026-09-11-ltt-llm-multijob-design.md`.
"""
from __future__ import annotations

import pytest

from platform_core.llm import luat_nhan as L


def _ts(**kw) -> "L.ThamSo":
    """`luat_nhan.ThamSo` với số THỜI GIAN của phép kiểm (lớp ấy không còn mặc định số)."""
    kw.setdefault("pool", 0)
    kw.setdefault("cho_whale_toi_da_s", 30.0)
    kw.setdefault("lao_hoa_s", 300.0)
    kw.setdefault("cho_backfill_toi_da_s", 120.0)
    return L.ThamSo(**kw)


POOL = 204_800
TS4 = _ts(so_slot=4, pool=POOL)


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
    ts = _ts(so_slot=4, pool=0)
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
    ts = _ts(so_slot=4, pool=POOL, chua_slot_tuong_tac=1)
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
    ts1 = _ts(so_slot=1, pool=POOL)
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

# ── 6. BACKFILL có chặn — L-12b, chủ dự án chốt 17/09/2026 ─────────────────
#
# Luật: Σ token đặt chỗ của lượt ĐANG CHẠY + lượt xin ≤ pool KV (`-kvu`: một bể
# `-c` chung cho mọi slot). Lượt chưa vừa thì CHỜ; lượt sau vừa pool thì được vào
# trước (backfill) — nhưng chỉ trong `cho_backfill_toi_da_s`; quá thì lượt lớn
# chặn mọi lượt trẻ hơn tới khi pool rút đủ (chống bỏ đói).

POOL_38 = 221_184                      # `apps/ltt_llm/ngan_sach.py` — 3.8, `-c`
TS38 = _ts(so_slot=3, pool=POOL_38)


def test_VI_DU_CHU_DU_AN_110K_cho_55K_backfill_roi_110K_chay():
    """Ví dụ nguyên văn của chủ dự án (17/09).

    job1 15K + job2 100K đang chạy; job3 110K ⇒ 225K > pool ⇒ CHỜ (không 429).
    job4 55K tới sau ⇒ 170K ≤ pool ⇒ được phục vụ TRƯỚC job3. Nhả ngân sách ⇒ job3 chạy.
    """
    job1, job2 = luot("j1", user="a", tok=15_000), luot("j2", user="b", tok=100_000)
    job3 = luot("j3", user="c", tok=110_000, tuoi=20)
    job4 = luot("j4", user="d", tok=55_000, tuoi=1)
    giu, cho = [job1, job2], [job3, job4]

    assert L.xet(job3, giu, cho, TS38) == L.PhanXu(False, L.CHO_NGAN_SACH)
    assert L.xet(job4, giu, cho, TS38).nhan, "backfill: 55K vua pool phai vao truoc 110K"

    # job4 chạy; job2 xong ⇒ 15K + 55K + 110K = 180K ≤ pool ⇒ job3 được nhận.
    giu2 = [job1, luot("j4", user="d", tok=55_000)]
    assert L.xet(luot("j3", user="c", tok=110_000, tuoi=200), giu2, [job3], TS38).nhan


def test_DOI_CHUNG_luot_sau_KHONG_vua_pool_thi_khong_backfill():
    """Đối chứng cho ca trên: backfill chỉ dành cho lượt VỪA, không phải "ai sau cũng vào"."""
    giu = [luot("j1", user="a", tok=15_000), luot("j2", user="b", tok=100_000)]
    job3 = luot("j3", user="c", tok=110_000, tuoi=20)
    job4 = luot("j4", user="d", tok=110_000, tuoi=1)
    assert L.xet(job4, giu, [job3, job4], TS38) == L.PhanXu(False, L.CHO_NGAN_SACH)


def test_CHONG_BO_DOI_qua_cua_so_backfill_luot_lon_chan_luot_tre_hon():
    """Cận trên có số: chờ quá `cho_backfill_toi_da_s` thì không ai trẻ hơn chen nữa.

    Sau đó lượt lớn chờ tối đa bằng thời gian các lượt ĐANG CHẠY nhả đủ pool.
    """
    giu = [luot("j1", user="a", tok=15_000), luot("j2", user="b", tok=100_000)]
    job3 = luot("j3", user="c", tok=110_000, tuoi=121)
    job4 = luot("j4", user="d", tok=55_000, tuoi=1)
    assert L.xet(job4, giu, [job3, job4], TS38) == L.PhanXu(False, L.NHUONG_LUOT_LON)


def test_chong_bo_doi_chan_ca_nguoi_xep_TRUOC_theo_so_giu():
    """`sap_xep_cho` đặt người giữ ít suất hơn lên trước tuổi chờ. Luật 6a phải chặn
    theo TUỔI, không theo thứ tự xếp — nếu không, khách mới của tài khoản rảnh
    chen mãi qua lượt lớn của tài khoản đang giữ một suất."""
    giu = [luot("j1", user="c", tok=15_000), luot("j2", user="b", tok=100_000)]
    job3 = luot("j3", user="c", tok=110_000, tuoi=121)      # user c đang giữ j1
    job4 = luot("j4", user="d", tok=5_000, tuoi=1)
    assert L.xet(job4, giu, [job3, job4], TS38) == L.PhanXu(False, L.NHUONG_LUOT_LON)


def test_hai_luot_lon_qua_cua_so_KHONG_chan_lan_nhau():
    """Deadlock nếu luật 6a đối xứng: người chờ lâu nhất không bị ai chặn."""
    giu = [luot("g", user="x", tok=100_000)]
    a = luot("a", user="a", tok=150_000, tuoi=500)
    b = luot("b", user="b", tok=150_000, tuoi=300)
    cho = [a, b]
    # `a` bị ngân sách giữ lại (đúng), không bị `b` chặn.
    assert L.xet(a, giu, cho, TS38) == L.PhanXu(False, L.CHO_NGAN_SACH)
    # Pool rút ⇒ `a` vào; `b` (trẻ hơn) không được chen trước `a`.
    assert L.xet(a, [], cho, TS38).nhan
    assert L.xet(b, [], cho, TS38) == L.PhanXu(False, L.XEP_SAU)


def test_job_nen_qua_cua_so_khong_chan_khach_tuong_tac():
    giu = [luot("g", user="x", tok=100_000)]
    nen = luot("n", user="job", lop=L.NEN, tok=150_000, tuoi=500)
    khach = luot("k", user="k", tok=5_000, tuoi=1)
    assert L.xet(khach, giu, [nen, khach], TS38).nhan


def test_whale_ket_sau_whale_dang_chay_KHONG_chan_luot_nho():
    """🔴 L-12b: trước 17/09 whale thứ hai chờ >30 s ⇒ `WHALE_CHAN` mọi lượt khác
    SUỐT lượt whale đang chạy (~4,5 phút cho 150K) — mà chặn không làm whale kia
    xong sớm hơn. Ca này ĐỎ trên luật cũ."""
    giu = [luot("w1", user="a", tok=150_000, whale=True)]
    w2 = luot("w2", user="b", tok=30_000, whale=True, tuoi=200)
    nho = luot("nho", user="c", tok=5_000, tuoi=1)
    assert L.xet(w2, giu, [w2, nho], TS38) == L.PhanXu(False, L.WHALE_NHUONG)
    assert L.xet(nho, giu, [w2, nho], TS38).nhan


def test_whale_ket_sau_whale_CHAN_lai_khi_whale_kia_xong():
    """Đối chứng chống bỏ đói whale: whale đang chạy xong ⇒ whale đã chờ lâu lại chặn."""
    w2 = luot("w2", user="b", tok=150_000, whale=True, tuoi=200)
    nho = luot("nho", user="c", tok=5_000, tuoi=1)
    giu = [luot("t", user="a", tok=100_000)]              # w2 chưa vừa pool
    assert L.xet(nho, giu, [w2, nho], TS38) == L.PhanXu(False, L.WHALE_CHAN)


def test_whale_moi_VAN_nhuong_whale_dang_chay_cong_bang_prefill():
    """Luật ≤1 whale là luật CÔNG BẰNG PREFILL, không phải luật ngân sách: một
    prompt 55K MỚI (không cache) vẫn chờ whale đang chạy dù vừa pool. Phiên dài
    gửi lượt tiếp (tiền tố đã cache, `uoc_moi`) KHÔNG là whale nên vẫn backfill."""
    giu = [luot("j2", user="b", tok=100_000, whale=True)]
    assert L.xet(luot("j4", user="d", tok=55_000, whale=True, tuoi=40), giu, [], TS38)         == L.PhanXu(False, L.WHALE_NHUONG)
    assert L.xet(luot("j4", user="d", tok=55_000, tuoi=1), giu, [], TS38).nhan


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
    sai = _ts(so_slot=4, pool=0)                 # "quên" pool
    assert L.xet(yc, giu, [], sai).nhan, "doi chung khong doi ket qua => phep kiem vo dung"


@pytest.mark.parametrize("n", [1, 2, 4, 8])
def test_tran_tai_khoan_va_tran_nen_hop_ly_moi_n(n):
    assert 1 <= L.tran_tai_khoan(n) <= n
    assert 1 <= L.tran_nen(n) <= n
    #: mặc định KHÔNG chừa suất nào ⇒ nền chạm trần slot.
    assert L.tran_nen(n) == n
    #: chừa 1 ⇒ hành vi cũ, và sàn `max(1, …)` giữ cho N = 1 vẫn chạy được nền.
    assert L.tran_nen(n, 1) == max(1, n - 1)


# ── Tính chất trên MÔ PHỎNG hàng đợi (L-12b) ────────────────────────────────

def _chay(ts, den, so_giay):
    """Mô phỏng theo giây. `den`: danh sách `(giây tới, id, token, thời lượng)`.

    Mỗi giây mọi người chờ hỏi `xet` theo thứ tự tới (như nhịp 0,5 s của
    `phong_cho`); lượt xong được nhả đúng một lần. Trả `(vi_pham, giây_nhận)`.
    """
    giu: list[tuple[L.Luot, int]] = []
    cho: list[tuple[str, str, int, int, int]] = []
    nhan: dict[str, int] = {}
    vi_pham = []
    den = sorted(den)
    for t in range(so_giay):
        giu = [(g, het) for g, het in giu if het > t]
        while den and den[0][0] <= t:
            toi, rid, tok, dai = den.pop(0)
            cho.append((rid, f"u-{rid}", tok, dai, toi))
        for rid, _uid, _tok, dai, _toi in list(cho):
            ds = [L.Luot(id=c[0], user_id=c[1], token_dat_truoc=c[2], tuoi_s=float(t - c[4]))
                  for c in cho]
            ban = next(x for x in ds if x.id == rid)
            if L.xet(ban, [g for g, _ in giu], ds, ts).nhan:
                giu.append((ban, t + dai))
                cho = [c for c in cho if c[0] != rid]
                nhan[rid] = t
                if (sum(g.token_dat_truoc for g, _ in giu) > ts.pool
                        or len(giu) > ts.so_slot):
                    vi_pham.append((t, [g.token_dat_truoc for g, _ in giu]))
    return vi_pham, nhan


@pytest.mark.parametrize("seed", [1, 7, 42])
def test_KHONG_BAO_GIO_nhan_vuot_pool_hay_vuot_so_suat(seed):
    """Bất biến an toàn: `-kvu` tràn pool thì llama.cpp huỷ MỌI slot đang chạy.
    Tải gần bão hoà, đa số lượt nhỏ, 8 % lượt 100–185K."""
    import random

    rng = random.Random(seed)
    den = []
    for i in range(160):
        lon = rng.random() < 0.08
        den.append((rng.randint(0, 3_000), f"r{i:04d}",
                    rng.randint(100_000, 185_000) if lon else rng.randint(2_000, 40_000),
                    rng.randint(5, 120)))
    vi_pham, nhan = _chay(TS38, den, 4_000)
    assert not vi_pham, f"nhan vuot pool/so suat: {vi_pham[:3]}"
    assert len(nhan) > 100, "mo phong khong phuc vu duoc ai => phep kiem vo dung"


def _dong_nho_lien_tuc():
    """Hai lượt 60K đang chạy lúc 0; lượt LỚN 185K tới ở giây 1; từ giây 2 cứ 20 s
    một lượt 50K chạy 100 s. Luôn có ≥1 lượt nhỏ chạy ⇒ 185K + 50K > pool: nếu
    backfill không có chặn, lượt lớn KHÔNG BAO GIỜ vừa."""
    den = [(0, "a", 60_000, 100), (0, "b", 60_000, 150), (1, "LON", 185_000, 60)]
    den += [(2 + 20 * k, f"n{k:03d}", 50_000, 100) for k in range(80)]
    return den


def test_CHONG_BO_DOI_luot_lon_duoc_nhan_trong_can_tren():
    """Cận trên: cửa sổ backfill (120 s) + lượt nhỏ dài nhất đang chạy (100 s)."""
    _, nhan = _chay(TS38, _dong_nho_lien_tuc(), 1_700)
    assert "LON" in nhan, "luot lon bi bo doi"
    assert nhan["LON"] - 1 <= 120 + 100 + 2, nhan["LON"]
    assert sum(1 for k in nhan if k.startswith("n")) >= 3, "khong backfill luot nao"


def test_DOI_CHUNG_bo_chan_backfill_thi_luot_lon_bi_bo_doi():
    """Cùng dòng khách, cửa sổ backfill vô hạn ⇒ lượt lớn chết đói. Ca này là lý do
    ca trên chứng minh được gì (memory "số 0 cần đối chứng")."""
    from dataclasses import replace

    _, nhan = _chay(replace(TS38, cho_backfill_toi_da_s=10**9), _dong_nho_lien_tuc(), 1_700)
    assert "LON" not in nhan
