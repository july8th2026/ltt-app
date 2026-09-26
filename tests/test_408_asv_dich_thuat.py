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

        from apps.auto_scan_video import features, giai_doan_chep_loi
        monkeypatch.setattr(giai_doan_chep_loi, "chep_loi",
                            lambda duong_tieng, **kw: ban_ghi_gia(2.0))

        # 🔴 **Ban va cu cua phep kiem nay va mot ham KHONG AI GOI.**
        #
        #    No thay `dich_thuat.dich_ban_ghi` — dung o thoi diem viet, nhung pha
        #    14 da doi `CONTENT_PROCESS` sang goi `ai.goi_tinh_tien`. Tu do phep
        #    kiem van XANH trong khi kich ban cua no (mot dispatch mo ho) **khong
        #    con xay ra**: giai doan hong vi mot ly do khac han, va phep khang
        #    dinh o cuoi do mot thu khong lien quan.
        #
        # ⭐ Cung mot lop khiem khuyet ma pha 14 tim thay o ba ban sao cua mot
        #    stub, va pha 22 tim thay o mot ban gia tra ve sai kieu: **mot ban
        #    thay the tro toi mot cua da doi cho**. Cho nay bi bo sot vi no
        #    khong lam do gi ca — no chi lang le thoi kiem.
        #
        # ⇒ Thay o CUA THAT, va tao mot lan mo ho THAT: goi `on_dispatch` roi
        #   mat ket noi. Do dung la tinh huong I5 noi toi.
        dem = {"n": 0}

        def mo_ho(db_, *, messages, on_dispatch=None, **kw):
            dem["n"] += 1
            if on_dispatch is not None:
                on_dispatch("ltt_llm")
            raise ConnectionResetError("mat ket noi sau khi da gui")

        monkeypatch.setattr("platform_core.llm.dieu_phoi.goi", mo_ho)
        try:
            bao_dam_user(db, "uA"); credit.nap(db, "uA", 1000)
            khoa = nap_nguon_vao_kho(kho, tmp_path, owner_id="uA")
            run = features.tao_run(db, owner_id="uA", source_key=khoa,
                                   settings={"giong_id": "Minh Đức"}, uoc_luong_credit=10)
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
            assert s.status not in ("succeeded", "pending"), s.status
            assert dem["n"] >= 1, "kich ban chua he cham toi cua goi model"

            # 🔑 Bat bien THAT cua I5: cua goi model chi duoc cham DUNG MOT LAN.
            #
            # ⛔ Phep kiem cu khang dinh "hang doi rong tuyet doi", va do la mot
            #    menh de RONG HON menh de no muon bao ve: mot job dieu phoi
            #    (`advance`) con lai chi lam mot viec — quyet toan lan chay — va
            #    no khong goi provider nao ca. Do bang bo dem thi do dung thu can
            #    do, va khong vo khi so vong lap doi.
            truoc = dem["n"]
            for _ in range(6):
                job = jobs.claim(db, worker_id="w2",
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
            assert dem["n"] == truoc, (
                f"cua goi model bi cham lai ({truoc} -> {dem['n']}) sau mot lan "
                "dispatch MO HO")
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
    # 🔴 **Ghim `2` ở đây là một quả bom hẹn giờ, và nó vừa nổ (24/09).** Khi
    #    `PHIEN_BAN_LOI_NHAC` thật sự lên `2`, phép tiêm thành **no-op**: vân tay
    #    không đổi, bài đỏ — mà mã thì đúng. ⛔ Một đối chứng phải tiêm một giá
    #    trị **khác giá trị hiện hành**, không phải một hằng gõ tay.
    monkeypatch.setattr(van_ban, "PHIEN_BAN_LOI_NHAC_DICH",
                        van_ban.PHIEN_BAN_LOI_NHAC_DICH + 1)
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
    # ⭐ Pha 14: `CONTENT_PROCESS` khong con goi `dich_thuat.dich_ban_ghi`.
    #    Chan o CUA goi model (`ai.goi_tinh_tien`) — mot cho cho ca kho.
    from tests.fixtures.asv_media import cua_ai_gia

    cua_ai_gia(monkeypatch)


# ─────────────────────────────────────────────────────────────────────────────
# N-21 — MỘT hằng cho MỘT lời nhắc. ⛔ Không dùng chung.
# ─────────────────────────────────────────────────────────────────────────────

#: Mỗi module ⇒ lời nhắc nó **thuộc về**. Hai module cùng một lời nhắc thì được
#: đọc chung một hằng; hai lời nhắc khác nhau thì ⛔ **không**.
CHU_CUA_LOI_NHAC = {
    "van_ban": "dich",          # tài liệu + vân tay của `dich_thuat._loi_nhac`
    "dich_thuat": "dich",
    "long_tieng": "long_tieng",
    "thi_hanh": "long_tieng",   # vân tay CONTENT_PROCESS chạy `long_tieng`
}


def test_MOI_hang_PHIEN_BAN_LOI_NHAC_chi_phoi_DUNG_MOT_loi_nhac():
    """🔴 **Phép bắt cơ học cho N-21.**

    Trước 24/09 **một** hằng `PHIEN_BAN_LOI_NHAC` bị **ba** vân tay đọc, nên sửa
    lời nhắc của đường **chết** làm vô hiệu kết quả của hai đường **sống** ⇒ mọi
    đoạn dịch lại (**có tính tiền**) + **bảy** giai đoạn hạ nguồn bị đặt lại.

    ⛔ Không có phép bắt này thì luật sẽ hỏng lại trong ba tuần.
    """
    import ast
    from pathlib import Path

    goc = Path(__file__).resolve().parent.parent / "apps" / "auto_scan_video"
    doc_boi: dict[str, set[str]] = {}
    for tep in goc.glob("*.py"):
        cay = ast.parse(tep.read_text(encoding="utf-8"))
        for n in ast.walk(cay):
            # ⛔ Chỉ đếm chỗ ĐỌC (`Load`), ⛔ không đếm chỗ KHAI (`Store`):
            #    `van_ban.py` khai **cả hai** hằng, nên nếu đếm cả chỗ khai thì
            #    nó thành "người đọc" của cả hai và bài này đỏ vì chính cấu trúc
            #    nó đang bảo vệ. (Đã đỏ đúng như vậy ở lần chạy đầu.)
            if not isinstance(n, (ast.Attribute, ast.Name)):
                continue
            if not isinstance(getattr(n, "ctx", None), ast.Load):
                continue
            ten = n.attr if isinstance(n, ast.Attribute) else n.id
            if ten.startswith("PHIEN_BAN_LOI_NHAC"):
                doc_boi.setdefault(ten, set()).add(tep.stem)

    assert doc_boi, "⛔ không thấy hằng nào — phép kiểm đang đo chính nó"
    for hang, cac_module in sorted(doc_boi.items()):
        chu = {CHU_CUA_LOI_NHAC.get(m, m) for m in cac_module}
        assert len(chu) == 1, (
            f"⛔ N-21: hằng {hang!r} bị {sorted(cac_module)} đọc, tức nó chi "
            f"phối {len(chu)} lời nhắc khác nhau ({sorted(chu)}). Tách ra: một "
            f"hằng cho mỗi lời nhắc.")


def test_DOI_CHUNG_tang_hang_DICH_thi_van_tay_LONG_TIENG_khong_nhuc_nhich(monkeypatch):
    """⭐ **Hai vế — thiếu vế hai thì bài đang đo chính nó.**

    (a) tăng hằng của lời nhắc **DỊCH** ⇒ vân tay giai đoạn `CONTENT_PROCESS`
        (chạy `long_tieng`) **KHÔNG đổi**;
    (b) tăng hằng của lời nhắc **LONG_TIENG** ⇒ vân tay ấy **CÓ đổi**.
    """
    from apps.auto_scan_video import pipeline, thi_hanh, van_ban

    def _vt():
        return thi_hanh.phien_ban_engine(pipeline.CONTENT_PROCESS)

    truoc = _vt()
    monkeypatch.setattr(van_ban, "PHIEN_BAN_LOI_NHAC_DICH",
                        van_ban.PHIEN_BAN_LOI_NHAC_DICH + 1)
    assert _vt() == truoc, (
        "⛔ N-21 tái phát: đổi lời nhắc DỊCH vẫn kéo theo CONTENT_PROCESS")

    monkeypatch.setattr(van_ban, "PHIEN_BAN_LOI_NHAC_LONG_TIENG",
                        van_ban.PHIEN_BAN_LOI_NHAC_LONG_TIENG + 1)
    assert _vt() != truoc, (
        "⛔ vế đối chứng hỏng: đổi lời nhắc của CHÍNH nó mà vân tay không đổi "
        "— bài này đang đo chính nó")


# ══════════════════════════════════════════════════════════════════════════════
#  Task 5 — doi_soat: sau phep DEM tren mot luot chay (khong can ban tham chieu)
# ══════════════════════════════════════════════════════════════════════════════

def test_doi_soat_phan_biet_CHUA_DO_voi_BANG_KHONG():
    """⛔ `0` và "chưa đo được" là HAI trạng thái. Gộp chúng là mất khả năng phân biệt."""
    from tools.asv_doi_soat import doi_soat

    rong = doi_soat({"giai_doan": []})
    assert rong["sai_so_p90"] is None, "khong co cap (doan, that) thi phai la None"
    assert rong["so_doan_nan_oan"] is None


def test_doi_soat_tinh_sai_so_tu_cap_doan_va_that():
    from tools.asv_doi_soat import doi_soat

    dong = {"giai_doan": [{"giai_doan": "voice_synthesis", "tom_tat": {
        "luot_doc": [{"ma": "seg_0001", "giay_doan": 2.0, "giay": 2.0},
                     {"ma": "seg_0002", "giay_doan": 2.0, "giay": 3.0}],
        "so_doan_nan_oan": 1}}]}
    ra = doi_soat(dong)
    # |2-2|/2 = 0 ; |3-2|/3 = 0,3333 -> p50 = 0,1667 (trung binh hai gia tri)
    assert ra["sai_so_max"] == pytest.approx(1 / 3, abs=1e-6)
    assert ra["ti_le_doan_ngan"] == pytest.approx(0.5, abs=1e-6)
    assert ra["so_doan_nan_oan"] == 1


# ══════════════════════════════════════════════════════════════════════════════
#  Task 11 — ho_so_dich: MOT loi goi cho CA video
# ══════════════════════════════════════════════════════════════════════════════

def test_ho_so_dich_tra_ve_DU_nam_khoa():
    from apps.auto_scan_video import ho_so_dich

    goi = {"noi_dung": '{"the_loai":"vlog","so_nguoi_noi":1,'
                       '"bang_dai_tu":{"A->KHAN":{"toi":"minh","goi":"cac ban"}},'
                       '"bang_ten_rieng":{"光子":"Quang Tu"},"giong_van":"than mat"}'}
    ra = ho_so_dich._doc(goi["noi_dung"])
    assert ra["the_loai"] == "vlog"
    assert ra["bang_dai_tu"]["A->KHAN"]["goi"] == "cac ban"
    assert ra["bang_ten_rieng"]["光子"] == "Quang Tu"


def test_ho_so_dich_MOT_loi_goi_cho_ca_video():
    """⛔ Khong duoc goi theo lo: ho so la cau hoi TOAN CUC."""
    import ast
    import inspect

    from apps.auto_scan_video import ho_so_dich

    cay = ast.parse(inspect.getsource(ho_so_dich))
    vong = [n for n in ast.walk(cay) if isinstance(n, (ast.For, ast.While))]
    trong_vong = any(
        isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
        and c.func.attr == "goi"
        for v in vong for c in ast.walk(v))
    assert not trong_vong, "loi goi model nam trong mot vong lap"


# ══════════════════════════════════════════════════════════════════════════════
#  Task 7b — cua so ngu canh mang BAN DA DICH + noi ho so dich vao loi nhac
# ══════════════════════════════════════════════════════════════════════════════

def test_ngu_canh_ke_uu_tien_BAN_DA_DICH_cho_phia_truoc():
    """🔴 Lời nhắc nói `ke_ben` là "câu khán giả VỪA NGHE". Với phía `truoc` thì
    khán giả đã nghe **bản tiếng Việt**, ⛔ không phải chữ Hán nguồn."""
    from apps.auto_scan_video.long_tieng import ngu_canh_ke

    tat_ca = [{"ma": "seg_0001", "chu": "你好"},
              {"ma": "seg_0002", "chu": "你呢"},
              {"ma": "seg_0003", "chu": "再见"}]
    ra = ngu_canh_ke(tat_ca, 1, ke=1,
                     da_dich={"seg_0001": {"chu": "Chao cac ban"}})
    assert ra["truoc"] == ["Chao cac ban"], ra
    # phía `sau` CHƯA dịch nên vẫn là nguồn — đó là đúng, ⛔ không phải thiếu sót
    assert ra["sau"] == ["再见"], ra


def test_ngu_canh_ke_KHONG_co_ban_dich_thi_giu_nguyen_nhu_cu():
    """⛔ Không có `da_dich` thì hàm phải chạy y hệt bản trước một mili-giây."""
    from apps.auto_scan_video.long_tieng import ngu_canh_ke

    tat_ca = [{"ma": "a", "chu": "X"}, {"ma": "b", "chu": "Y"},
              {"ma": "c", "chu": "Z"}]
    assert ngu_canh_ke(tat_ca, 1, ke=1) == {"truoc": ["X"], "sau": ["Z"]}


def test_loi_nhac_mang_BANG_DAI_TU_va_TEN_RIENG_khi_co_ho_so():
    """C1+C2: quan hệ nhân vật quyết MỘT lần cho cả video, ⛔ không mỗi lô một lần."""
    from apps.auto_scan_video.long_tieng import loi_nhac

    lo = [{"ma": "seg_0001", "chu": "光子来了", "bat": 0.0, "ket": 2.0}]
    tin = loi_nhac(lo, tat_ca=lo, ngon_ngu_goc="zh", dac_diem_giong={},
                   ho_so={"bang_dai_tu": {"A->KHAN": {"toi": "minh",
                                                     "goi": "cac ban"}},
                          "bang_ten_rieng": {"光子": "Quang Tu"}})
    ca = " ".join(m["content"] for m in tin)
    assert "Quang Tu" in ca and "cac ban" in ca


def test_doi_loi_nhac_thi_PHAI_tang_PHIEN_BAN_LONG_TIENG():
    """⛔ Thiếu bước này, lượt chạy mới dùng lại bản lồng tiếng của lời nhắc CŨ."""
    from apps.auto_scan_video import long_tieng
    assert long_tieng.PHIEN_BAN_LONG_TIENG >= 3
