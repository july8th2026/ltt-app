"""test_1250 — L-11 va L-12, hai loi do MA TRAN TEST JOB DAI tim ra tren production.

⛔ Ca hai deu **khong mot unit test nao trong kho bat duoc**, vi ca hai chi hien
   ra khi he DANG DAY va co mot bien co that (deploy, hoac mot khach gui ngu
   canh lon giua luc dong). Do la ly do chuong trinh "Van hanh that" ton tai:
   `docs/ltt_llm_dual/MA_TRAN_TEST_JOB_DAI.md`.

## L-11 — deploy giet stream => mat toi 20 phut suc chua

Deploy giua luc 6 luot stream dang chay: tien trinh chet, luong dap nhip chet
theo, sau dong lease nam lai giu TOAN BO suc chua. Do duoc: im 516 s, con han
toi phut 20.

⭐ Doi chieu Kubernetes Lease API: ho KHONG xoa lease luc khoi dong, ho dat
   `leaseDurationSeconds` la BOI SO NHO cua nhip lam moi (1,5-4x). Ta dang o
   **20x** (nhip 60 s / han 1200 s).

## L-12 — request prefill LON bi duoi khi co nguoi khac cho

Cung MOT request 67.989 token (duoi tran vao 171.458):

    phong cho TRONG     -> 200, chay tron
    phong cho CO NGUOI  -> 429 sau 0,48 s

Vi `sum(...) + moi` luon vuot ngay khi mon ay TU NO lon hon tran phong. Cho bao
lau cung vo ich, va cau chu "busy, retry later" la mot loi khuyen khong bao gio
dung cho ca nay.

## L-12b (17/09/2026) — go HAN tran token cua phong cho

Ban va 13/09 chi noi cho MOT mon lon. Tran 57.000 tren tong token MOI cua nguoi
CHO la luat thu hai cho cung cau hoi ma `luat_nhan` luat 2 (tong token dat cho
cua luot DANG CHAY + luot nay <= pool KV) da tra loi — va no con duoi oan: mot
whale 68K dang cho lam MOI luot moi 429. Chu du an chot 17/09: nhan theo NGAN
SACH, luot chua vua thi CHO. Phong cho chi con chan DO DAI HANG (so nguoi, so
whale). Cac ve luat nhan (backfill, chong bo doi) o `test_1203`.
"""
from datetime import datetime, timedelta, timezone

import pytest

from platform_core.llm import admission, phong_cho


# ── L-11 ──────────────────────────────────────────────────────────────────
def test_han_mo_coi_cua_STREAM_ngan_hon_han_chung():
    assert admission.ORPHAN_TIMEOUT_STREAM < admission.ORPHAN_TIMEOUT, (
        "lease stream dung chung han 20 phut voi job nen — do chinh la L-11: mot "
        "deploy lam mat TOAN BO suc chua trong 20 phut.")


def test_han_stream_nam_trong_dai_KUBERNETES():
    """🔴 Nguong phai co NGUON. Nguon o day la ty le han/nhip cua Kubernetes.

    `coordination/v1`: `leaseDurationSeconds` la boi so nho cua nhip lam moi —
    mac dinh cua ho lam moi 10 s / han 15-40 s, tuc **1,5-4x**.
    """
    ty_le = admission.ORPHAN_TIMEOUT_STREAM.total_seconds() / admission.HEARTBEAT_SECONDS
    assert 1.5 <= ty_le <= 4.0, (
        f"han/nhip = {ty_le:.1f}x, ngoai dai Kubernetes 1,5-4x. "
        "Duoi 1,5x thi mot nhip lo lam thu lease cua nguoi DANG duoc phuc vu; "
        "tren 4x thi quay lai L-11 duoi mot con so khac.")


