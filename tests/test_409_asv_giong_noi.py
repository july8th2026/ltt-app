"""Auto Scan Video — VOICE_SYNTHESIS: sinh tieng tung doan, phuc hoi tung doan.

Giai doan tra tien THU HAI, va la giai doan dau tien co **nhieu lan goi tra tien
trong mot lan chay**. Nen trong tam la: mot lan chay lai duoc phep goi lai bao
nhieu lan?

  §1 phan loai loi   — ban / mo ho / thuong
  §2 van tay muc doan
  §3 kiem tep tieng
  §4 phuc hoi tung doan   <- trong tam
  §5 quyen so huu giong
  §6 cong thoat
  §7 cho bang chung ngoai

⛔ Prompt 12 cam ghep/canh thoi gian trong lop provider.
"""
from __future__ import annotations

import subprocess
import wave
from pathlib import Path

import pytest

from tests.fixtures.asv_media import require_ffmpeg


def _wav(dich: Path, *, giay: float = 0.4) -> bytes:
    from platform_core import media
    require_ffmpeg()
    dich.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [media.ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", f"sine=frequency=440:duration={giay}",
         "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", str(dich)],
        check=True, capture_output=True)
    return dich.read_bytes()


# ══════════════════════════════════════════════════════════════════════════════
#  §1 Phan loai loi
# ══════════════════════════════════════════════════════════════════════════════

def test_BAN_khong_phai_HONG(monkeypatch):
    """🔴 `apps/ltt_voice/features.py:219` ghi thang bai hoc nay: boc
    `DangBanTam` thanh mot loi hong la bien "may dang ban" thanh "job hong", va
    mot job hong se **TRU CREDIT cho viec chua tung chay**.
    """
    from apps.auto_scan_video import giong_noi
    from apps.ltt_voice import features as vf

    def ban(chu, **kw):
        raise vf.DangBanTam(retry_after_s=3)

    monkeypatch.setattr(vf, "goi_cong", ban)
    with pytest.raises(giong_noi.MayBan):
        giong_noi.doc_mot_doan("xin chao")


def test_mat_ket_noi_thanh_GiongMoHo_khong_bao_gio_thu_lai(monkeypatch):
    """I5/G7 — may co the da sinh xong va da tinh tien."""
    from apps.auto_scan_video import giong_noi
    from apps.ltt_voice import features as vf

    class TimeoutError_(RuntimeError):
        pass
    TimeoutError_.__name__ = "ReadTimeout"

    monkeypatch.setattr(vf, "goi_cong",
                        lambda chu, **kw: (_ for _ in ()).throw(TimeoutError_("x")))
    with pytest.raises(giong_noi.GiongMoHo):
        giong_noi.doc_mot_doan("xin chao")


def test_loi_thuong_van_la_GiongError_thu_lai_duoc(monkeypatch):
    from apps.auto_scan_video import giong_noi
    from apps.ltt_voice import features as vf

    monkeypatch.setattr(vf, "goi_cong",
                        lambda chu, **kw: (_ for _ in ()).throw(ValueError("hong")))
    with pytest.raises(giong_noi.GiongError):
        giong_noi.doc_mot_doan("xin chao")


def test_doan_QUA_DAI_bi_tu_choi_chu_KHONG_tu_chia_nho():
    """⛔ Chia mot cau thoai thanh hai luot sinh la doi mot doan thanh HAI GIONG
    DOC khac nhau o giua cau.

    Tran 1.500 ky tu la tran CHAT LUONG cua `ltt_voice` (#168 bao troi giong tu
    ~3.000), khong phai mot con so ai cung duoc chinh.
    """
    from apps.auto_scan_video import giong_noi
    from apps.ltt_voice.tham_so_cong_khai import TRAN_MOI_LUOT_SINH

    with pytest.raises(giong_noi.GiongError) as loi:
        giong_noi.doc_mot_doan("a" * (TRAN_MOI_LUOT_SINH + 1))
    assert str(TRAN_MOI_LUOT_SINH) in str(loi.value)


