"""Auto Scan Video — CONTENT_PROCESS: dich, lineage, an toan cuoc goi tra tien.

Giai doan DAU TIEN tieu tien that. Nen phan quan trong nhat cua tep nay khong
phai chat luong ban dich — ma la **dieu gi xay ra khi cuoc goi that bai**.

  §1 hop dong van ban da xu ly
  §2 chia lo va gop tat dinh
  §3 an toan cuoc goi tra tien  <- trong tam
  §4 van tay
  §5 cong thoat
  §6 cho bang chung ngoai

⛔ Prompt 11 cam: khong sua ban ghi tai cho, khong sinh tieng noi.
"""
from __future__ import annotations

import json

import pytest

from tests.fixtures.asv_media import ban_ghi_gia

# 🔴 Pha 13: cac phep kiem trong tep nay chay HET chuoi, nen chung cham toi
#    `audio_prepare` — va truoc pha 13 dieu do co nghia la chung nap
#    **htdemucs THAT** moi luot gate, tren mot may dang phuc vu khach.
#    Fixture autouse duoi day thay dung mieng nang do; ffmpeg, kho, CSDL,
#    hang doi va worker van that.  (`LTT_TEST_NANG=1` de chay model that)
from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401


def _ban_ghi(so_doan: int = 3) -> dict:
    from apps.auto_scan_video import ban_ghi
    return ban_ghi.chuan_hoa(ban_ghi_gia(float(so_doan)), thoi_luong_nguon=60.0)


def _ban_dich_du(goc: dict) -> dict:
    return {d["ma"]: f"ban dich cua {d['ma']}" for d in goc["doan"]}


# ══════════════════════════════════════════════════════════════════════════════
#  §1 Hop dong van ban da xu ly
# ══════════════════════════════════════════════════════════════════════════════

def test_giu_NGUYEN_ma_doan_cua_ban_ghi():
    """Muc 3 — kheo noi giua hai tai lieu.

    Bon giai doan ha nguon (VOICE, TIMING, COMPOSE, QC) deu bam vao ma nay; mot
    lan danh so lai o day se lam ca bon lech mot cach im lang.
    """
    from apps.auto_scan_video import van_ban

    goc = _ban_ghi(3)
    tl = van_ban.dung(goc, _ban_dich_du(goc), provider="p", model="m")

    assert [m["ma"] for m in tl["muc"]] == [d["ma"] for d in goc["doan"]]


def test_GIU_CA_ban_goc_lan_ban_dich():
    """Bo ban goc di la bo kha nang tra loi cau hoi "no dich tu cai gi"."""
    from apps.auto_scan_video import van_ban

    goc = _ban_ghi(2)
    tl = van_ban.dung(goc, _ban_dich_du(goc), provider="p", model="m")

    for m, d in zip(tl["muc"], goc["doan"]):
        assert m["goc"] == d["chu"]
        assert m["chu"] != m["goc"]


def test_ban_ghi_nguon_KHONG_bi_sua_tai_cho():
    """⛔ Prompt 11 cam ro. Ban ghi la bang chung; ban dich la dien giai."""
    from apps.auto_scan_video import van_ban

    goc = _ban_ghi(3)
    truoc = json.dumps(goc, sort_keys=True, ensure_ascii=False)
    van_ban.dung(goc, _ban_dich_du(goc), provider="p", model="m")
    assert json.dumps(goc, sort_keys=True, ensure_ascii=False) == truoc


def test_THIEU_mot_doan_thi_TU_CHOI_ca_tai_lieu():
    """Muc 4 — phan hoi khong day du.

    ⛔ Chap nhan mot ban dich thieu nghia la ban long tieng se im lang o dung
       nhung cho do — va khong ai biet vi sao.
    """
    from apps.auto_scan_video import van_ban

    goc = _ban_ghi(3)
    thieu = _ban_dich_du(goc)
    del thieu[goc["doan"][1]["ma"]]

    with pytest.raises(van_ban.VanBanError) as loi:
        van_ban.dung(goc, thieu, provider="p", model="m")
    assert "1" in str(loi.value), "phai noi thieu bao nhieu doan"


