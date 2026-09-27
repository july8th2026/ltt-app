"""Task 25 — BAT BIEN O BIEN cua may sinh tieng, va LY DO HONG doc duoc.

## Vi sao bai nay ton tai — do duoc 27/09/2026, khong phai mot lo ngai

`test_448::test_G17_hai_preset_tren_PHIM_KHACH_THAT` chet **bon lan** (2 preset
x 2 phim), moi lan sau **3** lan thu, o dung mot cho:

    voice_synthesis  failed_terminal  thu=3  "Tep tieng sinh ra qua ngan (0.0s)."

Doc CSDL + kho tep cua chinh bon luot ay (`pytest-15006/test_G17_…_0`):

  * `content_process` cua ca bon: **0** doan rong (95, 95, 80, 80 doan) —
    gia thuyet "mot doan `chu` rong" SAI;
  * 12 tep `tieng/sapi_*.wav` (4 luot x 3 lan thu) **deu 0,000 giay** ⇒ chet o
    doan DAU moi lan, khong phai mot doan le trong 95;
  * `chu` cua `seg_0001` la `'这才是让人羡慕的生活。'` — chu TRUNG **nguyen van**,
    trong khi `ngon_ngu_dich = "vi"`.

⇒ Ban dich khong he dich. Va do tren chinh bo thay the SAPI:

    '这才是让人羡慕的生活。'  ->  46 byte / 0,000 giay
    ''                      ->  46 byte / 0,000 giay      <- Y HET
    'Chao buoi sang…'       -> 103.648 byte / 2,349 giay

**Mot chu KHONG dich va mot chu RONG cho ra cung mot tep**, nen thong bao
"tep tieng qua ngan" chi tay vao may sinh tieng trong khi loi o THUONG NGUON.
Do la thu bai nay chot: loi phai **goi ten doan** (`ma`) va noi chu den tu dau.

## Bon menh de, va vi sao khong bo cai nao

  §1 chu RONG sau chuan hoa  -> ⛔ khong goi may sinh tieng, doan duoc GOI TEN,
                                giu khoang lang dung do dai khe (quyet dinh
                                san pham — xem `giai_doan_giong._DOAN_IM_LANG`)
  §2 tep ngan tu chu KHONG rong -> loi goi ten `ma` + so ky tu, khong de
                                nguyen cau "tep qua ngan"
  §3 ban dich con he chu NGUON  -> chan TRUOC khi ton mot giay GPU, va la that
                                bai CUOI CUNG (thu lai 3 lan la lang phi:
                                deterministic — da do 12 lan hom nay)
  §4 `vi_sao_hong` cua mot luot hong ⛔ khong bao gio duoc rong im lang

⚠️ §3 co **doi chung** (`test_mot_chu_HAN_le_trong_cau_Viet_KHONG_bi_chan`):
   khong doi chung thi mot cua chan "moi thu" cung xanh.
"""
from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.asv_media import require_ffmpeg

#: Cau Trung THAT cua `seg_0001`, phim `暴雨天野外露营…` — chinh cau da lam
#: `voice_synthesis` chet 12 lan. ⛔ Khong bia mot cau khac: bai nay chot dung
#: du lieu da gay ra su co.
CAU_TRUNG_THAT = "这才是让人羡慕的生活。"

#: Ky tu VO HINH — `van_ban.kiem` cho qua (`str.split()` khong tach `U+200B`)
#: nhung `text_pipeline.chuan_hoa` xoa het ⇒ day la duong THAT dan toi mot
#: luot goi may sinh tieng voi chu rong. ⛔ Khong phai mot ca bia ra.
CHU_VO_HINH = "​‌﻿"