def test_doan_RONG_bi_tu_choi():
    from apps.auto_scan_video import giong_noi

    with pytest.raises(giong_noi.GiongError):
        giong_noi.doc_mot_doan("   ")


# ══════════════════════════════════════════════════════════════════════════════
#  §2 Van tay muc DOAN
# ══════════════════════════════════════════════════════════════════════════════

def test_van_tay_o_muc_DOAN_doi_theo_noi_dung_va_giong():
    """Van tay muc doan la thu cho phep sinh lai **dung nhung doan con thieu**.

    Mot van tay o muc giai doan thi mot doan hong keo theo ca bai phai doc lai.
    """
    from apps.auto_scan_video import giong_noi

    goc = dict(ma_doan="seg_0001", chu="xin chao", voice_id="", preset="bac")
    nen = giong_noi.van_tay_doan(**goc)

    assert nen != giong_noi.van_tay_doan(**{**goc, "chu": "tam biet"})
    assert nen != giong_noi.van_tay_doan(**{**goc, "preset": "nam"})
    assert nen != giong_noi.van_tay_doan(**{**goc, "voice_id": "vc_abc"})
    assert nen != giong_noi.van_tay_doan(**{**goc, "ma_doan": "seg_0002"})


def test_van_tay_giong_nhau_thi_KHOA_giong_nhau():
    """Nen ghi lai la luy dang: mot lan chet giua chung ton cong sinh, khong ton
    tinh dung dan."""
    from apps.auto_scan_video import assets, giong_noi

    vt = giong_noi.van_tay_doan(ma_doan="seg_0001", chu="a", voice_id="",
                                preset="bac")
    k1 = assets.dat_khoa(owner_id="uA", run_id="r1", stage="voice_synthesis",
                         van_tay=vt, duoi="wav")
    k2 = assets.dat_khoa(owner_id="uA", run_id="r1", stage="voice_synthesis",
                         van_tay=vt, duoi="wav")
    assert k1 == k2


# ══════════════════════════════════════════════════════════════════════════════
#  §3 Kiem tep tieng
# ══════════════════════════════════════════════════════════════════════════════

def test_kiem_tep_tieng_do_tren_TEP_THAT(tmp_path):
    """Muc 8 — kiem TRUOC khi danh dau doan thanh cong."""
    from apps.auto_scan_video import giong_noi

    _wav(tmp_path / "a.wav", giay=0.5)
    assert giong_noi.kiem_tep_tieng(str(tmp_path / "a.wav")) == pytest.approx(
        0.5, abs=0.1)


