"""G5 — chot so GPU trong vong bao tri (`KE_HOACH_TIEP_2026-08-24.md` §4).

## Vi sao viec nay ton tai

Lien ket driver cua card thu hai tren may nay **mong manh** (`oem3.inf` khong
liet ke no). Khi no rung thi **khong co gi hong**: job van chay, chi la tat ca
don vao mot card. Nang luc giam mot nua va moi tin hieu van xanh — khong ngoai
le, khong job do, khong canh bao.

⇒ Day la mot loi **im lang**, va mot loi im lang chi bat duoc bang mot phep dem
chu dong. Do la toan bo noi dung cua G5.

## Cai bay tep nay canh

Con so "may nay phai co may card" **khong tu suy duoc**. Hai cach "thong minh"
deu sai, va ca hai deu hong IM LANG:

  · doc so card luc khoi dong  -> may khoi dong lai khi card DA rung se chot
                                  muc thap do thanh "binh thuong" vinh vien;
  · nho muc cao nhat tung thay -> mot lan cam thu card thu ba lam may bao thieu
                                  mai mai.

Nen no la mot **tuyen bo ve phan cung** do nguoi khai, va khong khai = tat.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def jr(monkeypatch):
    import platform_core.job_runner as m
    monkeypatch.delenv(m.GPU_MONG_DOI_ENV, raising=False)
    return m


class _Gpu:
    def __init__(self, i): self.index, self.uuid = i, f"GPU-{i}"


def _gia_lap(monkeypatch, jr, *, so_card: int):
    from platform_core import gpu as gpu_mod
    monkeypatch.setattr(gpu_mod, "list_gpus",
                        lambda: [_Gpu(i) for i in range(so_card)])


# ── Doc cau hinh ─────────────────────────────────────────────────────────────

def test_khong_khai_thi_TAT_han_phep_kiem(jr, monkeypatch):
    """Mot canh bao ban tren may chua bao gio co card thu hai la mot canh bao bi
    tat tieng — va mot canh bao bi tat tieng te hon khong co canh bao."""
    _gia_lap(monkeypatch, jr, so_card=1)
    assert jr._so_gpu_mong_doi() == 0
    assert jr._quet_so_gpu() == -1, "khong khai ma van quet"


def test_khai_sai_kieu_thi_TAT_va_NOI_RA(jr, monkeypatch, caplog):
    """🔴 Khai sai te hon khong khai: nguoi van hanh tuong minh da bat.

    Nen no phai tat (an toan) NHUNG phai de lai mot dong log — im lang o day la
    dung cai loi ma ca phep kiem nay sinh ra de chan.
    """
    monkeypatch.setenv(jr.GPU_MONG_DOI_ENV, "hai")
    with caplog.at_level("WARNING"):
        assert jr._so_gpu_mong_doi() == 0
    # `caplog.text` la ban DA dinh dang — `r.message` chua chac co, va `% r.args`
    # thi no vao dung cai bay dinh dang cua chinh no.
    assert jr.GPU_MONG_DOI_ENV in caplog.text, caplog.text


@pytest.mark.parametrize("gia_tri,mong", [("2", 2), ("1", 1), ("0", 0), ("-3", 0)])
def test_doc_duoc_so_hop_le(jr, monkeypatch, gia_tri, mong):
    monkeypatch.setenv(jr.GPU_MONG_DOI_ENV, gia_tri)
    assert jr._so_gpu_mong_doi() == mong


# ── Dem va bao dong ──────────────────────────────────────────────────────────

def test_du_card_thi_KHONG_bao(jr, monkeypatch):
    monkeypatch.setenv(jr.GPU_MONG_DOI_ENV, "2")
    _gia_lap(monkeypatch, jr, so_card=2)
    goi = []
    _chan_alert(monkeypatch, goi)
    assert jr._quet_so_gpu() == 2
    assert goi == [], "du card ma van bao"


def test_thua_card_cung_KHONG_bao(jr, monkeypatch):
    """Cam them card la tin tot. Bao dong vi tin tot la cach nguoi ta hoc cach
    bo qua canh bao."""
    monkeypatch.setenv(jr.GPU_MONG_DOI_ENV, "2")
    _gia_lap(monkeypatch, jr, so_card=3)
    goi = []
    _chan_alert(monkeypatch, goi)
    assert jr._quet_so_gpu() == 3
    assert goi == []


def test_thieu_card_thi_BAO(jr, monkeypatch, caplog):
    monkeypatch.setenv(jr.GPU_MONG_DOI_ENV, "2")
    _gia_lap(monkeypatch, jr, so_card=1)
    goi = []
    _chan_alert(monkeypatch, goi)
    with caplog.at_level("WARNING"):
        assert jr._quet_so_gpu() == 1
    assert goi, "thieu card ma khong bao"
    from platform_core.public_api import notifications
    assert all(g["kind"] == notifications.GPU_MISSING for g in goi)
    # Log phai co truoc thu, de hop thu hong thi con so van con dau vet.
    assert "THIEU GPU" in caplog.text


def test_khoa_khu_trung_lap_mang_CON_SO(jr, monkeypatch):
    """🔴 1/2 va 0/2 la HAI su viec khac nhau.

    Neu khoa chi la "gpu" thi card thu hai rung se bi im lang suot ca chu ky
    nghi (mot ngay), chi vi card thu nhat vua duoc bao. Dung luc te nhat: may
    dang mat card lien tiep.
    """
    monkeypatch.setenv(jr.GPU_MONG_DOI_ENV, "2")
    goi = []
    _chan_alert(monkeypatch, goi)

    _gia_lap(monkeypatch, jr, so_card=1)
    jr._quet_so_gpu()
    _gia_lap(monkeypatch, jr, so_card=0)
    jr._quet_so_gpu()

    khoa = {g["subject"] for g in goi}
    assert khoa == {"gpu:1/2", "gpu:0/2"}, khoa


# ── Noi dung canh bao ────────────────────────────────────────────────────────

def test_than_canh_bao_NOI_RO_no_khong_lam_job_hong(jr, monkeypatch):
    """⭐ Nguoi doc canh bao nay se di tim job do, va se khong thay cai nao.

    Than thu phai chan viec do lai: van de la thong luong, khong phai loi. Mot
    canh bao khong noi ro dieu do se bi doc thanh bao dong gia.
    """
    monkeypatch.setenv(jr.GPU_MONG_DOI_ENV, "2")
    _gia_lap(monkeypatch, jr, so_card=1)
    goi = []
    _chan_alert(monkeypatch, goi)
    jr._quet_so_gpu()
    than = goi[0]["body"]
    assert "không có job nào hỏng" in than.lower() or "khong co job nao hong" in than.lower()
    assert "nvidia-smi -L" in than, "phai chi ra lenh de nguoi truc tu kiem"


# ── Noi dat: PHAI nam duoi lease bao tri ─────────────────────────────────────

def test_goi_trong_vong_bao_tri_chu_khong_trong_vong_job():
    """🔴 `_mot_luot_bao_tri` chay duoi lease `bao_tri` ⇒ DUNG MOT LAN tren toan
    cum. Vong job chay o MOI tien trinh worker.

    Dat nham cho thi moi worker gui mot thu ve cung mot card — dung lop loi ma
    H36 sinh ra de sua (webhook trung, canh bao trung, don rac chay N lan).
    """
    import inspect

    from platform_core import job_runner

    than = inspect.getsource(job_runner._mot_luot_bao_tri)
    assert "_quet_so_gpu()" in than

    vong = inspect.getsource(job_runner._chay_mot_job)
    assert "_quet_so_gpu" not in vong


def test_loi_khi_dem_KHONG_lam_dung_viec_khac():
    """`nvidia-smi` treo khong duoc lam dung viec don du lieu va giao webhook."""
    import inspect

    from platform_core import job_runner

    than = inspect.getsource(job_runner._mot_luot_bao_tri)
    i = than.index("_quet_so_gpu()")
    quanh = than[max(0, i - 200):i + 200]
    assert "try:" in quanh and "except" in quanh


def _chan_alert(monkeypatch, goi: list) -> None:
    """Bat moi `raise_alert` lai thay vi cham CSDL."""
    from platform_core.public_api import notifications

    def gia(db, *, user_id, kind, subject="", title="", body="", now=None):
        goi.append({"user_id": user_id, "kind": kind, "subject": subject,
                    "title": title, "body": body})
        return object()

    monkeypatch.setattr(notifications, "raise_alert", gia)

    # Khong cham CSDL that: phep kiem nay noi ve phep DEM va noi dung canh bao,
    # khong noi ve tang luu tru.
    import platform_core.job_runner as jr_mod

    class _Db:
        def execute(self, *a, **kw):
            class _Kq:
                def scalars(self_inner): return self_inner
                def all(self_inner): return [_Admin()]
            return _Kq()

        def commit(self): pass

    class _Admin:
        id = "admin-1"

    monkeypatch.setattr(jr_mod, "_one_session", lambda: iter([_Db()]))