def test_kiem_so_TAP_HOP_ma_chu_khong_so_SO_LUONG():
    """Hai tap cung kich thuoc van co the khac nhau — va do la dung kieu lech
    im lang can bat o day."""
    from apps.auto_scan_video import van_ban

    goc = _ban_ghi(2)
    tl = van_ban.dung(goc, _ban_dich_du(goc), provider="p", model="m")
    tl["muc"][0]["ma"] = "seg_9999"      # van du hai muc, nhung sai tap

    with pytest.raises(van_ban.VanBanError):
        van_ban.kiem(tl, goc)


def test_tom_tat_KHONG_chua_loi_thoai():
    """I16 — tom tat di vao `stage.outputs` va vao log."""
    from apps.auto_scan_video import van_ban

    goc = _ban_ghi(2)
    tl = van_ban.dung(goc, _ban_dich_du(goc), provider="p", model="m")
    goi = repr(van_ban.tom_tat(tl))
    assert "ban dich cua" not in goi and "cau thu" not in goi


# ══════════════════════════════════════════════════════════════════════════════
#  §2 Chia lo va gop tat dinh
# ══════════════════════════════════════════════════════════════════════════════

def test_chia_lo_giu_nguyen_thu_tu_va_khong_mat_doan():
    from apps.auto_scan_video import dich_thuat

    doan = [{"ma": f"seg_{i:04d}", "chu": str(i)} for i in range(1, 48)]
    cac_lo = dich_thuat.chia_lo(doan, moi_lo=20)

    assert [len(l) for l in cac_lo] == [20, 20, 7]
    assert [d["ma"] for l in cac_lo for d in l] == [d["ma"] for d in doan]


def test_gop_TAT_DINH_khong_phu_thuoc_thu_tu_model_tra_ve():
    """Model tra ve mot bang khoa theo ma, nen mot lo tra ve lon xon cung khong
    lam lech ket qua. Khong co phep doi chieu theo thu tu o bat cu dau."""
    from apps.auto_scan_video import dich_thuat

    ma = {"seg_0001", "seg_0002", "seg_0003"}
    lon_xon = '{"seg_0003":"ba","seg_0001":"mot","seg_0002":"hai"}'
    ra = dich_thuat._doc_ban_dich(lon_xon, ma)
    assert ra == {"seg_0001": "mot", "seg_0002": "hai", "seg_0003": "ba"}


def test_doc_duoc_JSON_bi_boc_trong_dau_nhay_ba():
    """Thoi quen rat pho bien cua model. No khong dang lam hong mot lan chay."""
    from apps.auto_scan_video import dich_thuat

    ra = dich_thuat._doc_ban_dich('```json\n{"seg_0001":"mot"}\n```',
                                  {"seg_0001"})
    assert ra == {"seg_0001": "mot"}


@pytest.mark.parametrize("hong", [
    "khong phai json gi ca",
    '{"seg_0001": }',
    '["mot","hai"]',
])
def test_phan_hoi_HONG_bi_bat(hong):
    from apps.auto_scan_video import dich_thuat

    with pytest.raises(dich_thuat.DichError):
        dich_thuat._doc_ban_dich(hong, {"seg_0001"})


def test_phan_hoi_THIEU_ma_bi_bat_kem_so_luong():
    from apps.auto_scan_video import dich_thuat

    with pytest.raises(dich_thuat.DichError) as loi:
        dich_thuat._doc_ban_dich('{"seg_0001":"mot"}',
                                 {"seg_0001", "seg_0002", "seg_0003"})
    assert "2" in str(loi.value) and "3" in str(loi.value)


# ══════════════════════════════════════════════════════════════════════════════
#  §3 An toan cuoc goi tra tien — TRONG TAM
# ══════════════════════════════════════════════════════════════════════════════