def test_reclaim_don_lease_STREAM_som_hon_lease_NEN(monkeypatch):
    """Hanh vi, khong phai hang so: cung mot moc nhip, stream bi thu con nen thi khong."""
    gio = datetime.now(timezone.utc)
    cu = gio - timedelta(minutes=5)          # 5 phut: qua 180 s, chua qua 20 phut

    class _Gia:
        def __init__(self, mode):
            self.mode, self.heartbeat_at, self.resource = mode, cu, "r"

    da_xoa: list = []

    class _DbGia:
        def query(self, *a):
            return self

        def filter(self, *a):
            return self

        def all(self):
            return [_Gia("stream"), _Gia("nen")]

        def delete(self, x):
            da_xoa.append(x.mode)

        def flush(self):
            pass

    monkeypatch.setattr(admission, "_now", lambda: gio)
    n = admission.reclaim_expired(_DbGia())
    assert da_xoa == ["stream"], (
        f"doi chi don lease stream, thuc te don: {da_xoa}. Lease nen chay dai va "
        "dap nhip thua thot hon — thu no som la giet mot job dang chay.")
    assert n == 1


# ── L-12 / L-12b ──────────────────────────────────────────────────────────
def _waiter(prefill: int, nhip: datetime, whale: bool = False):
    class _W:
        token_prefill_moi = prefill
        heartbeat_at = nhip
        trang_thai = "cho"
        resource = "r"
        la_whale = whale
    return _W()


class _Phong:
    """Ban gia toi thieu cua `db` cho `kiem_phong`."""

    def __init__(self, dsach):
        self._d = dsach

    def query(self, *a):
        return self

    def filter(self, *a):
        return self

    def all(self):
        return self._d


def _goi(dang_cho, *, whale=False, so_nguoi=32, so_ca_voi=2):
    """`dang_cho`: danh sach `(prefill, la_whale)`."""
    gio = datetime.now(timezone.utc)
    phong_cho.kiem_phong(
        _Phong([_waiter(p, gio, w) for p, w in dang_cho]), resource="r",
        so_nguoi_toi_da=so_nguoi, la_whale=whale, so_ca_voi_toi_da=so_ca_voi, now=gio)


def test_mon_LON_van_duoc_vao_hang_du_co_nguoi_cho():
    """🔴 Ve chinh cua L-12 — va no DO tren ban truoc ban va 13/09."""
    _goi([(10_000, False)], whale=True)      # 68K: khong duoc nem


def test_mon_lon_van_vao_duoc_khi_phong_TRONG():
    _goi([], whale=True)


def test_mot_whale_dang_cho_khong_duoi_luot_nho():
    """🔴 L-12b: ban va 13/09 cong CA whale dang cho vao tran 57K — mot whale 68K
    trong phong lam luot 10 token 429 (`phong_day_token_prefill`). Ve nay DO tren
    ban 13/09."""
    _goi([(68_000, True)], whale=False)


def test_luot_THU_HAI_lon_hon_57K_cung_vao_hang():
    """🔴 L-12b: ban 13/09 chi cho MOT mon >57K (`phong_day_mot_mon_lon`)."""
    _goi([(68_000, True)], whale=True)


def test_so_WHALE_cho_co_tran_va_429_TRUOC_200():
    """Whale chay NOI TIEP; hang whale khong chan thi whale cuoi het trần chờ
    GIUA SSE. Tran so whale bien ca ay thanh 429 truoc 200."""
    with pytest.raises(phong_cho.PhongDay) as e:
        _goi([(68_000, True), (150_000, True)], whale=True, so_ca_voi=2)
    assert e.value.ly_do == "phong_day_ca_voi"


def test_tran_so_whale_KHONG_chan_luot_thuong():
    """Doi chung: cung phong day whale, luot thuong van vao hang."""
    _goi([(68_000, True), (150_000, True)], whale=False, so_ca_voi=2)


def test_tran_SO_NGUOI_van_giu_nguyen():
    with pytest.raises(phong_cho.PhongDay) as e:
        _goi([(1, False)] * 3, so_nguoi=3)
    assert e.value.ly_do == "phong_day_so_nguoi"