def _wav(dich: Path, *, giay: float = 0.4) -> bytes:
    """Mot WAV THAT dai `giay`. `giay=0` cho ra tep 0,0 giay hop le dinh dang."""
    from platform_core import media
    require_ffmpeg()
    dich.parent.mkdir(parents=True, exist_ok=True)
    if giay <= 0:
        # ffmpeg khong sinh duoc `duration=0`; ghi tay mot WAV 0 khung — dung
        # thu SAPI tra ve (46 byte, co luong tieng, 0,000 giay).
        import wave
        with wave.open(str(dich), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(b"")
        return dich.read_bytes()
    subprocess.run(
        [media.ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", f"sine=frequency=440:duration={giay}",
         "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", str(dich)],
        check=True, capture_output=True)
    return dich.read_bytes()


# ══════════════════════════════════════════════════════════════════════════════
#  Khung: mot run da xong toi CONTENT, voi ban long tieng TU CHON
# ══════════════════════════════════════════════════════════════════════════════

def _dung_moi_truong(tmp_path, monkeypatch, *, cau: dict[str, str] | None = None,
                     so_doan: int = 3, ngon_ngu_dich: str = "vi"):
    """Run san sang cho VOICE. `cau` = `{ma_doan: chu}` de ghi de ban dich.

    ⭐ Khuon nay di theo `test_409::TestPhucHoiTungDoan._dung_moi_truong` —
       ⛔ khong phai mot khung thu hai: no chi them mot tham so (`cau`), vi bai
       nay can dat mot `chu` DAC BIET vao dung mot doan.
    """
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

    goc = ban_ghi.chuan_hoa(ban_ghi_gia(float(so_doan)), thoi_luong_nguon=60.0)
    bang = {d["ma"]: f"dich {d['ma']}" for d in goc["doan"]}
    bang.update(cau or {})
    tl = van_ban.dung(goc, bang, provider="p", model="m")
    tl["ma_giong"] = "mau:gia"
    tl["ngon_ngu_dich"] = ngon_ngu_dich

    # ⭐ `van_ban.kiem` chay o `_doc_ban_dich` — neu mot `chu` khong lot qua duoc
    #    no thi ca bai duoi day noi ve mot duong KHONG TON TAI. Kiem o day de
    #    cho hong hien ra ngay tai khung, khong an vao mot assert xa hon.
    van_ban.kiem(tl)

    goi = json.dumps(tl, sort_keys=True, ensure_ascii=False).encode("utf-8")
    tam = assets.khoa_staging(owner_id="uA", run_id=run.id,
                              stage=pipeline.CONTENT_PROCESS,
                              van_tay="vt", duoi="json")
    kho.put(tam, io.BytesIO(goi), content_type="application/json")
    a = assets.promote_va_ghi(db, kho, owner_id="uA", run_id=run.id,
                              stage=pipeline.CONTENT_PROCESS, van_tay="vt",
                              kind="json", duoi="json", staging_key=tam)
    s = features.giai_doan_theo_ten(db, run.id, pipeline.CONTENT_PROCESS)
    features.danh_dau_xong(db, s, outputs={"khoa_asset": [a.storage_key]},
                           fingerprint="vt")
    db.commit()
    return db, kho, run


def _gan_may_sinh_tieng(monkeypatch, tmp_path, dem, *, giay: float = 0.4):
    """May sinh tieng gia. `dem` nhan MOI chu that su di toi may."""
    from apps.auto_scan_video import giong_noi

    monkeypatch.setattr(giong_noi, "san_sang", lambda: True)
    monkeypatch.setattr(giong_noi, "giai_giong", lambda db, **kw: (None, "bac"))

    def doc(chu, *, ref_b64=None, preset=None, **_):
        dem.append(chu)
        return _wav(tmp_path / f"g{len(dem)}.wav", giay=giay), {}

    monkeypatch.setattr(giong_noi, "doc_mot_doan", doc)


# ══════════════════════════════════════════════════════════════════════════════
#  §1 Chu RONG sau chuan hoa — ⛔ khong goi may sinh tieng, GOI TEN doan
# ══════════════════════════════════════════════════════════════════════════════

class TestChuRongKhongToiMaySinhTieng:

    def test_ky_tu_VO_HINH_lot_qua_van_ban_kiem_nhung_chuan_hoa_xoa_het(self):
        """Duong THAT dan toi mot luot goi voi chu rong — do, dung suy.

        ⛔ Khong co menh de nay thi §1 la mot cua chan cho mot ca ⛔ khong bao
           gio xay ra (`van_ban.kiem:180` da chan `chu` rong), tuc ma phong thu
           mua su yen tam bang tin dung gia.
        """
        from apps.auto_scan_video import van_ban
        from apps.ltt_voice import text_pipeline

        assert van_ban._sach(CHU_VO_HINH), \
            "U+200B khong con lot qua `van_ban._sach` — §1 doi duong khac"
        assert not text_pipeline.chuan_hoa(CHU_VO_HINH).strip(), \
            "`chuan_hoa` khong con xoa ky tu vo hinh"

    def test_chu_se_doc_la_MOT_ban_luat_voi_doc_mot_doan(self, monkeypatch):
        """`chu_se_doc` phai la CHINH phep chuan hoa `doc_mot_doan` dung.

        🔴 Hai ban cua mot luat la hai ban se lech nhau: mot cua chan doc "co
           chu khong" bang mot phep, roi may sinh tieng nhan mot phep khac, thi
           cua chan bao "co" cho dung cai se thanh rong.

        ⭐ Ban gia cua `goi_cong` o day **nem neu bi goi** — no vua lam vui long
           bánh cóc `test_428` (⛔ khong goi engine nang khong rao chan) vua lam
           menh de MANH HON: no chung minh engine ⛔ khong bao gio bi cham toi,
           chu khong chi rang co mot ngoai le duoc nem ra.
        """
        from apps.auto_scan_video import giong_noi
        from apps.ltt_voice import features as vf

        def chan(*a, **kw):
            raise AssertionError("da goi may sinh tieng voi chu rong")

        monkeypatch.setattr(vf, "goi_cong", chan)

        assert hasattr(giong_noi, "chu_se_doc")
        for mau in (CHU_VO_HINH, "  ", "Chao moi nguoi.", "...", CAU_TRUNG_THAT):
            ra = giong_noi.chu_se_doc(mau)
            if not ra:
                with pytest.raises(giong_noi.GiongError):
                    giong_noi.doc_mot_doan(mau)

    def test_doan_vo_hinh_KHONG_toi_may_sinh_tieng_va_duoc_GOI_TEN(
            self, tmp_path, monkeypatch):
        """Bat bien cung cua Task 25: ⛔ khong goi may sinh tieng voi chu rong."""
        from apps.auto_scan_video import giai_doan_giong

        db, kho, run = _dung_moi_truong(
            tmp_path, monkeypatch, so_doan=3, cau={"seg_0002": CHU_VO_HINH})
        dem: list = []
        _gan_may_sinh_tieng(monkeypatch, tmp_path, dem)

        ra = giai_doan_giong.chay(db, kho, run=run)

        assert all(str(c).strip() for c in dem), \
            f"da goi may sinh tieng voi chu rong: {[repr(c) for c in dem]}"
        tt = ra["tom_tat"]
        assert tt.get("so_doan_im_lang") == 1, \
            f"phai DEM duoc doan im lang, tom_tat = {tt.get('so_doan_im_lang')!r}"
        assert "seg_0002" in (tt.get("doan_im_lang") or []), \
            f"phai GOI TEN doan im lang, co: {tt.get('doan_im_lang')!r}"
        db.close()

    def test_doan_im_lang_van_co_ban_ke_de_TIMING_khong_chet(
            self, tmp_path, monkeypatch):
        """Quyet dinh "bo qua" phai giu duoc thuong tang.

        🔴 `thoi_gian.lap_ke_hoach` NEM `Doan {ma} chua co tieng` cho moi `ma`
           thieu dong `ban_ke`. Nen "bo qua" ⛔ khong duoc nghia la "khong ghi
           gi" — no la mot khoang lang dung do dai khe.
        """
        from apps.auto_scan_video import giai_doan_giong, nan_thoi_luong

        db, kho, run = _dung_moi_truong(
            tmp_path, monkeypatch, so_doan=3, cau={"seg_0002": CHU_VO_HINH})
        _gan_may_sinh_tieng(monkeypatch, tmp_path, [])

        ra = giai_doan_giong.chay(db, kho, run=run)
        khoa_ke = [p for p in ra["phan"] if p["kind"] == "json"]
        assert khoa_ke, "khong co ban ke"
        with kho.open(khoa_ke[0]["staging_key"]) as f:
            ban_ke = json.loads(f.read().decode("utf-8"))
        ma_co = {str(d["ma"]) for d in ban_ke["doan"]}
        assert "seg_0002" in ma_co, \
            f"doan im lang mat dong ban_ke ⇒ TIMING se chet; co: {sorted(ma_co)}"
        dong = next(d for d in ban_ke["doan"] if str(d["ma"]) == "seg_0002")
        assert float(dong["giay"]) > 0, "khoang lang phai co do dai THAT"
        assert dong.get("im_lang") is True, \
            "dong ban_ke phai KHAI la khoang lang, khong im lang giong tieng that"
        assert nan_thoi_luong is not None
        db.close()

    def test_co_im_lang_duoc_TIEU_THU_o_qc_do_luong(self):
        """🔴 Mot co ⛔ khong ai doc la mot co ⛔ khong ton tai.

        `giai_doan_qc_do_luong` ASR tung doan roi cham WER voi `chu`. Voi doan
        im lang, `chu` **⛔ khong rong** (no la chuoi goc, vd toan ky tu vo hinh)
        nen phep `if not chu: continue` ⛔ khong loc duoc no ⇒ ASR nghe mot
        khoang lang, `wer ≈ 1.0`, `sua_chua.giong_khong_dat` danh dau, va **vong
        sua chay cho mot doan ⛔ khong co gi de doc**.

        ⇒ Quyet dinh "bo qua" (muc (d) bao cao Task 25) chi dung khi co nay duoc
          TIEU THU o day. ⛔ Khong co phep kiem nay thi bo qua bien thanh mot
          vong lap tra tien GPU, va ⛔ khong bao cao nao bat duoc.
        """
        import ast
        import inspect
        import textwrap

        from apps.auto_scan_video import giai_doan_qc_do_luong, nan_thoi_luong

        # ── (1) Phep vi tu: do HANH VI, ⛔ khong do cach go ─────────────────
        assert nan_thoi_luong.la_dong_im_lang({"im_lang": True}) is True
        assert nan_thoi_luong.la_dong_im_lang({"chu": "co chu"}) is False
        assert nan_thoi_luong.la_dong_im_lang({}) is False
        assert nan_thoi_luong.la_dong_im_lang(None) is False

        # ── (2) Va `qc_do_luong` phai GOI no ───────────────────────────────
        #
        # ⛔ Doc AST, ⛔ khong `in` tren chuoi: mot chu thich mang ten ham cung
        #    lot. Va tim mot LOI GOI TEN HAM chu khong mot vi tri chuoi — mot
        #    loi goi ben vung qua moi lan doi cach go, con vi tri chuoi thi
        #    khong (bai hoc `test_409`, cung phien nay).
        than = textwrap.dedent(inspect.getsource(giai_doan_qc_do_luong.chay))
        goi = {
            n.func.attr for n in ast.walk(ast.parse(than))
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        }
        assert "la_dong_im_lang" in goi, (
            "`giai_doan_qc_do_luong.chay` ⛔ khong goi `la_dong_im_lang` ⇒ doan "
            "khoang lang se bi ASR + cham WER (wer ≈ 1,0) va keo ca lan chay "
            f"vao vong sua. Cac loi goi tim thay: {sorted(goi)}")


# ══════════════════════════════════════════════════════════════════════════════
#  §2 Tep ngan tu chu KHONG rong — loi phai GOI TEN doan
# ══════════════════════════════════════════════════════════════════════════════

def test_tep_0_giay_tu_chu_KHONG_rong_phai_GOI_TEN_doan(tmp_path, monkeypatch):
    """Dung ca da xay ra 12 lan: chu khong rong, tep 0,0 giay.

    ⛔ Thong bao ⛔ khong duoc dung lai o "Tep tieng sinh ra qua ngan (0.0s)." —
       cau do chi tay vao may sinh tieng, va da lam mot phien di tim sai cho.
    """
    from apps.auto_scan_video import giai_doan_giong, giong_noi

    db, kho, run = _dung_moi_truong(tmp_path, monkeypatch, so_doan=2)
    _gan_may_sinh_tieng(monkeypatch, tmp_path, [], giay=0.0)

    with pytest.raises(giong_noi.GiongError) as loi:
        giai_doan_giong.chay(db, kho, run=run)
    cau = str(loi.value)
    assert "seg_0001" in cau, f"loi khong goi ten doan: {cau!r}"
    assert "0.0" in cau or "0,0" in cau, f"loi mat so giay do duoc: {cau!r}"
    db.close()


# ══════════════════════════════════════════════════════════════════════════════
#  §3 Ban dich con he chu NGUON — chan TRUOC khi ton GPU
# ══════════════════════════════════════════════════════════════════════════════

class TestBanDichChuaDich:

    def test_ty_le_chu_han_do_duoc_tren_CAU_THAT(self):
        from apps.auto_scan_video import ngon_ngu

        assert ngon_ngu.ty_le_chu_han(CAU_TRUNG_THAT) > 0.8, \
            "cau Trung that phai do ra gan 1,0"
        assert ngon_ngu.ty_le_chu_han("Chao buoi sang moi nguoi.") == 0.0

    def test_mot_chu_HAN_le_trong_cau_Viet_KHONG_bi_chan(self):
        """🔑 DOI CHUNG. ⛔ Khong co no thi mot cua chan "moi thu" cung xanh."""
        from apps.auto_scan_video import ngon_ngu

        cau = ("Ten thuong hieu viet la 茶 trong tieng Trung, nhung ca cau nay "
               "la tieng Viet va phai duoc doc binh thuong.")
        assert not ngon_ngu.chua_dich_sang(cau, dich=ngon_ngu.VI), \
            "mot chu Han le da lam ca cau bi coi la chua dich"

    def test_ban_dich_con_chu_TRUNG_bi_chan_TRUOC_may_sinh_tieng(
            self, tmp_path, monkeypatch):
        from apps.auto_scan_video import giai_doan_giong, giong_noi

        db, kho, run = _dung_moi_truong(
            tmp_path, monkeypatch, so_doan=2, cau={"seg_0001": CAU_TRUNG_THAT})
        dem: list = []
        _gan_may_sinh_tieng(monkeypatch, tmp_path, dem)

        with pytest.raises(giong_noi.GiongKhongHopLe) as loi:
            giai_doan_giong.chay(db, kho, run=run)
        cau = str(loi.value)
        assert "seg_0001" in cau, f"loi khong goi ten doan: {cau!r}"
        assert dem == [], \
            f"da ton mot luot may sinh tieng cho chu chua dich: {dem!r}"
        db.close()

    def test_la_that_bai_CUOI_CUNG_khong_thu_lai_ba_lan(self):
        """3 lan thu x 4 luot = 12 luot vo ich, do duoc 27/09.

        `GiongKhongHopLe` ⛔ khong ke thua `GiongError` (lop `TAM_THOI`) —
        `test_409` da chot menh de do; day chot rang cua MOI dung dung lop ay.
        """
        from apps.auto_scan_video import giong_noi, loi as asv_loi

        assert not issubclass(giong_noi.GiongKhongHopLe, giong_noi.GiongError)
        assert asv_loi.phan_loai(giong_noi.GiongKhongHopLe("x")) != asv_loi.TAM_THOI


# ══════════════════════════════════════════════════════════════════════════════
#  §4 `vi_sao_hong` — mot luot hong ⛔ khong bao gio tra rong im lang
# ══════════════════════════════════════════════════════════════════════════════

class TestViSaoHong:
    """🔴 Do duoc 27/09: `test_448` dung `vi_sao_hong` CHI tu `AsvUsage` co
       `trang_thai != "da_giao"`. Bon luot G17 hong khong co dong nao nhu vay
       (moi dong deu `da_giao` — `voice_synthesis` chet TRUOC khi ghi so), nen
       bao cao in `[]` trong khi `asv_run.error` mang dung cau loi.

       `[]` doc **y het** "lan chay nay khong co ly do hong" ⇒ dung ho
       *"hai trang thai gop thanh mot gia tri"*.
    """

    def _run_hong(self, tmp_path, monkeypatch):
        import platform_core.db as dbmod
        from platform_core import credit
        from platform_core.storage import LocalStorage, set_storage
        from tests.conftest import bao_dam_user
        from tests.fixtures.asv_media import nap_nguon_vao_kho

        monkeypatch.setenv("LTT_DATABASE_URL",
                           f"sqlite:///{(tmp_path / 'h.db').as_posix()}")
        dbmod.reset_engine()
        import platform_core.models  # noqa: F401
        from platform_core.registry import load_app_tables
        load_app_tables()
        dbmod.Base.metadata.create_all(dbmod.get_engine())
        db = next(dbmod.get_session())
        kho = LocalStorage(str(tmp_path / "kho")); set_storage(kho)

        from apps.auto_scan_video import features, pipeline

        bao_dam_user(db, "uA"); credit.nap(db, "uA", 1000)
        run = features.tao_run(db, owner_id="uA",
                               source_key=nap_nguon_vao_kho(kho, tmp_path,
                                                            owner_id="uA"),
                               settings={"preset": "bac"}, uoc_luong_credit=50)
        s = features.giai_doan_theo_ten(db, run.id, pipeline.VOICE_SYNTHESIS)
        features.danh_dau_hong(db, s, "Tệp tiếng sinh ra quá ngắn (0.0s).",
                               cuoi_cung=True)
        db.commit()
        return db, run

    def test_mang_LY_DO_THAT_cua_giai_doan_hong(self, tmp_path, monkeypatch):
        from apps.auto_scan_video import quan_sat

        db, run = self._run_hong(tmp_path, monkeypatch)
        ra = quan_sat.vi_sao_hong(db, run)
        assert ra, "lan chay hong ma vi_sao_hong rong"
        cau = json.dumps(ra, ensure_ascii=False)
        assert "voice_synthesis" in cau, cau
        assert "quá ngắn" in cau, cau
        db.close()

    def test_KHONG_BAO_GIO_tra_rong_cho_mot_luot_hong(self, tmp_path,
                                                      monkeypatch):
        """Khong doc duoc ly do thi phai NOI RA, ⛔ khong tra `[]`."""
        from apps.auto_scan_video import features, pipeline, quan_sat

        db, run = self._run_hong(tmp_path, monkeypatch)
        # Xoa moi dau vet ly do: giai doan hong ma khong co thong diep.
        s = features.giai_doan_theo_ten(db, run.id, pipeline.VOICE_SYNTHESIS)
        s.error = ""
        run.error = ""
        db.commit()

        ra = quan_sat.vi_sao_hong(db, run)
        assert ra, "luot hong + khong ly do ⇒ van phai tra MOT dong noi ro"
        assert any(d.get("nguon") == quan_sat.NGUON_KHONG_DOC_DUOC for d in ra), \
            f"thieu dong 'khong doc duoc': {ra!r}"
        db.close()

    def test_van_GIU_nguon_so_cai_cua_test_448(self, tmp_path, monkeypatch):
        """⛔ Ban moi khong duoc lam MAT nguon cu (dong so cai khong `da_giao`)."""
        from apps.auto_scan_video import quan_sat, su_dung

        db, run = self._run_hong(tmp_path, monkeypatch)
        from apps.auto_scan_video import pipeline
        su_dung.ghi(db, run, stage=pipeline.VOICE_SYNTHESIS, item_key="seg_0001",
                    su_dung=su_dung.SuDung(
                        nang_luc="tong_hop_tieng", app_chu="ltt_voice",
                        trang_thai=su_dung.TU_CHOI, don_vi=su_dung.GIAY,
                        so_luong=0.0, credit=0, ma_dispatch="giong:seg_0001:x",
                        ghi_chu={"ly_do": "may sinh tieng tu choi"}))
        db.commit()

        cau = json.dumps(quan_sat.vi_sao_hong(db, run), ensure_ascii=False)
        assert "may sinh tieng tu choi" in cau, cau
        db.close()

    def test_lan_chay_XONG_thi_vi_sao_hong_rong(self, tmp_path, monkeypatch):
        """🔑 Doi chung: `[]` phai van co nghia khi that su khong co gi hong."""
        from apps.auto_scan_video import quan_sat
        from apps.auto_scan_video.tables import RUN_DONE

        db, run = self._run_hong(tmp_path, monkeypatch)
        run.status = RUN_DONE
        run.error = ""
        from apps.auto_scan_video import features, pipeline
        s = features.giai_doan_theo_ten(db, run.id, pipeline.VOICE_SYNTHESIS)
        s.status = "succeeded"
        s.error = ""
        db.commit()

        assert quan_sat.vi_sao_hong(db, run) == []
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
#  §4 Duong DUNG LAI — `im_lang` phai song qua mot luot chay LAI
# ══════════════════════════════════════════════════════════════════════════════
#
# 🔴 §1 do duong **MOI SINH**. `[F]` co BA duong ra cho mot doan, va hai duong
#    con lai — dung lai tep cu (`"cu"`) va dung lai ban ghi lat (`"lat"`) — dung
#    ra khoi khoi `[F0]` hoan toan. Truoc ban sua nay chung ⛔ khong mang
#    `im_lang` va ⛔ khong dem, nen MOI luot chay lai bao `so_doan_im_lang = 0`
#    cho dung nhung doan khach da mat.
#
# ⚠️ Va no ⛔ khong chi la mot con so bao cao sai: `qc_do_luong` doc
#    `la_dong_im_lang` de KHONG cham WER mot khoang lang. Mot dong mat co ⇒
#    `wer ≈ 1,0` ⇒ `sua_chua.giong_khong_dat` ⇒ **mot vong sua tra tien** cho mot
#    doan ⛔ khong co gi de doc. Dung dieu docstring cua `la_dong_im_lang` cam.

def test_LUOT_CHAY_LAI_dung_lai_khoang_lang_van_phai_DEM_va_GAN_CO(
        tmp_path, monkeypatch):
    """Chay `voice_synthesis` HAI lan tren cung mot run.

    Luot hai di vao nhanh **dung lai** (`_doan_trong_staging` thay tep cua luot
    mot), va bat bien cua Task 25 phai giu nguyen o do:

      · `so_doan_im_lang` / `doan_im_lang` ⛔ khong duoc ve 0 / `[]`;
      · dong `ban_ke` cua doan ay van phai `la_dong_im_lang`.

    ⭐ Bai nay cung chot rang luot hai ⛔ KHONG goi lai may sinh tieng — tuc no
       that su di duong dung lai chu ⛔ khong sinh lai tat ca (neu sinh lai thi
       bat bien tren xanh mot cach vo nghia).
    """
    from apps.auto_scan_video import giai_doan_giong, nan_thoi_luong

    db, kho, run = _dung_moi_truong(
        tmp_path, monkeypatch, so_doan=3, cau={"seg_0002": CHU_VO_HINH})
    dem: list = []
    # ⭐ `giay=0.9` ⛔ khong tuy y: khe cua `ban_ghi_gia` la 0,8 s va moc sau la
    #    1,0 s, nen 0,9 s la `giay > khe` NHUNG `giay <= ngan_sach` — tuc no lam
    #    `so_doan_nan_oan` KHAC 0. Voi `giay=0.4` (mac dinh) bo dem ay bang 0 o
    #    ca hai luot va phep so duoi day se xanh ma ⛔ khong do gi.
    _gan_may_sinh_tieng(monkeypatch, tmp_path, dem, giay=0.9)

    ra1 = giai_doan_giong.chay(db, kho, run=run)
    assert ra1["tom_tat"]["so_doan_im_lang"] == 1, \
        "khung sai: luot MOI SINH da khong dem duoc (§1 moi la cho do dieu do)"
    assert ra1["tom_tat"]["so_doan_nan_oan"] > 0, \
        "khung sai: luot dau ⛔ khong co doan `nan oan` nao de so o luot hai"
    sinh_luot_1 = len(dem)

    # ── Luot HAI: cung run, cung ban dich, cung giong ───────────────────────
    ra2 = giai_doan_giong.chay(db, kho, run=run)
    tt = ra2["tom_tat"]

    assert len(dem) == sinh_luot_1, (
        f"luot hai goi lai may sinh tieng {len(dem) - sinh_luot_1} lan ⇒ no "
        f"⛔ khong di duong dung lai, nen bai nay ⛔ khong do dieu no noi")
    assert tt["so_doan_im_lang"] == 1, (
        f"luot chay LAI bao `so_doan_im_lang = {tt['so_doan_im_lang']}` — khach "
        f"mat mot cau thoai va bao cao ⛔ khong noi ra. Cai gia cua quyet dinh "
        f"Task 25 phai DEM DUOC o ca ba duong ra cua `[F]`, ⛔ khong chi duong "
        f"moi sinh")
    assert "seg_0002" in (tt.get("doan_im_lang") or []), (
        f"luot chay LAI ⛔ khong GOI TEN doan im lang: "
        f"{tt.get('doan_im_lang')!r} — mot con so buoc nguoi doc di tim")
    # ⭐ Truong THU BA cua cung ho loi (dieu phoi xin "dem ca tap"):
    #    `so_doan_nan_oan` la tinh chat cua DOAN, ⛔ khong cua luot doc — nen hai
    #    luot cua cung mot video phai ra cung con so. Truoc ban sua, luot chay
    #    lai bao 0 va `asv_doi_soat` ⛔ khong so sanh duoc hai luot.
    assert tt["so_doan_nan_oan"] == ra1["tom_tat"]["so_doan_nan_oan"], (
        f"luot chay LAI bao `so_doan_nan_oan = {tt['so_doan_nan_oan']}` trong "
        f"khi luot dau bao {ra1['tom_tat']['so_doan_nan_oan']} — cung mot video, "
        f"cung nhung doan, hai con so")

    khoa_ke = [p for p in ra2["phan"] if p["kind"] == "json"]
    with kho.open(khoa_ke[0]["staging_key"]) as f:
        ban_ke = json.loads(f.read().decode("utf-8"))
    dong = next(d for d in ban_ke["doan"] if str(d["ma"]) == "seg_0002")
    assert nan_thoi_luong.la_dong_im_lang(dong), (
        f"dong `ban_ke` cua doan DUNG LAI mat co `im_lang` ({dong!r}) ⇒ "
        f"`qc_do_luong` se ASR mot khoang lang, cham WER voi mot cau chu, ra "
        f"`wer ≈ 1,0` va keo ca lan chay vao MOT VONG SUA tra tien cho mot "
        f"doan ⛔ khong co gi de doc")
    db.close()


#: Khoa duy nhat duoc phep CHI co o nhanh DUNG LAI. No la ca y nghia cua nhanh
#: ay (`tom_tat.so_doan_dung_lai` / `so_doan_moi_sinh` dem bang no), nen no la
#: mot ngoai le CO TEN — ⛔ khong phai mot lech duoc tha.
KHOA_CHI_CUA_DUNG_LAI = {"tu_cu"}


def test_BAT_BIEN_O_BIEN_dong_ban_ke_co_CUNG_TAP_KHOA_du_den_tu_nhanh_nao(
        tmp_path, monkeypatch):
    """🔴 **Hai lan, cung mot cho noi, cung mot thieu sot.**

        nhanh SINH MOI   do that / ghi co that
        nhanh DUNG LAI   tra `0.0` (`edd5409f`) / ⛔ khong ghi co (`im_lang`)

    Hai ban sua le ⛔ khong ngan lan thu ba: `[F]` co BA duong ra dung mot dong
    `ban_ke`, va ⛔ khong cho nao doi chieu chung. Bai nay la **phep do co hoc**
    thay cho loi dan do — no so **TAP KHOA** cua dong `ban_ke` cua CUNG mot `ma`
    giua luot MOI SINH va luot DUNG LAI.

    ⭐ Vi sao tap khoa chu ⛔ khong gia tri: mot truong bi ROI mat ha nguon (hong
       im lang, cach day bon buoc — `qc_do_luong`, `thoi_gian.lap_ke_hoach`), con
       mot gia tri khac nhau giua hai luot thi thuong la DUNG (`tu_cu`, va `giay`
       do lai co the lech vai phan nghin). ⇒ Do cai ma su khac biet **luon** la
       bug.

    ⛔ Va bai nay co **hai** loai dong de so: dong DAU cua mot nhom va dong THEO
       SAU (`no_ban_ke` co y dung hai hinh dang khac nhau), nen no so theo `ma`
       chu ⛔ khong tron ca danh sach lai.
    """
    from apps.auto_scan_video import giai_doan_giong

    db, kho, run = _dung_moi_truong(
        tmp_path, monkeypatch, so_doan=3, cau={"seg_0002": CHU_VO_HINH})
    _gan_may_sinh_tieng(monkeypatch, tmp_path, [])

    def _ke(ra):
        khoa_ke = [p for p in ra["phan"] if p["kind"] == "json"]
        with kho.open(khoa_ke[0]["staging_key"]) as f:
            return {str(d["ma"]): d
                    for d in json.loads(f.read().decode("utf-8"))["doan"]}

    moi = _ke(giai_doan_giong.chay(db, kho, run=run))      # nhanh SINH MOI
    lai = _ke(giai_doan_giong.chay(db, kho, run=run))      # nhanh DUNG LAI

    assert set(moi) == set(lai), (
        f"hai luot phu khac tap `ma`: chi o luot dau {sorted(set(moi) - set(lai))}, "
        f"chi o luot hai {sorted(set(lai) - set(moi))}")

    lech: dict[str, tuple] = {}
    for ma in sorted(moi):
        a = set(moi[ma]) | KHOA_CHI_CUA_DUNG_LAI
        b = set(lai[ma]) | KHOA_CHI_CUA_DUNG_LAI
        if a != b:
            lech[ma] = (sorted(a - b), sorted(b - a))

    assert not lech, (
        "dong `ban_ke` cua nhanh DUNG LAI ⛔ khong mang cung tap khoa voi nhanh "
        "SINH MOI — {ma: (ROI o luot dung lai, chi co o luot dung lai)} = "
        f"{lech}. Mot truong bi roi o day no ra o mot giai doan cach day bon "
        "buoc (`qc_do_luong`, `thoi_gian.lap_ke_hoach`), va do dung la khuon "
        "cua `edd5409f` (`giay = 0.0`) va cua `im_lang` — hai lan cung mot cho.")
    db.close()