class TestAnToanCuocGoiTraTien:
    """I5 / G7. Day la giai doan dau tien co the tinh tien khach hai lan."""

    def test_dispatch_va_rejected_duoc_TRUYEN_THANG_tu_JobContext(self, monkeypatch):
        """🔑 Ngu nghia dispatch BEN VUNG cua nen tang.

        `ctx.provider_dispatched()` ghi `provider_state` xuong CSDL **ngay
        truoc** khi goi ra ngoai. Mot lan sap sau do doc ra duoc la "co the da
        goi", chu khong phai "chua goi".
        """
        from types import SimpleNamespace

        from apps.auto_scan_video import dich_thuat

        bat = {}

        def gia(db, **kw):
            bat.update(kw)
            return SimpleNamespace(content='{"seg_0001":"mot"}')

        monkeypatch.setattr("platform_core.llm.dieu_phoi.goi", gia)

        da_dispatch, da_reject = [], []
        ctx = SimpleNamespace(
            provider_dispatched=lambda *a, **k: da_dispatch.append(1),
            provider_rejected=lambda *a, **k: da_reject.append(1),
            is_cancelled=None, progress=None)

        dich_thuat.dich_mot_lo(None, [{"ma": "seg_0001", "chu": "x"}],
                               ngon_ngu_goc="en", ctx=ctx)

        assert bat["on_dispatch"] is not None, "khong truyen on_dispatch"
        assert bat["on_rejected"] is not None, "khong truyen on_rejected"

    def test_mat_ket_noi_SAU_KHI_gui_thanh_DichMoHo(self, monkeypatch):
        """⛔ Loi nay KHONG BAO GIO duoc thu lai tu dong.

        Provider co the da nhan yeu cau va da tinh tien; thu lai la bien mot lan
        goi tra tien thanh hai.
        """
        from apps.auto_scan_video import dich_thuat

        class AmbiguousProviderError(RuntimeError):
            pass

        def gia(db, **kw):
            raise AmbiguousProviderError("mat ket noi sau khi bat dau gui")

        monkeypatch.setattr("platform_core.llm.dieu_phoi.goi", gia)

        with pytest.raises(dich_thuat.DichMoHo):
            dich_thuat.dich_mot_lo(None, [{"ma": "seg_0001", "chu": "x"}],
                                   ngon_ngu_goc="")

    def test_loi_KHONG_mo_ho_van_la_DichError_thu_lai_duoc(self, monkeypatch):
        """Phan biet hai loai la ca diem cua viec phan loai: mot ben thu lai
        duoc, mot ben khong."""
        from apps.auto_scan_video import dich_thuat

        def gia(db, **kw):
            raise RuntimeError("het khoa kha dung")

        monkeypatch.setattr("platform_core.llm.dieu_phoi.goi", gia)

        with pytest.raises(RuntimeError) as loi:
            dich_thuat.dich_mot_lo(None, [{"ma": "seg_0001", "chu": "x"}],
                                   ngon_ngu_goc="")
        assert not isinstance(loi.value, dich_thuat.DichMoHo)

    def test_giai_doan_hong_MO_HO_thi_job_KHONG_quay_lai_hang_doi(self, tmp_path,
                                                                  monkeypatch):
        """Chuoi day du: dispatch mo ho -> giai doan hong -> job KHONG chay lai.

        Do la nua thu hai cua I5, va no khong the kiem bang mot phep kiem don
        vi: phai xem hang doi that.
        """
        import platform_core.db as dbmod
        from platform_core import credit, jobs
        from platform_core.job_runner import JobContext
        from platform_core.storage import LocalStorage, set_storage
        from tests.conftest import bao_dam_user
        from tests.fixtures.asv_media import nap_nguon_vao_kho

        monkeypatch.setenv("LTT_DATABASE_URL",
                           f"sqlite:///{(tmp_path / 'p11.db').as_posix()}")
        dbmod.reset_engine()
        import platform_core.models  # noqa: F401
        from platform_core.registry import load_app_tables
        load_app_tables()
        dbmod.Base.metadata.create_all(dbmod.get_engine())
        db = next(dbmod.get_session())
        kho = LocalStorage(str(tmp_path / "kho")); set_storage(kho)

        from apps.auto_scan_video import (dich_thuat, features,
                                          giai_doan_chep_loi)
        monkeypatch.setattr(giai_doan_chep_loi, "chep_loi",
                            lambda duong_tieng, **kw: ban_ghi_gia(2.0))

        def mo_ho(db_, ban, ctx=None):
            raise dich_thuat.DichMoHo("co the da goi provider")

        monkeypatch.setattr(dich_thuat, "dich_ban_ghi", mo_ho)
        try:
            bao_dam_user(db, "uA"); credit.nap(db, "uA", 1000)
            khoa = nap_nguon_vao_kho(kho, tmp_path, owner_id="uA")
            run = features.tao_run(db, owner_id="uA", source_key=khoa,
                                   settings={}, uoc_luong_credit=10)
            db.commit()

            for _ in range(14):
                job = jobs.claim(db, worker_id="w",
                                 capabilities={"api", "ffmpeg", "gpu", "voice"})
                if job is None:
                    break
                db.commit()
                ctx = JobContext(job.id); ctx.job_type = job.job_type
                try:
                    jobs.complete(db, job, jobs.resolve_handler(job.job_type)(
                        dict(job.params), ctx) or {})
                except Exception as exc:      # noqa: BLE001
                    jobs.fail(db, job, str(exc), retry=False)
                db.commit()
            db.expire_all()

            s = features.giai_doan_theo_ten(db, run.id, "content_process")
            assert s.status != "succeeded"
            assert jobs.claim(db, worker_id="w2",
                              capabilities={"api", "ffmpeg", "gpu", "voice"}) is None, (
                "job dich mo ho van con trong hang doi -> se goi provider lan hai")
        finally:
            db.close(); set_storage(None); dbmod.reset_engine()

    def test_KHONG_co_du_phong_provider_im_lang(self):
        """Muc 8. Doi model la doi chat luong ban dich — tuc doi san pham.

        ⛔ Mot lan doi lang le nghia la khach nhan mot ban dich khac ma khong ai
           noi gi.
        """
        from apps.auto_scan_video import dich_thuat

        assert len(dich_thuat.THU_TU_PROVIDER) == 1, (
            "da them provider thu hai — no phai vao van tay TRUOC, va phai la "
            "mot quyet dinh san pham chu khong phai mot du phong im lang")

    def test_xin_tran_token_theo_TEN_CUA(self):
        """🔴 CLAUDE.md ghi mot loi da xay ra that: cua stream muon ngan sach
        1.024 cua cua dong bo, va **moi cau tra loi dai cut o dung 1.024 token,
        im lang**. Bai hoc la xin theo TEN CUA.
        """
        import inspect

        from apps.auto_scan_video import dich_thuat

        ma = inspect.getsource(dich_thuat._tran_token_ra)
        assert 'mac_dinh_cho("job")' in ma, (
            "phai xin ngan sach theo ten cua, khong dung mot mac dinh chung")