def test_tep_tieng_QUA_NGAN_bi_tu_choi(tmp_path):
    """⛔ Mot WAV dung dinh dang nhung dai 0 giay se qua moi phep kiem ve dinh
    dang, roi TIMING dat mot khoang im vao dung cho do — va khong ai biet vi sao.
    """
    from apps.auto_scan_video import giong_noi

    rong = tmp_path / "rong.wav"
    with wave.open(str(rong), "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(24000)
        f.writeframes(b"")
    with pytest.raises(giong_noi.GiongError):
        giong_noi.kiem_tep_tieng(str(rong))


def test_tep_KHONG_PHAI_tieng_bi_tu_choi(tmp_path):
    from apps.auto_scan_video import giong_noi

    hong = tmp_path / "hong.wav"
    hong.write_bytes(b"day khong phai wav" * 40)
    with pytest.raises(Exception):
        giong_noi.kiem_tep_tieng(str(hong))


# ══════════════════════════════════════════════════════════════════════════════
#  §4 Phuc hoi tung doan — TRONG TAM
# ══════════════════════════════════════════════════════════════════════════════

class TestPhucHoiTungDoan:
    """Muc 7 + cong thoat: *"resumable at the smallest safe granularity"*.

    Hat nho nhat AN TOAN la mot doan. Hat nho hon (chia mot cau thanh hai luot)
    khong an toan — no doi mot doan thanh hai giong doc khac nhau o giua cau.
    """

    def _dung_moi_truong(self, tmp_path, monkeypatch, *, so_doan=3):
        """Mot run da xong toi CONTENT, san sang cho VOICE."""
        import json

        import platform_core.db as dbmod
        from platform_core import credit
        from platform_core.storage import LocalStorage, set_storage
        from tests.conftest import bao_dam_user
        from tests.fixtures.asv_media import ban_ghi_gia, nap_nguon_vao_kho

        monkeypatch.setenv("LTT_DATABASE_URL",
                           f"sqlite:///{(tmp_path / 'v.db').as_posix()}")
        dbmod.reset_engine()
        import platform_core.models  # noqa: F401
        from platform_core.registry import load_app_tables
        load_app_tables()
        dbmod.Base.metadata.create_all(dbmod.get_engine())
        db = next(dbmod.get_session())
        kho = LocalStorage(str(tmp_path / "kho")); set_storage(kho)

        from apps.auto_scan_video import (assets, ban_ghi, features, pipeline,
                                          van_ban)

        bao_dam_user(db, "uA"); credit.nap(db, "uA", 1000)
        khoa_nguon = nap_nguon_vao_kho(kho, tmp_path, owner_id="uA")
        run = features.tao_run(db, owner_id="uA", source_key=khoa_nguon,
                               settings={"preset": "bac"}, uoc_luong_credit=50)
        db.commit()

        goc = ban_ghi.chuan_hoa(ban_ghi_gia(float(so_doan)),
                                thoi_luong_nguon=60.0)
        tl = van_ban.dung(goc, {d["ma"]: f"dich {d['ma']}" for d in goc["doan"]},
                          provider="p", model="m")
        goi = json.dumps(tl, sort_keys=True, ensure_ascii=False).encode("utf-8")
        tam = assets.khoa_staging(owner_id="uA", run_id=run.id,
                                  stage=pipeline.CONTENT_PROCESS,
                                  van_tay="vt", duoi="json")
        import io
        kho.put(tam, io.BytesIO(goi), content_type="application/json")
        a = assets.promote_va_ghi(db, kho, owner_id="uA", run_id=run.id,
                                  stage=pipeline.CONTENT_PROCESS, van_tay="vt",
                                  kind="json", duoi="json", staging_key=tam)
        s = features.giai_doan_theo_ten(db, run.id, pipeline.CONTENT_PROCESS)
        features.danh_dau_xong(db, s, outputs={"khoa_asset": [a.storage_key]},
                               fingerprint="vt")
        db.commit()
        return db, kho, run

    def _gan_may_sinh_tieng(self, monkeypatch, tmp_path, dem):
        """May sinh tieng gia. Dem so lan goi that su."""
        from apps.auto_scan_video import giong_noi

        monkeypatch.setattr(giong_noi, "san_sang", lambda: True)
        monkeypatch.setattr(giong_noi, "giai_giong",
                            lambda db, **kw: (None, "bac"))

        # `**_`: ban gia nay do SO LAN GOI, khong do tham so. Liet ke tung
        # tham so se bat no phai doi moi lan chu ky that moc them mot tuy
        # chon khong lien quan — va lan nao cung la mot lan do do vi mot
        # ly do khac voi ly do no ton tai.
        def doc(chu, *, ref_b64=None, preset=None, **_):
            dem.append(chu)
            return _wav(tmp_path / f"g{len(dem)}.wav", giay=0.4), {}

        monkeypatch.setattr(giong_noi, "doc_mot_doan", doc)

    def test_chay_lai_KHONG_sinh_lai_doan_da_co(self, tmp_path, monkeypatch):
        """🔑 Bat bien trung tam cua pha nay.

        Doan da co artifact **con song va con dung** thi khong duoc goi lai —
        moi lan goi lai la mot lan tra tien cho mot thu da co.
        """
        from apps.auto_scan_video import giai_doan_giong, giong_noi

        db, kho, run = self._dung_moi_truong(tmp_path, monkeypatch, so_doan=3)
        dem: list = []
        self._gan_may_sinh_tieng(monkeypatch, tmp_path, dem)

        # Luot 1: sinh ca ba, roi promote nhu than thi hanh van lam.
        ra1 = giai_doan_giong.chay(db, kho, run=run)
        assert ra1["tom_tat"]["so_doan_moi_sinh"] == 3
        assert len(dem) == 3

        from apps.auto_scan_video import assets, pipeline
        for phan in ra1["phan"]:
            assets.promote_va_ghi(
                db, kho, owner_id="uA", run_id=run.id,
                stage=pipeline.VOICE_SYNTHESIS, van_tay=phan["van_tay"],
                kind=phan["kind"], duoi=phan["duoi"],
                staging_key=phan["staging_key"])
        db.commit()

        # Luot 2: khong doan nao duoc goi lai.
        dem.clear()
        ra2 = giai_doan_giong.chay(db, kho, run=run)
        assert dem == [], f"da goi lai {len(dem)} doan da co san"
        assert ra2["tom_tat"]["so_doan_moi_sinh"] == 0
        assert ra2["tom_tat"]["so_doan_dung_lai"] == 3
        db.close()

    def test_chi_sinh_lai_doan_bi_MAT(self, tmp_path, monkeypatch):
        """Muc 7 — thanh cong mot phan phai checkpoint duoc.

        Xoa MOT tep roi chay lai: dung mot doan duoc sinh, hai doan kia giu nguyen.
        """
        from apps.auto_scan_video import assets, giai_doan_giong, pipeline

        db, kho, run = self._dung_moi_truong(tmp_path, monkeypatch, so_doan=3)
        dem: list = []
        self._gan_may_sinh_tieng(monkeypatch, tmp_path, dem)

        ra1 = giai_doan_giong.chay(db, kho, run=run)
        wav_phan = [p for p in ra1["phan"] if p["kind"] == "audio"]
        for phan in ra1["phan"]:
            assets.promote_va_ghi(
                db, kho, owner_id="uA", run_id=run.id,
                stage=pipeline.VOICE_SYNTHESIS, van_tay=phan["van_tay"],
                kind=phan["kind"], duoi=phan["duoi"],
                staging_key=phan["staging_key"])
        db.commit()

        # Xoa tep cua doan dau — ban ghi con, tep mat.
        mat = assets.dat_khoa(owner_id="uA", run_id=run.id,
                              stage=pipeline.VOICE_SYNTHESIS,
                              van_tay=wav_phan[0]["van_tay"], duoi="wav")
        kho.delete(mat)

        dem.clear()
        ra2 = giai_doan_giong.chay(db, kho, run=run)
        assert len(dem) == 1, f"phai sinh lai DUNG mot doan, da sinh {len(dem)}"
        assert ra2["tom_tat"]["so_doan_moi_sinh"] == 1
        assert ra2["tom_tat"]["so_doan_dung_lai"] == 2
        db.close()

    def test_MOT_tep_cho_MOI_doan(self, tmp_path, monkeypatch):
        """TIMING dat tung doan vao khe cua no. Mot tep lien mach thi khong con
        cho de dat — va mot doan sua se bat ca bai doc lai."""
        from apps.auto_scan_video import giai_doan_giong

        db, kho, run = self._dung_moi_truong(tmp_path, monkeypatch, so_doan=4)
        self._gan_may_sinh_tieng(monkeypatch, tmp_path, [])

        ra = giai_doan_giong.chay(db, kho, run=run)
        wav = [p for p in ra["phan"] if p["kind"] == "audio"]
        assert len(wav) == 4
        assert len({p["van_tay"] for p in wav}) == 4, "bon doan phai bon van tay"
        db.close()

    def test_co_ban_ke_de_TIMING_biet_doan_nao_o_dau(self, tmp_path, monkeypatch):
        from apps.auto_scan_video import giai_doan_giong

        db, kho, run = self._dung_moi_truong(tmp_path, monkeypatch, so_doan=2)
        self._gan_may_sinh_tieng(monkeypatch, tmp_path, [])

        ra = giai_doan_giong.chay(db, kho, run=run)
        ke = [p for p in ra["phan"] if p["kind"] == "json"]
        assert len(ke) == 1, "phai co dung mot ban ke"

        import json
        with kho.open(ke[0]["staging_key"]) as f:
            noi_dung = json.loads(f.read())
        assert [d["ma"] for d in noi_dung["doan"]] == ["seg_0001", "seg_0002"]
        assert all(d["giay"] > 0 for d in noi_dung["doan"])
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
#  §5 Quyen so huu giong
# ══════════════════════════════════════════════════════════════════════════════

def test_giai_giong_la_NOI_DUY_NHAT_kiem_quyen_so_huu(monkeypatch):
    """🔴 Docstring cua `apps/ltt_voice/features.giai_giong` ghi: *"Day la cho
    quyen so huu duoc kiem, va no la cho duy nhat."*

    Goi `goi_cong` ma khong qua no la mo mot duong dung giong cua nguoi khac —
    dung bat bien I6/I7 ma ADR-002 vua dong.
    """
    from apps.auto_scan_video import giong_noi

    bat = {}
    # `giai_giong` that tra ve BA thu: `(ref_b64, preset, canh_bao)`. Ban dau
    # cho nay tra hai, va phep kiem do voi `ValueError` — dung, va la mot loi
    # cua PHEP KIEM chu khong cua ma. Mot stub sai arity la mot stub dang kiem
    # mot hop dong khac voi hop dong that.
    monkeypatch.setattr("apps.ltt_voice.features.giai_giong",
                        lambda db, yc: bat.update(owner=yc.owner_id,
                                                  voice=yc.voice_id)
                        or (None, "bac", None))
    giong_noi.giai_giong(None, owner_id="uA", voice_id="vc_x")
    assert bat["owner"] == "uA", "owner_id khong toi duoc phep kiem quyen"
    assert bat["voice"] == "vc_x"


def test_be_mat_lien_app_khai_o_CA_HAI_phia():
    """Hop dong app doi hai ban khai khop nhau chinh xac.

    ⭐ `ltt_voice` KHONG bi sua dong logic nao — chi them mot ban khai.
    """
    import apps.ltt_voice as voice
    from tools.lint_app_contract import APP_DUOC_DUNG_APP

    can = ("apps.ltt_voice.features", "giai_giong")
    assert can in voice.BE_MAT_CONG_KHAI
    assert can in APP_DUOC_DUNG_APP[("auto_scan_video", "ltt_voice")]


def test_KHONG_truyen_temperature_top_k_top_p():
    """⛔ Chung khong ra hop dong cong khai cua `ltt_voice`: cache CUDA graph cua
    no khoa theo `(B, temp, top_k, top_p)` (CLAUDE.md). Truyen vao la lam vo
    cache cua mot app khac."""
    import inspect

    from apps.auto_scan_video import giai_doan_giong, giong_noi
    from tests.test_401_asv_ranh_gioi_va_artifact import _vi_pham

    for mod in (giong_noi, giai_doan_giong):
        ma = inspect.getsource(mod)
        assert _vi_pham(ma, ("temperature", "top_k", "top_p")) == [], mod.__name__


def test_KHONG_ghep_thoi_gian_trong_lop_provider():
    """⛔ Prompt 12 cam ro. Ghep la viec cua TIMING_ALIGN (pha 13); tron vao day
    la giau mot quyet dinh timing ben trong mot lop provider — noi khong ai di
    tim no."""
    import inspect

    from apps.auto_scan_video import giai_doan_giong, giong_noi
    from tests.test_401_asv_ranh_gioi_va_artifact import _vi_pham

    for mod in (giong_noi, giai_doan_giong):
        ma = inspect.getsource(mod)
        assert _vi_pham(ma, ("concat", "amix", "adelay", "apad")) == [], (
            f"{mod.__name__} co dau hieu ghep tieng")


# ══════════════════════════════════════════════════════════════════════════════
#  §6 Cong thoat
# ══════════════════════════════════════════════════════════════════════════════

def test_cong_thoat_VOICE_chay_o_lan_voice(tmp_path, monkeypatch):
    """Dinh tuyen: giai doan phai roi vao app khai `requires=("voice",)`.

    🔴 Khai sai o day hong **im lang**: `apps/ltt_voice/manifest.py:112` ghi lai
       rang neu `LTT_WORKER_POOLS` thieu lan `voice` thi job nam `queued` mai
       mai, khong loi nao bao.
    """
    from platform_core.registry import discover, job_type_owners
    from apps.auto_scan_video import pipeline

    g = pipeline.THEO_TEN[pipeline.VOICE_SYNTHESIS]
    assert g.app_slug == "asv_voice"
    assert job_type_owners().get(g.job_type) == "asv_voice"

    apps_ = {a.slug: a for a in discover()}
    assert apps_["asv_voice"].manifest.requires == ("voice",)
    assert apps_["asv_voice"].manifest.catalog_parent == "auto_scan_video"
    assert apps_["asv_voice"].manifest.surface == "runtime"


def test_lan_ffmpeg_KHONG_nhat_duoc_job_VOICE(tmp_path, monkeypatch):
    """Do bang hang doi that, khong bang doc manifest."""
    import platform_core.db as dbmod
    from platform_core import credit, jobs
    from tests.conftest import bao_dam_user

    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'r.db').as_posix()}")
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    try:
        bao_dam_user(db, "uA"); credit.nap(db, "uA", 100)
        jobs.submit(db, user_id="uA", app_slug="asv_voice",
                    job_type="asv_voice.voice_synthesis", params={})
        db.commit()

        assert jobs.claim(db, worker_id="w", capabilities={"ffmpeg"}) is None
        assert jobs.claim(db, worker_id="w", capabilities={"gpu"}) is None
        co = jobs.claim(db, worker_id="w", capabilities={"voice"})
        assert co is not None and co.app_slug == "asv_voice"
    finally:
        db.close(); dbmod.reset_engine()


