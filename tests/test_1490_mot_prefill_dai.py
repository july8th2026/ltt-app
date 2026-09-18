"""Task 17 (L-29) — "một prefill dài mỗi lúc" theo model, ở phía máy A.

Phát hiện C4 (DECISION_LOG L-28, `KET_QUA_C4_18_09.md` §5): một prompt NGẮN còn
đang prefill khi prompt 32K vào engine thì chờ HẾT prefill dài (~35 s) — llama.cpp
nhồi token prompt vào lô theo THỨ TỰ SLOT (`server-context.cpp` 91f6a6cf3
:3110-3115, :3524), không có chunked prefill công bằng. Lượt đã ở pha decode vẫn
nhích (lặng ≤ 0,8 s).

Luật (khi hồ sơ model bật `mot_prefill_dai`):
  * whale (token prefill MỚI ≥ `nguong_whale`) KHÔNG vào engine khi còn lượt nào
    trên cùng tài nguyên CHƯA xong prefill (`WHALE_CHO_PREFILL`) — lượt ngắn đang
    prefill được xong trước; cận trên có số nhờ `WHALE_CHAN` (≥ 30 s không nhận
    lượt mới) + hạn ước prefill.
  * lượt NGẮN vẫn vào ngay, kể cả khi một whale đang prefill.
  * "xong prefill" = byte dữ liệu đầu tiên (stream) HOẶC quá hạn ước
    `san + token_moi / toc_prefill` (cửa không stream, và lưới khi mất tín hiệu).
    ⇒ whale đang decode ở cửa đồng bộ/job không còn khoá whale kế suốt lượt.
  * FIFO giữa các whale: whale trẻ không vượt whale già đang KHÔNG bị chặn.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from platform_core.llm import luat_nhan as L


def _ts(**kw) -> "L.ThamSo":
    kw.setdefault("so_slot", 4)
    kw.setdefault("pool", 200_000)
    kw.setdefault("cho_whale_toi_da_s", 30.0)
    kw.setdefault("lao_hoa_s", 300.0)
    kw.setdefault("cho_backfill_toi_da_s", 120.0)
    kw.setdefault("mot_prefill_dai", True)
    return L.ThamSo(**kw)


def luot(id_, user=None, lop=L.TUONG_TAC, tok=10_000, whale=False, tuoi=0.0,
         prefill=False):
    return L.Luot(id=id_, user_id=user or id_, lop=lop, token_dat_truoc=tok,
                  la_whale=whale, tuoi_s=tuoi, dang_prefill=prefill)


# ── 1. Luật thuần ─────────────────────────────────────────────────────────────

def test_whale_cho_luot_ngan_dang_prefill_xong():
    """Ca C4: lượt ngắn đang prefill ⇒ whale (đã qua 30 s nhường) CHỜ nó xong."""
    giu = [luot("ngan", prefill=True)]
    px = L.xet(luot("w", whale=True, tuoi=99), giu, [], _ts())
    assert px == L.PhanXu(False, L.WHALE_CHO_PREFILL)


def test_doi_chung_tat_co_thi_hanh_vi_cu():
    giu = [luot("ngan", prefill=True)]
    assert L.xet(luot("w", whale=True, tuoi=99), giu, [],
                 _ts(mot_prefill_dai=False)).nhan


def test_luot_ngan_da_xong_prefill_thi_whale_vao():
    giu = [luot("ngan", prefill=False)]
    assert L.xet(luot("w", whale=True, tuoi=99), giu, [], _ts()).nhan


def test_luot_nen_dang_prefill_cung_chan_whale():
    """Job nền đang prefill cũng bị cá voi đè — luật không theo lớp."""
    giu = [luot("job", lop=L.NEN, prefill=True)]
    px = L.xet(luot("w", whale=True, tuoi=0), giu, [], _ts())
    assert px == L.PhanXu(False, L.WHALE_CHO_PREFILL)


def test_luot_ngan_van_vao_ngay_khi_whale_dang_prefill():
    """Giữ lượt ngắn ở A không giúp nó (không preempt được) ⇒ nhận ngay."""
    giu = [luot("w", whale=True, prefill=True)]
    assert L.xet(luot("ngan"), giu, [], _ts()).nhan


def test_hai_whale_khong_prefill_chong():
    giu = [luot("w1", whale=True, prefill=True)]
    px = L.xet(luot("w2", whale=True, tuoi=99), giu, [], _ts())
    assert px == L.PhanXu(False, L.WHALE_NHUONG)


def test_whale_da_xong_prefill_khong_con_khoa_whale_ke():
    """Cửa đồng bộ/job: cờ whale không xoá được bằng byte đầu; quá hạn ước prefill
    (`dang_prefill=False`) thì whale đang decode thôi khoá whale kế."""
    giu = [luot("w1", whale=True, prefill=False)]
    assert L.xet(luot("w2", whale=True, tuoi=99), giu, [], _ts()).nhan
    # đối chứng: tắt cờ ⇒ cờ whale giữ suốt lượt như cũ
    px = L.xet(luot("w2", whale=True, tuoi=99), giu, [], _ts(mot_prefill_dai=False))
    assert px == L.PhanXu(False, L.WHALE_NHUONG)


def test_whale_cho_qua_30s_chan_luot_moi_de_prefill_rut_can():
    """Chống đói whale: quá 30 s ⇒ lượt mới bị chặn (WHALE_CHAN), lượt đang prefill
    xong dần ⇒ whale vào. Không cần đồng hồ thứ hai."""
    w = luot("w", whale=True, tuoi=31)
    giu = [luot("ngan", prefill=True)]
    assert L.xet(luot("moi"), giu, [w], _ts()) == L.PhanXu(False, L.WHALE_CHAN)


def test_fifo_giua_whale_whale_tre_khong_vuot_whale_gia():
    gia = luot("w_gia", whale=True, tuoi=10)
    tre = luot("w_tre", whale=True, tuoi=5)
    giu = [luot("job", lop=L.NEN)]          # đang decode, không ai prefill
    px = L.xet(tre, giu, [gia, tre], _ts())
    assert px == L.PhanXu(False, L.XEP_SAU)
    assert L.xet(gia, giu, [gia, tre], _ts()).nhan
    # đối chứng: tắt cờ ⇒ hành vi cũ (whale < 30 s coi như đang nhường, bị vượt)
    assert L.xet(tre, giu, [gia, tre], _ts(mot_prefill_dai=False)).nhan


def test_fifo_whale_gia_dang_bi_chan_thi_whale_tre_cung_bi_chan():
    gia = luot("w_gia", whale=True, tuoi=10)
    tre = luot("w_tre", whale=True, tuoi=5)
    giu = [luot("ngan", prefill=True)]
    assert L.xet(tre, giu, [gia, tre], _ts()) == L.PhanXu(False, L.WHALE_CHO_PREFILL)


# ── 2. Hạn ước prefill (lưới khi không có byte đầu) ───────────────────────────

def test_han_prefill_ton_san_va_toc_do():
    from platform_core.llm import tham_so_da_luot as T

    assert T.han_prefill_s(0, 1000.0, 5.0) == 5.0
    assert T.han_prefill_s(32_000, 1000.0, 5.0) == pytest.approx(37.0)
    assert T.han_prefill_s(32_000, 0.0, 5.0) == float("inf")


def test_ho_so_bat_mac_dinh_va_toc_do_bao_thu():
    """Hồ sơ hai model bật luật; tốc độ ước ≤ điểm CHẬM nhất của đường cong đo
    (hạn ước dài hơn thật — sai về phía giữ whale lâu hơn, không về phía chồng)."""
    from apps.ltt_llm import ngan_sach as N

    for m, h in N.HO_SO.items():
        assert h.mot_prefill_dai is True, m
        cham = min(v for _, v in N.DUONG_PREFILL_TOK_S[m])
        assert 0 < h.toc_prefill_uoc_tok_s < cham, m


def test_ban_khai_admission_mang_tham_so_prefill():
    from apps.ltt_llm import manifest as M
    from apps.ltt_llm.ngan_sach import HO_SO

    am = M._khai_admission("qwen38-api", "tn_x")
    assert am.mot_prefill_dai is True
    assert am.toc_prefill_tok_s == HO_SO["qwen38-api"].toc_prefill_uoc_tok_s


# ── 3. Tích hợp: admission.xet_va_giu trên CSDL, đồng hồ giả ──────────────────

TN = "llm_t17"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'adm.db').as_posix()}")
    monkeypatch.setenv("LTT_LLM_SAN_HAN_PREFILL_S", "5")
    import platform_core.db as dbmod

    dbmod.reset_engine()
    import platform_core.models  # noqa: F401

    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core.llm import admission

    monkeypatch.setattr(admission, "_BAN_DO_PREFILL", {TN: 1000.0})
    gen = dbmod.get_session()
    session = next(gen)
    try:
        yield session
    finally:
        session.close()
        dbmod.reset_engine()


def _xet(db, holder, *, now, moi=1_000, whale=False, tuoi=0.0, mode="stream"):
    from platform_core.llm import admission

    lease, ly_do = admission.xet_va_giu(
        db, resource=TN, slots=4, user_id=holder, mode=mode, holder_id=holder,
        token_pool=200_000, lop=L.TUONG_TAC, token_dat_truoc=moi + 3_000,
        token_prefill_moi=moi, la_whale=whale, tuoi_cho_s=tuoi, now=now)
    db.commit()
    return lease, ly_do


def _t(s: float) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=s)


def test_tich_hop_byte_dau_cua_luot_ngan_mo_cua_cho_whale(db):
    from platform_core.llm import admission

    ngan, _ = _xet(db, "ngan", now=_t(0), moi=1_300)
    w, ly_do = _xet(db, "w", now=_t(1), moi=32_000, whale=True, tuoi=99)
    assert w is None and ly_do == L.WHALE_CHO_PREFILL
    assert admission.danh_dau_prefill_xong(ngan.id) is True      # byte đầu về
    assert admission.danh_dau_prefill_xong(ngan.id) is False     # idempotent
    w, ly_do = _xet(db, "w", now=_t(2), moi=32_000, whale=True, tuoi=99)
    assert w is not None, ly_do
    # lượt ngắn mới trong lúc whale prefill: vào ngay
    ngan2, ly_do = _xet(db, "ngan2", now=_t(3), moi=800)
    assert ngan2 is not None, ly_do


def test_tich_hop_mat_tin_hieu_thi_het_han_uoc_mo_cua(db):
    """Cửa đồng bộ: không có byte đầu — hạn ước 5 + 1.300/1.000 = 6,3 s."""
    _xet(db, "ngan", now=_t(0), moi=1_300, mode="sync")
    w, ly_do = _xet(db, "w", now=_t(5), moi=32_000, whale=True, tuoi=99)
    assert ly_do == L.WHALE_CHO_PREFILL
    w, ly_do = _xet(db, "w", now=_t(8), moi=32_000, whale=True, tuoi=99)
    assert w is not None, ly_do


def test_tich_hop_whale_dong_bo_dang_decode_khong_khoa_whale_ke(db):
    """Whale ở cửa đồng bộ: 32K/1.000 + 5 = 37 s. Trước hạn: whale kế chờ;
    sau hạn: vào (trước L-29 nó chờ HẾT lượt, kể cả phần decode)."""
    _xet(db, "w1", now=_t(0), moi=32_000, whale=True, tuoi=99, mode="sync")
    _w2, ly_do = _xet(db, "w2", now=_t(20), moi=20_000, whale=True, tuoi=99)
    assert ly_do == L.WHALE_NHUONG
    w2, ly_do = _xet(db, "w2", now=_t(40), moi=20_000, whale=True, tuoi=99)
    assert w2 is not None, ly_do


def test_tich_hop_tai_nguyen_khong_khai_thi_hanh_vi_cu(db, monkeypatch):
    from platform_core.llm import admission

    monkeypatch.setattr(admission, "_BAN_DO_PREFILL", {})
    _xet(db, "ngan", now=_t(0), moi=1_300)
    w, ly_do = _xet(db, "w", now=_t(1), moi=32_000, whale=True, tuoi=99)
    assert w is not None, ly_do


def test_tich_hop_dong_thoi_gian_C4_qua_A(db):
    """Dòng thời gian C4 đi qua A (B giả: byte đầu của lượt ngắn sau 4 s).

    t=0   whale xin (chờ vì có lượt tương tác đang chạy — luật 5 cũ)
    t=28  lượt ngắn A vào
    t=30  whale hết 30 s nhường — TRƯỚC L-29 vào ngay, đè lượt A đang prefill
    t=31  lượt ngắn B xin ⇒ WHALE_CHAN (để prefill rút cạn)
    t=32  B giả trả byte đầu cho A ⇒ whale vào
    t=33  lượt ngắn C xin trong lúc whale prefill ⇒ vào ngay
    """
    from platform_core.llm import admission, phong_cho

    ts0 = datetime.now(timezone.utc)

    def t(s):
        return ts0 + timedelta(seconds=s)

    yc_w = phong_cho.YeuCauCho(
        resource=TN, slots=4, token_pool=200_000, user_id="w", mode="stream",
        holder_id="w", request_id="w", cua="stream", lop=L.TUONG_TAC,
        token_dat_truoc=35_000, token_prefill_moi=32_000, la_whale=True)
    wid = phong_cho.vao(db, yc_w, now=t(0))
    db.commit()

    from platform_core.models import LlmWaiter

    def nhip(s):
        """Người chờ đập nhịp như `cho_nhan` (không thì mất nhịp, rời hàng)."""
        db.get(LlmWaiter, wid).heartbeat_at = t(s)
        db.commit()

    def xin_whale(s):
        nhip(s)
        lease, ly_do = admission.xet_va_giu(
            db, resource=TN, slots=4, user_id="w", mode="stream", holder_id="w",
            token_pool=200_000, lop=L.TUONG_TAC, token_dat_truoc=35_000,
            token_prefill_moi=32_000, la_whale=True, waiter_id=wid, tuoi_cho_s=s,
            now=t(s))
        if lease is not None:
            w = db.get(LlmWaiter, wid)
            w.trang_thai, w.lease_id = "nhan", lease.id
        db.commit()
        return lease, ly_do

    dang_chay, _ = _xet(db, "dang_chay", now=t(-10), moi=500)
    admission.danh_dau_prefill_xong(dang_chay.id)
    assert xin_whale(1)[1] == L.WHALE_NHUONG
    nhip(28)
    a, ly_do = _xet(db, "a", now=t(28), moi=1_300)
    assert a is not None, ly_do
    assert xin_whale(30.5)[1] == L.WHALE_CHO_PREFILL
    _b, ly_do = _xet(db, "b", now=t(31), moi=900, tuoi=0.0)
    assert ly_do == L.WHALE_CHAN
    admission.danh_dau_prefill_xong(a.id)
    lease_w, ly_do = xin_whale(32)
    assert lease_w is not None, ly_do
    c, ly_do = _xet(db, "c", now=t(33), moi=700)
    assert c is not None, ly_do


# ── 4. Tín hiệu byte đầu ở cửa stream: mọi lượt, không riêng whale ────────────

def test_phat_danh_dau_prefill_xong_cho_ca_luot_ngan(monkeypatch):
    from types import SimpleNamespace

    from platform_core.llm import admission
    from platform_core.runtime_noi_bo import luong

    danh_dau: list[str] = []
    monkeypatch.setattr(admission, "danh_dau_prefill_xong",
                        lambda lease_id: danh_dau.append(lease_id) or True)
    monkeypatch.setattr(admission, "keep_alive",
                        lambda *a, **k: __import__("contextlib").nullcontext())
    monkeypatch.setattr(luong, "quyet_toan", lambda *a, **k: None)
    cb = SimpleNamespace(la_whale=False, lease_id="L-ngan", request_id="r-12345678",
                         user_id="u", da_giu=0, model_alias="ltt-3.8", waiter_id=None)
    luot_ = SimpleNamespace(chuan_bi=cb, dem=SimpleNamespace(nhin=lambda k: None, token_ra=0),
                            luc_khoi_cuoi=0.0, ket_thuc=None, da_quyet_toan=False,
                            ket_qua=None)
    mo = SimpleNamespace(luong=iter([b": ping\n\n", b"data: x\n\n", b"data: y\n\n"]),
                         hong=lambda e: None, xong=lambda tokens: None)
    list(luong._phat(mo, luot_))
    assert danh_dau == ["L-ngan"]


def test_tich_hop_dong_thoi_gian_C4_doi_chung_tat_luat(db, monkeypatch):
    """Đối chứng của ca trên: tài nguyên không bật luật ⇒ whale vào ngay ở t=30,5
    dù lượt A còn prefill (đúng hành vi đã gây C4 §5)."""
    from platform_core.llm import admission

    monkeypatch.setattr(admission, "_BAN_DO_PREFILL", {})
    dang_chay, _ = _xet(db, "dang_chay", now=_t(-10), moi=500)
    admission.danh_dau_prefill_xong(dang_chay.id)
    a, _ = _xet(db, "a", now=_t(28), moi=1_300)
    assert a is not None
    w, ly_do = _xet(db, "w", now=_t(30.5), moi=32_000, whale=True, tuoi=30.5)
    assert w is not None, ly_do


# ── 5. B giả mô phỏng llama.cpp: nhồi prompt theo THỨ TỰ SLOT ────────────────

class _BGia:
    """Engine giả: mỗi nhịp `dt` có `toc × dt` token prompt, chia cho các slot
    theo THỨ TỰ CHỈ SỐ (như `server-context.cpp` 91f6a6cf3 :3110-3115). Slot của
    engine do B chọn (LCP/LRU, A không định được) — `thu_tu_chon` là thứ tự B
    đưa lượt MỚI vào slot; ca xấu C4: whale rơi vào slot chỉ số thấp hơn."""

    def __init__(self, toc: float, thu_tu_chon: list[int]):
        self.toc = toc
        self.chon = list(thu_tu_chon)
        self.con: dict[int, tuple[str, int]] = {}   # slot → (tên, token prompt còn)
        self.byte_dau: dict[str, float] = {}

    def vao(self, ten: str, token: int) -> None:
        self.con[self.chon.pop(0)] = (ten, token)

    def nhip(self, t: float, dt: float) -> list[str]:
        ngan_sach = self.toc * dt
        xong = []
        for slot in sorted(self.con):
            ten, con = self.con[slot]
            if con <= 0 or ngan_sach <= 0:
                continue
            an = min(con, ngan_sach)
            ngan_sach -= an
            self.con[slot] = (ten, con - an)
            if con - an <= 0:
                self.byte_dau[ten] = t + dt
                xong.append(ten)
        return xong


def _mo_phong_C4(db) -> tuple[dict[str, float], dict[str, float]]:
    """Trả (lúc vào engine, lúc byte đầu) theo giây. Lượt `dang_chay` đã decode;
    whale W1 chờ từ t=0 (luật 5: nhường lượt tương tác 30 s); lượt ngắn A (1.300)
    tới t=29,5; whale W2 tới t=31. B chọn slot: W1 → 0, A/W2 → 2, 3."""
    from platform_core.llm import admission

    ts0 = datetime.now(timezone.utc)
    b = _BGia(toc=1_100.0, thu_tu_chon=[2, 0, 3])
    dang_chay, _ = _xet(db, "dang_chay", now=ts0 - timedelta(seconds=10), moi=500)
    admission.danh_dau_prefill_xong(dang_chay.id)
    lease: dict[str, str] = {}
    vao_luc: dict[str, float] = {}
    toi = {"W1": (0.0, 32_000, True), "A": (29.5, 1_300, False),
           "W2": (31.0, 20_000, True)}
    dt, t = 0.1, 0.0
    while t < 90 and len(b.byte_dau) < len(toi):
        for ten, (luc_toi, tok, whale) in toi.items():
            if ten in lease or t < luc_toi:
                continue
            l, _ly = _xet(db, ten, now=ts0 + timedelta(seconds=t), moi=tok,
                          whale=whale, tuoi=t - luc_toi)
            if l is not None:
                lease[ten], vao_luc[ten] = l.id, t
                b.vao(ten, tok)
        for ten in b.nhip(t, dt):                   # byte dữ liệu đầu ⇒ `_phat`
            admission.danh_dau_prefill_xong(lease[ten])
        t = round(t + dt, 6)
    return vao_luc, b.byte_dau


def test_mo_phong_B_luot_ngan_khong_cho_het_prefill_32K(db):
    vao, dau = _mo_phong_C4(db)
    ttft_a = dau["A"] - 29.5
    assert ttft_a < 3.0, (vao, dau)                 # ~1,2 s: prefill 1.300 một mình
    assert vao["W1"] >= dau["A"] - 1e-6             # W1 chờ A xong prefill
    assert vao["W2"] >= dau["W1"] - 1e-6            # whale thứ hai chờ W1 xong prefill


def test_mo_phong_B_doi_chung_tat_luat_thi_luot_ngan_cho_ca_32K(db, monkeypatch):
    """Tắt luật (tài nguyên không khai) ⇒ W1 vào ở t=30, slot 0, đè A ⇒ TTFT của A
    ≈ thời gian prefill 32K (~29 s) — đúng số C4 thấy. Luật mà hỏng thì ca trên đỏ."""
    from platform_core.llm import admission

    monkeypatch.setattr(admission, "_BAN_DO_PREFILL", {})
    vao, dau = _mo_phong_C4(db)
    assert dau["A"] - 29.5 > 20.0, (vao, dau)
    assert vao["W2"] >= dau["W1"] - 1e-6            # ≤1 whale prefill: luật cũ vẫn giữ
