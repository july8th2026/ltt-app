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


# ── L-12 ──────────────────────────────────────────────────────────────────
def _waiter(prefill: int, nhip: datetime):
    class _W:
        token_prefill_moi = prefill
        heartbeat_at = nhip
        trang_thai = "cho"
        resource = "r"
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


TRAN = 57_000


def _goi(dang_cho, moi):
    gio = datetime.now(timezone.utc)
    phong_cho.kiem_phong(
        _Phong([_waiter(p, gio) for p in dang_cho]), resource="r",
        token_prefill_moi=moi, so_nguoi_toi_da=32,
        token_prefill_toi_da=TRAN, now=gio)


def test_mon_LON_HON_TRAN_van_duoc_vao_hang_du_co_nguoi_cho():
    """🔴 Ve chinh cua L-12 — va no DO tren ban truoc ban va."""
    _goi(dang_cho=[10_000], moi=68_000)      # khong duoc nem


def test_mon_lon_van_vao_duoc_khi_phong_TRONG():
    _goi(dang_cho=[], moi=68_000)


def test_CHI_MOT_mon_lon_cung_luc():
    """Quyen vao hang cho mon lon khong duoc bien hang cho thanh kho prefill."""
    with pytest.raises(phong_cho.PhongDay) as e:
        _goi(dang_cho=[68_000], moi=70_000)
    assert e.value.ly_do == "phong_day_mot_mon_lon"


def test_tran_TONG_cho_mon_thuong_VAN_GIU_NGUYEN():
    """⛔ DOI CHUNG cho chinh ban va: no khong duoc noi long luat cu.

    Thieu ve nay thi mot ban va "cho tat ca qua" cung se XANH o ba ve tren.
    """
    with pytest.raises(phong_cho.PhongDay) as e:
        _goi(dang_cho=[30_000, 20_000], moi=10_000)   # 60.000 > 57.000
    assert e.value.ly_do == "phong_day_token_prefill"


def test_tran_SO_NGUOI_van_giu_nguyen():
    gio = datetime.now(timezone.utc)
    with pytest.raises(phong_cho.PhongDay) as e:
        phong_cho.kiem_phong(
            _Phong([_waiter(1, gio) for _ in range(3)]), resource="r",
            token_prefill_moi=1, so_nguoi_toi_da=3,
            token_prefill_toi_da=TRAN, now=gio)
    assert e.value.ly_do == "phong_day_so_nguoi"