# ══════════════════════════════════════════════════════════════════════════════
#  §4 Van tay
# ══════════════════════════════════════════════════════════════════════════════

def test_van_tay_doi_theo_ban_ghi_provider_model_va_ngon_ngu():
    from apps.auto_scan_video import van_ban

    goc = dict(checksum_ban_ghi="aaa", provider="ltt_llm", model="ltt_llm",
               ngon_ngu_dich="vi")
    nen = van_ban.van_tay_van_ban(**goc)

    assert nen != van_ban.van_tay_van_ban(**{**goc, "checksum_ban_ghi": "bbb"})
    assert nen != van_ban.van_tay_van_ban(**{**goc, "provider": "gemini"})
    assert nen != van_ban.van_tay_van_ban(**{**goc, "model": "khac"})
    assert nen != van_ban.van_tay_van_ban(**{**goc, "ngon_ngu_dich": "en"})


def test_van_tay_doi_khi_LOI_NHAC_doi(monkeypatch):
    """Doi loi nhac = doi ban dich, ke ca khi moi thu khac giu nguyen."""
    from apps.auto_scan_video import van_ban

    goc = dict(checksum_ban_ghi="aaa", provider="p", model="m",
               ngon_ngu_dich="vi")
    truoc = van_ban.van_tay_van_ban(**goc)
    monkeypatch.setattr(van_ban, "PHIEN_BAN_LOI_NHAC", 2)
    assert van_ban.van_tay_van_ban(**goc) != truoc


# ══════════════════════════════════════════════════════════════════════════════
#  §5 Cong thoat
# ══════════════════════════════════════════════════════════════════════════════