# ══════════════════════════════════════════════════════════════════════════════
#  §7 Cho bang chung ngoai
# ══════════════════════════════════════════════════════════════════════════════

class TestChoBangChungNgoai:
    """Nhung thu may nay khong chung minh duoc."""

    def test_chua_goi_may_sinh_tieng_THAT_lan_nao(self):
        """⛔ Moi phep kiem o day dung mot may sinh tieng gia.

        Goi that can dich vu `LTTStudioVoice` song sau loopback :8120 va mot
        `LTT_VOICE_SIDECAR_TOKEN` hop le — mot phu thuoc ngoai ma bo test khong
        duoc phep doi hoi.

        ⇒ **Chat luong giong, do dai tieng Viet so voi khe thoi gian (RISK-02-01),
          va hanh vi that khi may ban deu CHUA DUOC DO.** Pha 13 se can chinh so
          do dai do, nen day la mot mon no co han.
        """
        from apps.auto_scan_video import giong_noi

        assert giong_noi.san_sang() is False, (
            "May sinh tieng da san sang — hay chay mot smoke THAT: sinh vai "
            "doan, do do dai thuc te so voi khe thoi gian cua chung, roi cap "
            "nhat RISK-02-01 va xoa phep kiem nay.")


# ══════════════════════════════════════════════════════════════════════════════
#  §8 Chuẩn hoá văn bản — lỗ đã có thật trong bản đầu của pha 12
# ══════════════════════════════════════════════════════════════════════════════

