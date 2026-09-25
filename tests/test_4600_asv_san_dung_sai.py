"""Buoc 0.5 + Buoc 1 — SAN dung sai chieu DAI, va bo ve "viet lai cho DAI ra".

🔑 **Nen da do, ⛔ dung do lai o day.** Luot that `asvr_9fc9cc89` (phim 275 s,
   106 doan): 59 doan vao nac 2, 65 luot goi may B, LLM chiem ~52 % giai doan,
   khe trung vi 1,71 s.

Ba menh de, va menh de dau la mot loi TINH chu khong phai mot ti le xau:

  A. `DUNG_SAI_DAI x khe` = 0,08 x 1,71 s = **137 ms**, con luong tu thay doi nho
     nhat cua mot lan viet lai = **mot am tiet = 256 ms** (hoi quy
     `giay = 0,188 + n x 0,256`, R2 = 0,927, n = 47). Doi `±137 ms` la mot cau
     hoi ⛔ khong tra loi duoc — bat ke no cham bao nhieu doan (100/106).
  B. Chieu qua NGAN ⛔ khong duoc goi LLM: 0/5 he da khao sat co ve nay
     (`docs/auto_scan_video_final/NC_CAPCUT_VA_CONG_DONG.md` §D5), va lap luan da
     nam san trong chinh `nan_cho_vua` tu truoc.
  C. Buoc 0.5 — giay LAN DOC DAU phai vao `outputs`, ⛔ khong chi log: truoc buoc
     nay khong ai tinh duoc A va B tiet kiem bao nhieu luot goi may B.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from apps.auto_scan_video import nan_cho_vua as nan

GOC = Path(__file__).resolve().parents[1]

# 🔴 Nhom D chay het chuoi cham toi `audio_prepare`.
from tests.rao_chan_nang import demucs_gia_lap  # noqa: E402,F401
from tests.test_402_asv_mach_doc_gia import (asr_gia, db,  # noqa: E402,F401
                                             dich_gia, giong_gia, kho_tam)


# ══════════════════════════════════════════════════════════════════════════════
#  A. SAN TUYET DOI — nghiem thu 1 va 2
# ══════════════════════════════════════════════════════════════════════════════

def test_lech_NHO_HON_mot_am_tiet_la_VUA_khong_vao_nac_2():
    """⭐ Nghiem thu 1. Khe 1,0 s doc ra 1,10 s = lech +10 %, tuc **100 ms**.

    100 ms < 256 ms = mot am tiet ⇒ ⛔ khong mot lan viet lai nao co the nham
    trung dich. Truoc 25/09 doan nay bi day vao nac 2 (0,08 x 1,0 = 80 ms).
    """
    khe, giay = 1.0, 1.10
    assert giay - khe == pytest.approx(0.10, abs=1e-9)
    assert giay - khe < nan.SAN_DUNG_SAI_GIAY, "mau thu khong con do duoc gi"

    assert not nan.can_nan(giay, khe), (
        "lech %.0f ms < mot am tiet %.0f ms ma van bi coi la can nan"
        % ((giay - khe) * 1000, nan.SAN_DUNG_SAI_GIAY * 1000))
    assert not nan.nen_viet_lai(giay, khe), "vao nac 2 = tra tien cho may B"
    assert nan.ket_luan("s", chu="x", giay=giay, khe=khe,
                        so_vong=0).trang_thai == nan.VUA

    # ... va day LA mot thay doi hanh vi co y: ti le mot minh noi nguoc lai.
    assert nan.lech(giay, khe) > nan.DUNG_SAI_DAI, (
        "mau thu khong con phan biet duoc ban moi voi ban cu")


def test_SAN_khong_nuot_ca_THAT_khe_dai_van_do_bang_TI_LE():
    """⭐ Nghiem thu 2. Khe 10 s doc ra 11,0 s = lech +1 s, **tren** san.

    🔴 Day la nua khong the thieu cua nghiem thu 1: mot san dat qua cao se lam
       moi doan "vua" va bac thang nan im lang tat — dung ho `banh coc` ma kho
       nay da gap (do vang mat thi xoa cung xanh).
    """
    khe, giay = 10.0, 11.0
    assert nan.dung_sai_giay(khe) == pytest.approx(nan.DUNG_SAI_DAI * khe), (
        "khe dai ma san van thang ti le — san dat qua cao")
    assert giay - khe > nan.dung_sai_giay(khe)
    assert nan.can_nan(giay, khe), "lech 1 s tren khe 10 s ma khong phai nan"
    assert nan.nen_viet_lai(giay, khe), "ca THAT bi san nuot"


def test_san_la_MOT_am_tiet_khong_thap_hon():
    """⛔ Duoi luong tu thi phan quyet la tung dong xu."""
    assert nan.SAN_DUNG_SAI_GIAY >= 0.256, (
        "ha xuong duoi mot am tiet: ta lai tra tien cho mot lan viet lai khong "
        "the nham trung dich")


def test_dung_sai_giay_la_max_cua_TI_LE_va_SAN():
    """Hinh dang cua ham, do o ca hai che do + diem giao."""
    giao = nan.SAN_DUNG_SAI_GIAY / nan.DUNG_SAI_DAI     # 3,2 s
    assert nan.dung_sai_giay(giao / 2) == pytest.approx(nan.SAN_DUNG_SAI_GIAY)
    assert nan.dung_sai_giay(giao * 2) == pytest.approx(
        nan.DUNG_SAI_DAI * giao * 2)
    assert nan.dung_sai_giay(giao) == pytest.approx(nan.SAN_DUNG_SAI_GIAY)
    # Khe khong xac dinh: ⛔ khong duoc tra ve mot dung sai duong.
    assert nan.dung_sai_giay(0.0) == 0.0
    assert nan.dung_sai_giay(-1.0) == 0.0


# ══════════════════════════════════════════════════════════════════════════════
#  B. BAT BIEN CAP MODULE — nghiem thu 4
# ══════════════════════════════════════════════════════════════════════════════

def test_bat_bien_cap_module_CON_DUNG_va_DUNG_SAI_DAI_khong_doi():
    """⭐ Nghiem thu 4. Ban sua ⛔ khong dung tay vao `DUNG_SAI_DAI`, nen khang
    dinh `nan_cho_vua.py` dat o cap module phai con nguyen — sai thi app ⛔ KHONG
    NAP DUOC, ⛔ khong phai mot test do.
    """
    assert nan.DUNG_SAI_DAI == 0.08, "ban sua nay ⛔ khong duoc doi ti le"
    assert nan.DUNG_SAI_DAI < nan.tran_co_gian() - 1.0
    nan._kiem_chinh_sach()      # nem AssertionError neu bac thang tu mau thuan


def test_SAN_khong_bi_dua_vao_khang_dinh_cua_bac_thang():
    """🔴 Mot cai bay MOI ma ban sua nay de tranh.

    `DUNG_SAI_DAI` va `tran_co_gian() - 1` la hai TI LE khong don vi;
    `SAN_DUNG_SAI_GIAY` la GIAY tuyet doi. Mot bat dang thuc tron ca ba doc duoc
    va **luon dung o mot khe nao do, luon sai o mot khe khac** — dung ho
    `dieu-kien-thieu-pham-vi` va `banh-coc-do-cach-go`.
    """
    cay = ast.parse((GOC / "apps/auto_scan_video/nan_cho_vua.py")
                    .read_text(encoding="utf-8"))
    fn = next(f for f in ast.walk(cay) if isinstance(f, ast.FunctionDef)
              and f.name == "_kiem_chinh_sach")
    ten = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
    assert "SAN_DUNG_SAI_GIAY" not in ten, (
        "so mot GIAY tuyet doi voi mot TI LE trong cung mot bat dang thuc")


def test_hang_so_TU_KHAI_nguon_goc():
    """⭐ Cung luat voi cac hang khac trong tep: mot con so khong tu khai nguon
    goc la mot con so se troi, va ⛔ khong ai biet no da cu."""
    src = (GOC / "apps/auto_scan_video/nan_cho_vua.py").read_text(
        encoding="utf-8")
    dau = src.index("SAN_DUNG_SAI_GIAY = ")
    chu_thich = src[max(0, dau - 2000):dau]
    for moc in ("am tiet", "0,927", "VideoLingo", "Viral"):
        assert moc in chu_thich, f"chu thich cua san khong khai `{moc}`"


# ══════════════════════════════════════════════════════════════════════════════
#  C. BO ve "viet lai cho DAI ra" — nghiem thu 3
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("giay, khe", [(1.0, 10.0), (0.01, 10.0), (2.0, 5.0)])
def test_doan_qua_NGAN_KHONG_goi_LLM_du_lech_bao_nhieu(giay, khe):
    """⭐ Nghiem thu 3. `thoi_gian.lap_ke_hoach` da biet nuot khoang lang."""
    assert nan.lech(giay, khe) < -nan.DUNG_SAI_NGAN, "mau thu chua du ngan"
    assert not nan.nen_viet_lai(giay, khe), (
        "goi model keo dai mot cau ngan: 0/5 he khao sat lam dieu nay")


def test_DUNG_SAI_NGAN_con_nguyen_cho_PHAN_LOAI():
    """⛔ ⛔ Khong xoa `DUNG_SAI_NGAN` — no con dung de phan loai/bao cao.

    Mot doan qua ngan **van** phai doc ra la "khong vua" trong `tom_tat`; chi
    duong goi model bi chan. Xoa han thi bao cao mat kha nang phan biet "vua" voi
    "ngan qua ma ta co y bo qua" — dung ho `hai-trang-thai-gop-thanh-mot-gia-tri`.
    """
    assert nan.DUNG_SAI_NGAN == 0.35
    assert nan.can_nan(1.0, 10.0), (
        "doan ngan khong con bi coi la 'khong vua' — bao cao mat mot the loai")
    kq = nan.ket_luan("s", chu="x", giay=1.0, khe=10.0, so_vong=0)
    assert kq.trang_thai != nan.VUA, "doan ngan bi xep lan vao VUA"


def test_loi_nhac_NEM_neu_bi_goi_cho_mot_doan_NGAN():
    """🔴 Bat bien o BIEN, khong chi o vong lap.

    Mot cai chan o vong lap ma ⛔ khong co chan o bien la mot cai chan mot nguoi
    goi moi se di vong qua ma ⛔ khong ai thay — ho
    `cho-noi-hai-module-vut-truong-im-lang`.
    """
    m = {"ma": "s", "goc": "g", "bat": 0.0, "ket": 10.0}
    with pytest.raises(nan.NanError):
        nan.loi_nhac_nan(m, chu_hien_tai="x", giay_do_duoc=1.0, khe=10.0)
    # Bang nhau cung khong phai viec cua no.
    with pytest.raises(nan.NanError):
        nan.loi_nhac_nan(m, chu_hien_tai="x", giay_do_duoc=10.0, khe=10.0)
    # ... va chieu DAI van di duong cu.
    msgs = nan.loi_nhac_nan(m, chu_hien_tai="x", giay_do_duoc=14.0, khe=10.0)
    assert "RUT NGAN" in msgs[0]["content"]
    assert "DAY DAN HON" not in msgs[0]["content"], (
        "ve keo dai da bo ma loi nhac van con nhac den no")


def test_vong_nan_cua_giai_doan_goi_NEN_VIET_LAI_khong_phai_CAN_NAN():
    """⭐ Chan phai o dung cho: vong lap quyet dinh TIEU TIEN, nen no phai hoi
    ham tra loi cau hoi ve tien."""
    cay = ast.parse((GOC / "apps/auto_scan_video/giai_doan_giong.py")
                    .read_text(encoding="utf-8"))
    fn = next(f for f in cay.body if isinstance(f, ast.FunctionDef)
              and f.name == "chay")
    goi = {c.func.attr for c in ast.walk(fn) if isinstance(c, ast.Call)
           and isinstance(c.func, ast.Attribute)}
    assert "nen_viet_lai" in goi
    assert "can_nan" not in goi, (
        "vong lap con hoi `can_nan` — doan qua NGAN se lai goi model")


# ══════════════════════════════════════════════════════════════════════════════
#  D. BUOC 0.5 — giay tung vong vao `outputs`, truy van duoc
# ══════════════════════════════════════════════════════════════════════════════

def test_ban_ghi_luot_doc_KHONG_mang_loi_thoai_cua_khach():
    bg = nan.ban_ghi_luot_doc("s1", vong=1, giay=4.0, khe=3.0)
    assert bg["ma"] == "s1" and bg["vong"] == 1
    assert bg["giay"] == 4.0 and bg["khe"] == 3.0
    assert "chu" not in bg
    assert bg["lech"] == pytest.approx(nan.lech(4.0, 3.0), abs=1e-4)
    # Phan quyet dong hang voi con so cua chinh luot doc ay.
    assert bg["can_nan"] is True and bg["nen_viet_lai"] is True


def test_tom_tat_MANG_tung_luot_doc_va_khoa_cu_con_nguyen():
    cac = [nan.ket_luan("s1", chu="a", giay=3.0, khe=3.0, so_vong=0)]
    luot = [nan.ban_ghi_luot_doc("s1", vong=0, giay=5.0, khe=3.0),
            nan.ban_ghi_luot_doc("s1", vong=1, giay=3.0, khe=3.0)]
    t = nan.tom_tat(cac, tung_luot_doc=luot)
    assert t["so_luot_do"] == 2
    assert [d["vong"] for d in t["tung_luot_doc"]] == [0, 1]
    # 🔑 Giay LAN DOC DAU (5,0) chi ton tai o day — `tung_doan` giu 3,0.
    assert t["tung_luot_doc"][0]["giay"] == 5.0
    assert t["tung_doan"][0]["giay"] == 3.0
    for k in ("so_doan", "so_vua", "so_co_gian", "so_can_sua", "so_vong_tong",
              "lech_lon_nhat", "tung_doan"):
        assert k in t, k


def test_tom_tat_KHONG_co_tham_so_moi_van_hop_le():
    """⚠️ `tom_tat` co nguoi goi khac (bo do, bao cao cu). Them mot tham so
    ⛔ khong duoc bien loi goi cu thanh `TypeError`."""
    t = nan.tom_tat([])
    assert t["tung_luot_doc"] == [] and t["so_luot_do"] == 0


def test_buoc_0_5_GHI_giay_TUNG_VONG_vao_outputs(
        tmp_path, monkeypatch,
        db, kho_tam, asr_gia, dich_gia, giong_gia):  # noqa: F811
    """⭐ Nghiem thu 5 — mot luot gia co HAI vong nan.

    May sinh tieng luon tra ve 9 giay cho khe ~0,8 giay, nen moi doan chay het
    bac thang: **3 luot doc** (vong 0, 1, 2) va `so_vong = VONG_TOI_DA`.

    🔴 Menh de that o day: giay cua vong 0 va vong 1 **truy van duoc tu
       `asv_stage.outputs`**, khong phai chi nam trong mot dong log.
    """
    import json

    from apps.auto_scan_video import ai, features, long_tieng, pipeline
    from tests.test_402_asv_mach_doc_gia import _chay_het_hang_doi, _tao_run
    from tests.test_441_asv_v4_nan_cho_vua import _tieng_dai

    _tieng_dai(monkeypatch, giay=9.0)
    dem = {"n": 0}

    def gia_nan(db_, run_, thao_tac, messages, *, stage, item_key, uoc_credit=0,
                ctx=None, temperature=None, luoc_do=None):
        if thao_tac is ai.RUT_NGAN_CHO_VUA:
            dem["n"] += 1
            than = {"doan": {"chu": "cau ngan hon lan %d" % dem["n"]}}
            return {"noi_dung": json.dumps(than, ensure_ascii=False),
                    "su_dung": None}
        goi = json.loads(messages[-1]["content"])
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
    tt = gd.outputs or {}

    luot = tt.get("tung_luot_doc")
    assert luot, "⛔ `outputs` khong mang ban ghi luot doc nao — buoc 0.5 chua lam"
    assert tt["so_luot_do"] == len(luot)

    theo_ma: dict[str, list[dict]] = {}
    for d in luot:
        theo_ma.setdefault(d["ma"], []).append(d)

    nhieu_vong = {k: v for k, v in theo_ma.items() if len(v) > 1}
    assert nhieu_vong, (
        "khong doan nao co hon mot luot doc — mau thu khong do duoc buoc 0.5 "
        "(da goi viet lai %d lan)" % dem["n"])

    for ma, cac in nhieu_vong.items():
        vongs = sorted(d["vong"] for d in cac)
        assert vongs == list(range(len(cac))), (ma, vongs)
        assert len(cac) == nan.VONG_TOI_DA + 1, (
            "tieng luon 9 giay ma doan %s chi doc %d lan" % (ma, len(cac)))
        for d in cac:
            assert d["giay"] > 0, "ban ghi khong mang giay DO DUOC"
            assert d["khe"] > 0
            assert "chu" not in d

    # ⭐ Va no truy van duoc: dem luot doc dang le phai goi may B.
    assert sum(1 for d in luot if d["nen_viet_lai"]) > 0
    assert dem["n"] > 0, "chua vong nan nao chay"