def test_cong_thoat_CONTENT_chay_o_lan_API_va_giu_lineage(tmp_path, monkeypatch):
    """Cong thoat pha 11.

    Ba dieu: giai doan chay o lan `api` (khong phai ffmpeg), ban dich ben vung
    va kiem duoc, va ma doan khop 1:1 voi ban ghi.
    """
    import platform_core.db as dbmod
    from platform_core import credit, jobs
    from platform_core.job_runner import JobContext
    from platform_core.models import Job
    from platform_core.storage import LocalStorage, set_storage
    from sqlalchemy import select
    from tests.conftest import bao_dam_user
    from tests.fixtures.asv_media import nap_nguon_vao_kho

    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'p11b.db').as_posix()}")
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    kho = LocalStorage(str(tmp_path / "kho")); set_storage(kho)

    from apps.auto_scan_video import (assets, dich_thuat, features,
                                      giai_doan_chep_loi, van_ban)
    monkeypatch.setattr(giai_doan_chep_loi, "chep_loi",
                        lambda duong_tieng, **kw: ban_ghi_gia(2.0))
    monkeypatch.setattr(
        dich_thuat, "dich_ban_ghi",
        lambda db_, ban, ctx=None: {d["ma"]: f"dich {d['ma']}"
                                    for d in ban["doan"]})
    try:
        bao_dam_user(db, "uA"); credit.nap(db, "uA", 1000)
        khoa = nap_nguon_vao_kho(kho, tmp_path, owner_id="uA")
        run = features.tao_run(db, owner_id="uA", source_key=khoa, settings={},
                               uoc_luong_credit=10)
        db.commit()

        for _ in range(14):
            job = jobs.claim(db, worker_id="w",
                             capabilities={"api", "ffmpeg", "gpu", "voice"})
            if job is None:
                break
            db.commit()
            ctx = JobContext(job.id); ctx.job_type = job.job_type
            try:
                jobs.complete(db, job, jobs.resolve_handler(job.job_type)(
                    dict(job.params), ctx) or {})
            except Exception as exc:      # noqa: BLE001
                jobs.fail(db, job, str(exc), retry=False)
            db.commit()
        db.expire_all()

        s = features.giai_doan_theo_ten(db, run.id, "content_process")
        assert s.status == "succeeded", f"content: {s.status} {s.error}"

        # (a) lan API
        con = db.execute(select(Job).where(
            Job.plan_id == run.id,
            Job.step_id == "content_process")).scalars().all()
        assert len(con) == 1
        assert con[0].app_slug == "auto_scan_video", (
            "CONTENT phai chay o lan api, khong phai lan ffmpeg")
        assert con[0].admission_resource == "llm_remote", (
            "phai gianh cung tai nguyen voi ltt_llm")

        # (b) ben vung va kiem duoc
        khoa_ra = (s.outputs or {}).get("khoa_asset") or []
        a = assets.asset_cua(db, khoa_ra[0], "uA")
        assert assets.kiem_toan_ven(db, kho, a) == "ok"

        # (c) lineage 1:1 voi ban ghi
        truoc = features.giai_doan_theo_ten(db, run.id, "transcribe")
        with kho.open([k for k in (truoc.outputs or {})["khoa_asset"]][0]) as f:
            goc = json.loads(f.read())
        with kho.open(a.storage_key) as f:
            tl = json.loads(f.read())
        van_ban.kiem(tl, goc)
        assert [m["ma"] for m in tl["muc"]] == [d["ma"] for d in goc["doan"]]

        # (d) ban ghi nguon van NGUYEN VEN
        assert assets.kiem_toan_ven(
            db, kho, assets.asset_cua(
                db, (truoc.outputs or {})["khoa_asset"][0], "uA")) == "ok"
    finally:
        db.close(); set_storage(None); dbmod.reset_engine()


# ══════════════════════════════════════════════════════════════════════════════
#  §6 Cho bang chung ngoai
# ══════════════════════════════════════════════════════════════════════════════

class TestChoBangChungNgoai:
    """Nhung thu may nay khong chung minh duoc."""

    def test_chua_goi_model_THAT_lan_nao(self):
        """⛔ Moi phep kiem o day dung mot model gia.

        Goi model nha that can `llm_gateway` tren may B song va mot khoa hop le
        — tuc mot phu thuoc ngoai ma bo test khong duoc phep doi hoi. Do chinh
        xac ban dich, do dai cau tieng Viet so voi cau goc (RISK-02-01), va hanh
        vi that khi gap 429/timeout deu **chua duoc do**.

        Ghi ra day de pha 21 khong tuong rang duong dich da duoc nghiem thu that.
        """
        from apps.auto_scan_video import dich_thuat

        assert dich_thuat.THU_TU_PROVIDER == ("ltt_llm",)
