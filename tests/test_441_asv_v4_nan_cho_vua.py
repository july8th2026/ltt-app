"""Pha 15 — sinh tieng va nan cho vua khe thoi gian.

Nam nhom, theo dung nhung gi cong thoat doi:

  A. Chinh sach     — bac thang bon nac, va THU TU cua no
  B. Tran vong lap  — mot vong lap tren dich vu tra tien phai co day
  C. Dung lai       — doan khong doi thi khong doc lai, khong tra tien lai
  D. So cai         — moi doan da giao ghi DUNG MOT lan
  E. Giong          — lay tu ban long tieng, khong tu `settings`
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import nan_cho_vua as nan

# 🔴 Cac phep kiem chay het chuoi cham toi `audio_prepare`.
from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401


# ══════════════════════════════════════════════════════════════════════════════
#  A. Chinh sach
# ══════════════════════════════════════════════════════════════════════════════

def test_dung_sai_KHONG_doi_xung_va_phia_DAI_chat_hon():
    """⛔ Hai hau qua khong ngang nhau nen hai nguong khong ngang nhau.

    Dai hon khe -> cau tran sang canh sau hoac de len loi thoai ke tiep.
    Ngan hon khe -> mot khoang lang, ma `thoi_gian.py` von da biet cach nuot.
    """
    assert nan.DUNG_SAI_DAI < nan.DUNG_SAI_NGAN, (
        "phia DAI phai chat hon phia NGAN — mot ban long tieng hoi thua khoang "
        "lang van xem duoc; mot ban noi de len nhau thi khong")


def test_nac_CO_GIAN_cua_bac_thang_PHAI_voi_toi_duoc():
    """🔴 Khuyet tat that trong chinh sach cua chinh pha nay, tim ra bang kiem.

    Ban dau `DUNG_SAI_DAI` la 0,15 — dung bang tran co gian (1,15). Khi do mot
    doan hoac nam trong dung sai, hoac da vuot ca tran co gian: **khong co khoang
    nao** de `CO_GIAN` ton tai. Bac thang bon nac tren giay chi con ba nac khi
    chay, va no khong hong ra loi nao — moi doan van co mot trang thai hop le.
    """
    assert nan.DUNG_SAI_DAI < nan.tran_co_gian() - 1.0, (
        "dung sai (%.3f) khong nho hon tran co gian - 1 (%.3f): nac CO_GIAN "
        "khong bao gio chay" % (nan.DUNG_SAI_DAI, nan.tran_co_gian() - 1.0))

    # ... va no khong chi la mot bat dang thuc: phai co MOT do dai that roi vao do.
    khe = 3.0
    giua = khe * (1.0 + (nan.DUNG_SAI_DAI + (nan.tran_co_gian() - 1.0)) / 2)
    assert nan.can_nan(giua, khe), "khoang giua khong bi coi la can nan"
    duoc, _ = nan.co_gian_du_khong(giua, khe)
    assert duoc, "khoang giua khong co gian duoc"


def test_khe_la_DO_DAI_cua_doan_khong_phai_moc_KET():
    """🔴 Lo hong ma kiem dot bien tim ra, va no la mot mau thu MU.

    Moi mau thu cua nhom nay dat `bat = 0.0` — va o do `ket` BANG `ket - bat`.
    Nen mot cach cai dat lay thang `ket` lam khe van xanh het, du no sai voi moi
    doan khong bat dau tu giay 0 (tuc **moi doan tru doan dau tien**).

    ⭐ Hau qua neu lot: khe cua doan thu muoi la 100 giay thay vi 3 giay, nen
       khong doan nao bi coi la qua dai nua — ca bac thang nan **im lang tat**.
    """
    assert nan.khe_cua({"bat": 10.0, "ket": 13.0}) == 3.0
    assert nan.khe_cua({"bat": 0.0, "ket": 3.0}) == 3.0
    # Moc nguoc (du lieu hong) khong duoc cho ra khe am.
    assert nan.khe_cua({"bat": 5.0, "ket": 1.0}) == 0.0


def test_can_nan_dung_tren_mot_doan_KHONG_bat_dau_tu_khong():
    """Cung menh de, nhung o cap chinh sach: mot doan giua phim."""
    m = {"bat": 120.0, "ket": 123.0}
    khe = nan.khe_cua(m)
    assert khe == 3.0
    assert nan.can_nan(4.5, khe), "4,5 giay trong khe 3 giay ma khong bi coi la qua dai"


def test_trong_dung_sai_thi_KHONG_nan():
    assert not nan.can_nan(3.2, 3.0)      # +6,7%, duoi dung sai 8%
    assert not nan.can_nan(2.2, 3.0)      # -27%, trong dung sai ngan 35%


def test_ngoai_dung_sai_thi_PHAI_nan():
    assert nan.can_nan(3.6, 3.0)          # +20%, tren dung sai 8%
    assert nan.can_nan(1.7, 3.0)          # -43%


def test_khe_bang_KHONG_thi_khong_nan_duoc_gi():
    """Mot doan khong co khe (moc thoi gian hong) khong phai mot doan can nan —
    no la mot doan ta khong biet gi ve no. Nan mu la lam hong mot cau dang dung."""
    assert not nan.can_nan(5.0, 0.0)
    assert nan.lech(5.0, 0.0) == 0.0


def test_cau_NGAN_hon_khe_khong_can_co_gian_gi_ca():
    """⛔ Keo dai mot cau bang xu ly tin hieu nghe ra ngay; mot khoang lang thi
    khong ai de y. Nen phia ngan khong bi tran co gian chan."""
    duoc, he_so = nan.co_gian_du_khong(1.0, 3.0)
    assert duoc and he_so == 1.0


def test_co_gian_bi_chan_boi_TRAN_da_khai():
    tran = nan.tran_co_gian()
    duoc_it, _ = nan.co_gian_du_khong(3.0 * (tran - 0.02), 3.0)
    duoc_nhieu, he_so = nan.co_gian_du_khong(3.0 * (tran + 0.5), 3.0)
    assert duoc_it, "trong tran ma bi tu choi"
    assert not duoc_nhieu, "vuot tran ma van cho co gian"
    assert he_so > tran


def test_tran_co_gian_MUON_tu_thoi_gian_khong_go_lai_so():
    """⛔ Mot con so chep lai la mot con so se troi. Xem `banh-coc` trong CLAUDE.md."""
    from apps.auto_scan_video.thoi_gian import TRAN_TANG_TOC

    assert nan.tran_co_gian() == TRAN_TANG_TOC


def test_ba_trang_thai_ket_luan_dung_theo_bac_thang():
    tran = nan.tran_co_gian()
    assert nan.ket_luan("a", chu="x", giay=3.05, khe=3.0, so_vong=0).trang_thai == nan.VUA
    assert nan.ket_luan("b", chu="x", giay=3.0 * (tran - 0.05), khe=3.0,
                        so_vong=2).trang_thai == nan.CO_GIAN
    assert nan.ket_luan("c", chu="x", giay=3.0 * (tran + 1.0), khe=3.0,
                        so_vong=2).trang_thai == nan.CAN_SUA


def test_CAN_SUA_khong_duoc_tinh_la_DAT():
    """⛔ Cong thoat doi "artifact hop le HOAC mot that bai xac dinh". `CAN_SUA`
    la ve thu hai, va no khong duoc am tham di tiep nhu mot thanh cong."""
    kq = nan.ket_luan("c", chu="x", giay=99.0, khe=3.0, so_vong=2)
    assert kq.trang_thai == nan.CAN_SUA
    assert not kq.dat


# ══════════════════════════════════════════════════════════════════════════════
#  B. Loi nhac viet lai
# ══════════════════════════════════════════════════════════════════════════════

def test_loi_nhac_mang_theo_do_dai_DA_DO_DUOC():
    """🔑 Khac biet giua "hay viet ngan hon" va "cau nay doc ra 4,8 giay, khe co
    3,2 giay" — cai sau la mot muc tieu kiem duoc, va la ly do vong thu hai
    thuong khong can den."""
    import json

    m = {"ma": "seg_0001", "goc": "source", "bat": 0.0, "ket": 3.2}
    msgs = nan.loi_nhac_nan(m, chu_hien_tai="cau dai", giay_do_duoc=4.8, khe=3.2)
    goi = json.loads(msgs[-1]["content"])
    assert goi["doc_ra_het_giay"] == 4.8
    assert goi["khe_giay"] == 3.2
    assert 0 < goi["muc_tieu_giay"] < 3.2, (
        "muc tieu phai THAP hon khe — vua khit la vua du de mot dao dong nho "
        "cua may sinh tieng lam no tran ra lai")


def test_loi_nhac_doi_viec_theo_HUONG_lech():
    m = {"ma": "s", "goc": "g", "bat": 0.0, "ket": 3.0}
    dai = nan.loi_nhac_nan(m, chu_hien_tai="x", giay_do_duoc=5.0, khe=3.0)[0]["content"]
    ngan = nan.loi_nhac_nan(m, chu_hien_tai="x", giay_do_duoc=1.0, khe=3.0)[0]["content"]
    assert "RUT NGAN" in dai
    assert "DAY DAN HON" in ngan


def test_model_tra_ve_rong_thi_NEM():
    with pytest.raises(nan.NanError):
        nan.doc_nan({"doan": {"chu": "   "}})
    with pytest.raises(nan.NanError):
        nan.doc_nan({})


# ══════════════════════════════════════════════════════════════════════════════
#  C. Chay THAT: tran vong lap, dung lai, so cai
# ══════════════════════════════════════════════════════════════════════════════

from tests.test_402_asv_mach_doc_gia import (asr_gia, db, dich_gia,  # noqa: E402,F401
                                             giong_gia, kho_tam)


def _kho():
    from platform_core.storage import get_storage

    return get_storage()


def _tieng_dai(monkeypatch, giay: float = 9.0):
    """May sinh tieng LUON tra ve mot doan qua dai — de bac thang phai chay het.

    ⭐ Chin giay cho mot khe ~0,8 giay la vuot xa ca tran co gian, nen ket qua
       PHAI la `CAN_SUA`. Mot mau thu chi hoi qua dai se khong phan biet duoc
       "bac thang chay het" voi "bac thang dung o nac 3".
    """
    import math
    import struct
    import wave
    from apps.auto_scan_video import giong_noi

    def gia(chu, *, ref_b64=None, preset=None, **kw):
        import io

        n, sr = int(giay * 16000), 16000
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
            w.writeframes(b"".join(
                struct.pack("<h", int(8000 * math.sin(i / 20.0)))
                for i in range(n)))
        return buf.getvalue(), {}

    monkeypatch.setattr(giong_noi, "doc_mot_doan", gia)
    monkeypatch.setattr(giong_noi, "san_sang", lambda: True)


def test_vong_nan_co_TRAN_CUNG(tmp_path, monkeypatch, db, kho_tam, asr_gia,
                               dich_gia, giong_gia):
    """🔴 Mot vong lap "sua cho toi khi vua" tren mot dich vu TRA TIEN la mot hoa
    don khong co day. `V4_RESOURCE_CPU_GPU_POLICY` cam no bang chu.

    May sinh tieng o day luon tra ve 9 giay — khong lan viet lai nao cuu duoc.
    Neu vong khong co tran, phep kiem nay khong bao gio ket thuc.
    """
    from apps.auto_scan_video import ai, features, giai_doan_giong, pipeline
    from apps.auto_scan_video.tables import AsvRun
    from tests.test_402_asv_mach_doc_gia import _chay_het_hang_doi, _tao_run

    _tieng_dai(monkeypatch)
    dem = {"n": 0}

    def gia_nan(db_, run_, thao_tac, messages, *, stage, item_key, uoc_credit=0,
                ctx=None, temperature=None):
        # ⚠️ `noi_dung` la CHUOI (pha 22): cua that tra ve nguyen van phan
        #    hoi cua model, va `ai.doc_json` moi la bo doc.
        import json
        if thao_tac is ai.RUT_NGAN_CHO_VUA:
            dem["n"] += 1
            than = {"doan": {"chu": "cau ngan hon lan %d" % dem["n"]}}
            return {"noi_dung": json.dumps(than, ensure_ascii=False),
                    "su_dung": None}
        goi = json.loads(messages[-1]["content"])
        from apps.auto_scan_video import long_tieng
        than = {"doan": {
            str(d["ma"]): {"chu": "loi thoai cua %s" % d["ma"],
                           "cam_xuc": long_tieng.CAM_XUC[0],
                           "kieu_noi": long_tieng.KIEU_NOI[0], "nhan_manh": []}
            for d in goi.get("doan") or []}}
        return {"noi_dung": json.dumps(than, ensure_ascii=False),
                "su_dung": None}

    monkeypatch.setattr(ai, "goi_tinh_tien", gia_nan)

    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db)
    db.expire_all()

    gd = features.giai_doan_theo_ten(db, run.id, pipeline.VOICE_SYNTHESIS)
    assert gd is not None
    tt = (gd.outputs or {})
    assert dem["n"] > 0, "chua vong nan nao chay — phep kiem khong do duoc gi"
    assert dem["n"] <= nan.VONG_TOI_DA * max(1, tt.get("so_doan", 1)), (
        "goi viet lai %d lan, vuot tran %d vong moi doan"
        % (dem["n"], nan.VONG_TOI_DA))
    assert tt.get("so_can_sua", 0) > 0, (
        "tieng luon 9 giay ma khong doan nao bi danh la CAN_SUA")


def test_chay_lai_KHONG_doc_lai_va_KHONG_ghi_so_lan_hai(
        tmp_path, monkeypatch, db, kho_tam, asr_gia, dich_gia, giong_gia):
    """⭐ Hai menh de trong mot lan chay, va chung la hai mat cua cung mot dieu:
    doan khong doi thi khong doc lai (khong ton may sinh tieng) va khong ghi so
    lan hai (khong ton tien cua khach)."""
    from apps.auto_scan_video import features, giai_doan_giong, pipeline, su_dung
    from apps.auto_scan_video.tables import AsvRun
    from tests.test_402_asv_mach_doc_gia import _chay_het_hang_doi, _tao_run

    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db)
    db.expire_all()
    run = db.get(AsvRun, run.id)

    gd = features.giai_doan_theo_ten(db, run.id, pipeline.VOICE_SYNTHESIS)
    assert gd.status == "succeeded", "voice: %s %s" % (gd.status, gd.error)
    so_dong_1 = len(su_dung.cac_dong(db, run, stage=pipeline.VOICE_SYNTHESIS))
    assert so_dong_1 > 0, "khong ghi dong so cai nao cho tieng da giao"

    ra = giai_doan_giong.chay(db, _kho(), run=run, ctx=None)
    assert ra["tom_tat"]["so_doan_moi_sinh"] == 0, (
        "chay lai ma van doc lai — dung lai o muc doan khong hoat dong")

    so_dong_2 = len(su_dung.cac_dong(db, run, stage=pipeline.VOICE_SYNTHESIS))
    assert so_dong_2 == so_dong_1, (
        "ghi so lan hai cho cung mot doan: %d -> %d" % (so_dong_1, so_dong_2))


def test_giong_lay_tu_BAN_LONG_TIENG_khong_tu_settings(
        tmp_path, monkeypatch, db, kho_tam, asr_gia, dich_gia, giong_gia):
    """🔴 No cua pha 14, tra o day.

    Pha 14 dong bang giong vao ban long tieng vi loi thoai duoc VIET CHO mot
    giong. Neu giai doan nay van tu doc `settings` thi mot lan chay co the viet
    loi cho mot giong roi **doc len bang mot giong khac**, va khong cho nao bao
    loi vi ca hai deu tim thay mot gia tri hop le cua rieng minh.
    """
    from apps.auto_scan_video import features, giai_doan_giong, giong_noi, pipeline
    from apps.auto_scan_video.tables import AsvRun
    from tests.test_402_asv_mach_doc_gia import _chay_het_hang_doi, _tao_run

    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db)
    db.expire_all()
    run = db.get(AsvRun, run.id)

    # `settings` noi mot dang, ban long tieng noi mot dang khac.
    run.settings = {**dict(run.settings or {}), "voice_id": "GIONG SAI"}
    db.commit()

    bat = {}
    that = giong_noi.giai_giong

    def theo_doi(db_, *, owner_id, voice_id="", preset=""):
        bat["voice_id"] = voice_id
        return that(db_, owner_id=owner_id, voice_id=voice_id, preset=preset)

    monkeypatch.setattr(giong_noi, "giai_giong", theo_doi)
    giai_doan_giong.chay(db, _kho(), run=db.get(AsvRun, run.id), ctx=None)

    assert bat["voice_id"] != "GIONG SAI", (
        "doc `settings` thay vi `ma_giong` cua ban long tieng — loi thoai duoc "
        "viet cho mot giong va doc len bang giong khac")


def test_ban_ke_noi_cho_TIMING_biet_doan_nao_can_co_gian(
        tmp_path, monkeypatch, db, kho_tam, asr_gia, dich_gia, giong_gia):
    """Pha 16 phai biet doan nao khong vua va he so bao nhieu — khong thi no lai
    di do lai tu dau, hoac te hon, doan."""
    import json

    from apps.auto_scan_video import features, pipeline
    from tests.test_402_asv_mach_doc_gia import _chay_het_hang_doi, _tao_run

    _tieng_dai(monkeypatch, giay=6.0)
    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db)
    db.expire_all()

    gd = features.giai_doan_theo_ten(db, run.id, pipeline.VOICE_SYNTHESIS)
    khoa = next(k for k in (gd.outputs or {}).get("khoa_asset") or []
                if k.endswith(".json"))
    with _kho().open(khoa) as f:
        ke = json.loads(f.read().decode("utf-8"))
    assert ke["doan"], "ban ke rong"
    for d in ke["doan"]:
        assert "khe" in d, "ban ke khong noi khe muc tieu"
        assert d.get("trang_thai_nan") in nan.TRANG_THAI, (
            "ban ke khong noi doan nay co vua khong")


def test_van_tay_doan_GOM_van_ban_da_nan():
    """🔴 Lo hong thu hai: van tay bo qua van ban thi vong nan tu vo hieu hoa.

    Sau mot vong nan, doan nay la ket qua cua mot cau **KHAC**. Neu van tay
    khong doi theo cau thi khoa luu tru khong doi, va lan chay sau se **dung lai
    tep tieng CU** — dung cai ma ta vua quyet dinh la khong vua.

    ⛔ Va no khong hong ra loi nao: van co mot tep tieng hop le o dung cho, chi
       la no doc cau truoc khi sua.
    """
    from apps.auto_scan_video import giai_doan_giong

    a = giai_doan_giong._van_tay("seg_0001", "cau dai luom thuom", "G", "bac")
    b = giai_doan_giong._van_tay("seg_0001", "cau da rut ngan", "G", "bac")
    assert a != b, (
        "van tay khong doi khi van ban doi — mot doan da viet lai se dung lai "
        "tep tieng cu")

    # ... va van doi theo giong, vi loi thoai duoc doc BOI mot giong cu the.
    c = giai_doan_giong._van_tay("seg_0001", "cau da rut ngan", "GIONG KHAC", "bac")
    assert c != b