def test_phong_cho_KHONG_con_tran_token():
    """⛔ Chot bat bien chu du an 17/09: "co vua khong" chi co MOT nguoi tra loi.

    Tong token MOI dang cho vuot xa 57K ma luot thuong van vao hang — viec cua
    no la CHO toi khi `luat_nhan` luat 2 thay vua pool.
    """
    _goi([(30_000, False), (20_000, False), (40_000, False)], whale=False)
    import inspect
    assert "token_prefill_toi_da" not in inspect.signature(phong_cho.kiem_phong).parameters


def test_whale_duoc_cho_LAU_HON_luot_thuong_o_cua_stream(monkeypatch):
    from platform_core.llm import tham_so_da_luot
    for k in ("LTT_LLM_CHO_STREAM_S", "LTT_LLM_CHO_STREAM_WHALE_S"):
        monkeypatch.delenv(k, raising=False)
    ts = tham_so_da_luot.doc()
    assert ts.han_cho_stream(True) > ts.han_cho_stream(False)
    # Mot luot 150K tren 3.8 prefill ~230 s: whale thu hai xep sau no phai cho
    # duoc tron luot ay + phan sinh — 300 s chung la khong du.
    assert ts.han_cho_stream(True) >= 600


# ── L-12b: so suat va pool KV la HAI num cau hinh DOC LAP (chu du an 17/09) ─
def test_so_suat_va_pool_la_hai_num_doc_lap_va_CHI_HA(monkeypatch):
    from platform_core.registry import (ENV_POOL, ENV_SO_SUAT, AdmissionModel,
                                        ap_cau_hinh_admission)

    khai = AdmissionModel("ltt_38_3090", 3, 221_184, "rtx3090", "mac_dinh")
    for k in (ENV_SO_SUAT + "ltt_38_3090", ENV_POOL + "ltt_38_3090"):
        monkeypatch.delenv(k, raising=False)
    assert ap_cau_hinh_admission(khai) == khai, "khong env => dung ban khai"

    monkeypatch.setenv(ENV_SO_SUAT + "ltt_38_3090", "2")
    am = ap_cau_hinh_admission(khai)
    assert (am.slots, am.token_pool) == (2, 221_184), "doi so suat KHONG duoc cham pool"

    monkeypatch.delenv(ENV_SO_SUAT + "ltt_38_3090")
    monkeypatch.setenv(ENV_POOL + "ltt_38_3090", "200000")
    am = ap_cau_hinh_admission(khai)
    assert (am.slots, am.token_pool) == (3, 200_000), "doi pool KHONG duoc cham so suat"
    assert (am.resource, am.residency_group, am.vai_tro) == ("ltt_38_3090", "rtx3090", "mac_dinh")

    # ⛔ Khong bao gio vuot tran engine (`-np`, `-c`): env chi HA.
    monkeypatch.setenv(ENV_SO_SUAT + "ltt_38_3090", "8")
    monkeypatch.setenv(ENV_POOL + "ltt_38_3090", "999999")
    am = ap_cau_hinh_admission(khai)
    assert (am.slots, am.token_pool) == (3, 221_184)


def test_num_cau_hinh_di_qua_DUONG_THAT_cua_tool_ltt_llm(monkeypatch):
    """Doi chung duong goi: env phai toi `tool.admission_cho(model)` — cua ma
    `tien_kiem`, `job` va `admission_luc_nop` cung doc."""
    from platform_core.registry import ENV_SO_SUAT
    from apps.ltt_llm.manifest import MANIFEST

    tool = next(t for t in MANIFEST.tools if t.admission_theo_model)
    goc = tool.admission_cho("ltt-3.8")
    monkeypatch.setenv(ENV_SO_SUAT + goc.resource, "1")
    assert tool.admission_cho("ltt-3.8").slots == 1
    assert tool.admission_cho("ltt-3.5").slots == goc.slots, "num cua 3.8 lan sang 3.5"