class TestChuanHoaVanBan:
    """🔴 Bản đầu của `doc_mot_doan` gọi thẳng `goi_cong(chu)` với **bản dịch
    thô** của model, bỏ qua hoàn toàn `text_pipeline.chuan_hoa`.

    Hậu quả không nhỏ: ngày tháng đọc thành chuỗi ký tự, URL đọc từng chữ cái,
    viết tắt đọc từng chữ cái, ký tự vô hình thành **token lạ (OOV)** cho
    tokenizer, và tên riêng không được từ điển sửa.

    ⭐ Lỗ này lộ ra vì một phiên khác cảnh báo về một phần **nhỏ hơn** của cùng
       vấn đề (`tu_dien_rieng` mới thêm). Phần lớn lỗ đã hỏng từ trước đó.
    """

    def test_van_ban_duoc_CHUAN_HOA_truoc_khi_doc(self, monkeypatch):
        """Bằng chứng trực tiếp: thứ tới máy sinh tiếng KHÁC bản dịch thô."""
        from apps.auto_scan_video import giong_noi
        from apps.ltt_voice import features as vf

        nhan = {}
        monkeypatch.setattr(vf, "goi_cong",
                            lambda chu, **kw: nhan.update(chu=chu) or (b"x", {}))

        giong_noi.doc_mot_doan("Xem tai https://vidu.vn nhe")
        assert "https" not in nhan["chu"], "URL chua duoc chuan hoa"
        assert "duong dan" in nhan["chu"] or "đường dẫn" in nhan["chu"]

    def test_ky_tu_VO_HINH_bi_xoa_truoc_khi_toi_tokenizer(self, monkeypatch):
        """⛔ Ký tự vô hình biến một chuỗi thành **token lạ** cho tokenizer —
        đúng loại lỗi phát âm khó truy nhất."""
        from apps.auto_scan_video import giong_noi
        from apps.ltt_voice import features as vf

        nhan = {}
        monkeypatch.setattr(vf, "goi_cong",
                            lambda chu, **kw: nhan.update(chu=chu) or (b"x", {}))

        giong_noi.doc_mot_doan("xin\u200bchao")
        assert "\u200b" not in nhan["chu"]

    def test_do_do_dai_SAU_khi_chuan_hoa_chu_khong_truoc(self):
        """⚠️ Chuẩn hoá có thể làm văn bản **dài ra**. Đo trước rồi chuẩn hoá
        sau là đo nhầm cái sẽ không được đọc."""
        import inspect

        from apps.auto_scan_video import giong_noi

        ma = inspect.getsource(giong_noi.doc_mot_doan)
        assert ma.index("chuan_hoa_van_ban") < ma.index("TRAN_MOI_LUOT_SINH", ma.index("chuan_hoa_van_ban")), (
            "do do dai truoc khi chuan hoa")

    def test_KHONG_dung_chuan_bi_van_ban_vi_no_CHIA_DOAN(self):
        """⛔ `features.chuan_bi_van_ban` vừa chuẩn hoá **vừa chia đoạn**, và
        chia một câu thoại thành hai lượt sinh là đổi nó thành hai giọng đọc
        khác nhau ở giữa câu (D-12-03). Ta chỉ lấy phần chuẩn hoá."""
        import inspect

        from apps.auto_scan_video import giai_doan_giong, giong_noi
        from tests.test_401_asv_ranh_gioi_va_artifact import _vi_pham

        for mod in (giong_noi, giai_doan_giong):
            assert _vi_pham(inspect.getsource(mod),
                            ("chuan_bi_van_ban", "chuan_bi")) == [], mod.__name__

    def test_tu_dien_rieng_di_duoc_toi_phep_chuan_hoa(self):
        """Đường dẫn tham số đã sẵn sàng cho từ điển phát âm của chủ sở hữu.

        ⚠️ **Chưa nối nguồn.** Module tra từ điển riêng theo chủ sở hữu được
        thêm ở lane `ltt_voice` **sau** khi worktree này ghim ở `c31b1ae`, nên
        nó chưa tồn tại ở đây. Phép kiểm này chốt rằng tham số đi lọt tới phép
        chuẩn hoá; việc nối nguồn là việc của bước merge.

        🔴 Vì sao quan trọng: nếu Auto Scan không truyền từ điển của chủ sở hữu
           thì bản lồng tiếng đọc tên riêng **khác** với bản khách nghe ở Studio
           — đúng lớp lỗi "một cửa có, cửa kia không".
        """
        from apps.auto_scan_video import giong_noi

        goc = giong_noi.chuan_hoa_van_ban("Anh Khoa")
        voi = giong_noi.chuan_hoa_van_ban("Anh Khoa",
                                          tu_dien_rieng={"Khoa": "Khua"})
        assert voi != goc, "tu dien rieng khong toi duoc phep chuan hoa"
        assert "Khua" in voi
