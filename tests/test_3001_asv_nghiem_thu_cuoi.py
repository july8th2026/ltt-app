"""NGHIEM THU CUOI cua ASV — nam luot tren PHIM KHACH THAT, cap ngon ngu TUONG MINH.

## Vi sao mot tep rieng thay vi mot script scratch

Luot `NEN_V3` (23/09) chay bang mot bai pytest **scratch** dung lai `_mot_luot`
cua `test_448`. No lam duoc viec, roi bien mat cung thu muc tam — nen luot ke tiep
phai dung lai tu dau, va hai luot "nghiem thu cuoi" khong con so sanh duoc voi
nhau. Bang chung con, khuon do thi khong: do la mot bao cao khong tai lap duoc.

⇒ Nen dinh nghia nam luot nam **trong kho**, va cai gi khac giua chung la mot
  bang chu khong phai mot doi tham so tren dong lenh.

## Nam luot, va cai gi tung luot tra loi

    A  giu hinh    AUTO_MATCH      zh -> vi   R-01: AUTO_MATCH con la duong chet?
    B  giu hinh    USER_SELECTED   zh -> vi   duong san pham chinh (NEN_V3 lam moc)
    C  cat thong   USER_SELECTED   zh -> vi   R-05: `smart_localize` CO cat khong?
    D  cat thong   AUTO_MATCH      zh -> vi   hai co che doc lap, hay chung dinh nhau?
    E  giu hinh    USER_SELECTED   vi -> en   CHIEU NGUOC — cap `-> en` co song?

⭐ D ton tai vi A va C moi cai doi mot truc. Neu chi chay A/B/C thi mot khiem
   khuyet chi hien khi AUTO_MATCH **va** preset cat gap nhau se khong bi cham —
   va do dung la o giao cua hai thu vua duoc sua trong phien nay (R-01, R-05).

⭐ E khong phai mot luot "cho du bo": hop dong ngon ngu (22/09) cho dich ∈ {vi,
   en}, va bao cao NEN_V3 ghi moi luot cua khach la `auto -> vi`. Mot cap chua
   tung chay la mot cap chua tung ton tai — `-> en` phai co mot lan chay THAT
   truoc khi ai do goi no la mot tinh nang.

## ⛔ Hai dieu tep nay CO Y khong lam nhu `test_448::test_G17`

1. **Khong ep whisper ve CPU.** `test_G17` dat `LTT_AUTOSUB_WHISPER_DEVICE=cpu`,
   va do la dung cho mot bai chay giua gate. Nhung mot luot NGHIEM THU do thoi
   gian, va mot con so ASR tren CPU khong noi duoc gi ve san pham.

2. **Khong bo trong cap ngon ngu.** Bo trong thi `routes.tao` lay mac dinh
   (`auto -> vi`), nen luot E se im lang chay `-> vi` roi bao XANH.

## Cong tac

    set LTT_TEST_NANG=1            rao chan phep kiem nang (rao_chan_nang.py)
    set LTT_ASV_NT_CUOI=1          bat chinh tep nay
    set LTT_ASV_QC_AI=1            R-07: tat thi khong do lop ngu nghia/thi giac
    set LTT_ASV_MODEL_THAT=1       + LTT_ASV_POOL_URL, LTT_ASV_GIONG_THAT
    set LTT_ASV_NT_RA=<thu muc>    noi ghi JSON tung luot
    set LTT_ASV_NT_LUOT=A,B        (tuy chon) chi chay mot so luot

`setup/nghiem_thu_asv.ps1` nap `app.env` va dat bon bien dau; tep nay chi doc.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from tests import rao_chan_nang
from tests.fixtures import asv_e2e as fx
from tests import test_423_asv_giao_dien as _t423
from tests.test_448_asv_v4_e2e_nghiem_thu import _dang_ky_may, _mot_luot

import apps.ltt_voice.tables  # noqa: E402,F401  isort:skip

#: Bo canh dung chung: hai nguoi dung that, qua HTTP that, CSDL scratch.
#:
#: ⚠️ Gan bang MOT PHEP GAN chu khong `from ... import moi_truong`: mot `import`
#:    bi chinh tham so cua bai test che di, va ruff goi do la F811 (dung — mot
#:    `import` chi de bi che la mot dong de doc sai). Phep gan noi ro rang day la
#:    mot bo canh duoc DUNG LAI, khong phai mot ten bi bo quen.
moi_truong = _t423.moi_truong

#: Bat chinh tep nay. Rieng khoi `LTT_TEST_NANG` vi mot luot o day la ~10-20
#: phut tren may production — `LTT_TEST_NANG` mo qua nhieu thu de mang y nghia
#: "dong y chay nam luot nghiem thu".
BIEN_BAT = "LTT_ASV_NT_CUOI"

#: Ten phien cho `cua_so_yen`. Phai la ten LAN, khong phai mot ten chung: nguoi
#: dang cho khoa doc dong nay de biet hoi ai.
PHIEN = os.environ.get("LTT_ASV_NT_PHIEN") or "asvf-nghiem-thu-v2"


def _bat() -> bool:
    return bool(os.environ.get(BIEN_BAT, "").strip())


CHI_KHI_BAT_NT = pytest.mark.skipif(
    not _bat(), reason=f"nghiem thu cuoi ASV (nam luot that). Bat bang {BIEN_BAT}=1")


# ── Bang nam luot. MOT nguon su that. ────────────────────────────────────────

def _bang_luot() -> list[dict]:
    from apps.auto_scan_video import hop_dong_v4 as hd
    from apps.auto_scan_video import ngon_ngu as nn

    # ⚠️ **`nguon_dinh_nghia` la mot cot bat buoc, khong phai mot chu thich.**
    #
    #    Nguoi doc sau phai phan biet duoc cai DA THOA THUAN (chu du an chot,
    #    hoac mot bang chung da co) voi cai LAN NAY TU QUYET. Khong phan biet
    #    duoc thi mot lua chon cua mot lan se duoc doc nhu mot yeu cau cua chu du
    #    an — va khong ai con ra soat lai no.
    #
    # 🔑 Nen cot nay co o CA NAM luot, khong chi o D. Neu chi D co, cot do doc
    #    nhu mot loi bien bach cho mot o le; co du nam thi no la mot muc truy
    #    nguyen, va nguoi doc thay ngay bon o kia dua vao dau.
    return [
        {"ma": "A", "preset": hd.PRESET_GIU_HINH,
         "che_do_giong": hd.CHE_DO_GIONG_TU_KHOP, "giong_id": "",
         "nguon": nn.ZH, "dich": nn.VI,
         "hoi": "R-01: AUTO_MATCH con la duong chet?",
         "nguon_dinh_nghia": "bang_chung/NEN_V3.md luot A (23/09)"},
        {"ma": "B", "preset": hd.PRESET_GIU_HINH,
         "che_do_giong": hd.CHE_DO_GIONG_TU_CHON, "giong_id": "Minh Đức",
         "nguon": nn.ZH, "dich": nn.VI,
         "hoi": "duong san pham chinh (NEN_V3 lam moc so sanh)",
         "nguon_dinh_nghia": "bang_chung/NEN_V3.md luot B (23/09)"},
        {"ma": "C", "preset": hd.PRESET_CAT_THONG_MINH,
         "che_do_giong": hd.CHE_DO_GIONG_TU_CHON, "giong_id": "Minh Đức",
         "nguon": nn.ZH, "dich": nn.VI,
         "hoi": "R-05: `smart_localize` CO cat canh nao khong?",
         "nguon_dinh_nghia": "bang_chung/NEN_V3.md luot C (23/09)"},
        {"ma": "D", "preset": hd.PRESET_CAT_THONG_MINH,
         "che_do_giong": hd.CHE_DO_GIONG_TU_KHOP, "giong_id": "",
         "nguon": nn.ZH, "dich": nn.VI,
         "hoi": "giao cua R-01 va R-05 — hai co che vua sua co dinh nhau?",
         # ⛔ **Dinh nghia nay do LAN `nghiem-thu-v2` tu chot 24/09.** `PLAN.md`
         #    chi ghi *"luot that cuoi A/B/C/D"*; A/B/C suy duoc tu `NEN_V3`, D
         #    thi KHONG co o dau. Dieu phoi tan thanh cung ngay, kem dung dieu
         #    kien: ban ghi bang chung phai noi ro day la lua chon cua lan.
         "nguon_dinh_nghia": "LAN nghiem-thu-v2 TU CHOT 24/09 — KHONG co trong "
                             "PLAN.md; dieu phoi tan thanh cung ngay"},
        {"ma": "E", "preset": hd.PRESET_GIU_HINH,
         "che_do_giong": hd.CHE_DO_GIONG_TU_CHON, "giong_id": "",
         "nguon": nn.VI, "dich": nn.EN,
         "hoi": "CHIEU NGUOC — cap `-> en` co phai duong song?",
         "nguon_dinh_nghia": "PLAN.md 22/09 (hop dong: dich thuoc {vi, en}) + "
                             "brief lan (mot luot chieu nguoc)"},
    ]


def test_MOI_luot_khai_NGUON_DINH_NGHIA_cua_no():
    """⛔ Mot o trong bang ma khong noi no den tu dau la mot o khong truy duoc.

    Va bai nay chot ca chieu NGUOC lai: luot nao do LAN tu quyet thi phai noi
    thang chu do ra, khong duoc dien mot nguon nghe nhu da thoa thuan.
    """
    for l in _bang_luot():
        nguon = l.get("nguon_dinh_nghia") or ""
        assert nguon, f"luot {l['ma']} khong khai `nguon_dinh_nghia`"
    d = next(l for l in _bang_luot() if l["ma"] == "D")
    assert "TU CHOT" in d["nguon_dinh_nghia"], (
        "luot D do lan nay tu dinh nghia (PLAN.md chi ghi 'A/B/C/D'), va ban "
        "ghi phai NOI RO dieu do — xem dieu kien dieu phoi 24/09")


def test_bang_luot_phu_HAI_CHIEU_va_CA_BON_o_cua_preset_x_che_do_giong():
    """Bang nam luot phai phu het cai no tu nhan la phu. Bai NHE, chay moi gate.

    ⛔ Mot bang thieu mot o la mot bao cao noi "da nghiem thu A/B/C/D" trong khi
       mot to hop chua tung chay. Nen phep dem nay phai co hoc, khong phai mot
       cau trong tai lieu.
    """
    from apps.auto_scan_video import hop_dong_v4 as hd

    bang = _bang_luot()
    zh_vi = [l for l in bang if (l["nguon"], l["dich"]) == ("zh", "vi")]
    o = {(l["preset"], l["che_do_giong"]) for l in zh_vi}
    assert o == {(p, g) for p in hd.PRESET for g in hd.CHE_DO_GIONG}, sorted(o)
    assert {(l["nguon"], l["dich"]) for l in bang} == {("zh", "vi"), ("vi", "en")}
    assert len({l["ma"] for l in bang}) == len(bang)


def test_moi_luot_co_cap_ngon_ngu_HOP_DONG():
    """Cap nao khong hop dong thi khuon phai chet o day, khong chet giua luot."""
    from apps.auto_scan_video import ngon_ngu as nn

    for l in _bang_luot():
        assert nn.kiem_cap(l["nguon"], l["dich"]) == (l["nguon"], l["dich"])


# ── Luot chay THAT ───────────────────────────────────────────────────────────

def _phim_nghiem_thu() -> Path | None:
    """Phim khach that dung cho luot zh->vi. `None` = khong co tep nao.

    Uu tien `v3` (106,8 s, hardsub Trung, co canh dang cat) vi do la phim
    `NEN_V3` da chay — hai bao cao so sanh duoc voi nhau. Khong co thi lay tep
    dau tien theo thu tu.
    """
    ten_moi = os.environ.get("LTT_ASV_NT_PHIM", "").strip()
    if ten_moi:
        p = Path(ten_moi)
        return p if p.is_file() else None
    phim = fx.phim_khach_that()
    if not phim:
        return None
    v3 = [p for p in phim if "深度解析" in p.name]
    return (v3 or list(phim))[0]


@pytest.fixture(autouse=True)
def khoa_may():
    """Khoa may cho CA luot, giu truoc khi bat cu bo canh nao cham CSDL.

    🔴 **Thu tu la mot yeu cau, khong phai mot chi tiet.** `moi_truong` goi
       `Base.metadata.drop_all()` tren CSDL scratch DUNG CHUNG. Neu khoa
       `postgres_test` duoc giu SAU no, mot phien khac dang do co the bi keo bang
       ra tu duoi chan — va no se doc `relation "jobs" does not exist` nhu mot
       khiem khuyet san pham (su co 17/09, `tests/test_1500`).

    ⇒ Nen bo canh nay la `autouse`: pytest dung bo canh `autouse` TRUOC cac bo
      canh duoc xin tuong minh o cung pham vi. Xin no bang mot tham so dat sau
      `moi_truong` se dung SAU — tuc dung sai.

    ⛔ Va no khong giu khoa khi tep nay dang TAT: hai bai nhe o tren chay moi
       luot gate, va giu `postgres_test` cho chung la chan ca may vi hai phep
       dem tap hop.
    """
    if not _bat():
        yield None
        return
    with fx.KhoaTheoPha(PHIEN, giu_suot=("postgres_test",)) as k:
        yield k


@rao_chan_nang.NANG
@CHI_KHI_BAT_NT
def test_NGHIEM_THU_CUOI_nam_luot_tren_phim_that(moi_truong, khoa_may, tmp_path,
                                                 monkeypatch):
    """Chay nam luot, ghi mot JSON moi luot, roi chot.

    ⛔ **Chot NGAY sau tung luot, khong chot sau ca nam.** Mot `assert` o cuoi
       lam bon luot sau khong chay khi luot dau do — tuc mot khiem khuyet o luot
       A xoa sach bang chung cua B/C/D/E, va phien sau phai tra lai gia ca nam
       luot de biet dieu no da biet duoc sau luot dau.

    ⇒ Nen moi luot ghi tep NGAY khi xong, va phan chot gom o cuoi cung mot lan —
      bang chung khong phu thuoc vao phan quyet.
    """
    phim = _phim_nghiem_thu()
    if phim is None:
        pytest.skip(
            "khong co phim khach that nao. Tha 1 clip tieng Trung (2-5 phut, co "
            f"hardsub, co canh dang cat) vao {fx.THU_MUC_PHIM_THAT}, hoac chi "
            "duong dan bang LTT_ASV_NT_PHIM. Duoi nhan: " + ", ".join(fx.DUOI_PHIM))

    # ⛔ Khong co card thi DUNG. Mot luot CPU ra tep dung duoc nen no XANH, va
    #    moi con so giay cua no la so cua khuon (xem `fx.doi_hoi_card`).
    fx.doi_hoi_card()

    _app, a, csrf_a, b, _csrf_b = moi_truong

    # Cung phep bao ve nhu `test_G17`: khong co khoa thi noi ra NGAY, khong hong
    # o giua chuoi sau khi da ton demucs va ASR.
    if fx.dung_model_that():
        from platform_core.db import get_session
        so_khoa = 0
        for _db in get_session():
            so_khoa = fx.nap_khoa_pool(_db)
            _db.commit()
            break
        assert so_khoa, (
            "LTT_ASV_MODEL_THAT=1 nhung pool that khong co khoa `ltt_llm` nao "
            "dung duoc — khong co duong nao goi model that")

    # R-07: `qc_ai` TAT mac dinh, va tat thi khong do lop ngu nghia/thi giac.
    assert os.environ.get("LTT_ASV_QC_AI", "").strip(), (
        "LTT_ASV_QC_AI chua bat. Mot luot nghiem thu cuoi khong bat no thi lop "
        "ngu nghia (`qc_ngu_nghia`) va lop thi giac (`qc_hinh`) KHONG chay — va "
        "bao cao se xanh ma khong do hai thu dat nhat (R-07 trong LOI_TONG.md)")

    fx.dat_cua_model(monkeypatch, su_that=None)
    fx.dat_cua_giong(monkeypatch, tmp_path / "tieng")

    goc_s = round(float(fx.soi(str(phim))["format"]["duration"]), 3)
    ra_dir = Path(os.environ.get("LTT_ASV_NT_RA") or (tmp_path / "nt_cuoi"))
    ra_dir.mkdir(parents=True, exist_ok=True)

    chi_chay = {m.strip().upper() for m in
                os.environ.get("LTT_ASV_NT_LUOT", "").split(",") if m.strip()}
    bang = [l for l in _bang_luot() if not chi_chay or l["ma"] in chi_chay]

    luot: list[dict] = []
    # ⭐ MOT `KhoaTheoPha` cho ca nam luot (`khoa_may`): `postgres_test` va
    #    `may_tao_tieng` la tai nguyen DOC QUYEN nen giu suot la dung, con
    #    `cpu_nhieu` van chi boc tung pha TINH va nha ngay.
    khoa = khoa_may
    for l in bang:
        t0 = time.time()
        kq = _mot_luot(
            a, csrf_a, b, phim, tmp_path / f"luot_{l['ma']}",
            nhan=f"{l['ma']}::{l['nguon']}->{l['dich']}::{l['preset']}",
            preset=l["preset"], che_do_giong=l["che_do_giong"],
            giong_id=l["giong_id"], khoa=khoa,
            ngon_ngu_nguon=l["nguon"], ngon_ngu_dich=l["dich"])
        kq["ma_luot"] = l["ma"]
        kq["cau_hoi_luot"] = l["hoi"]
        # 🔑 Di theo BANG CHUNG, khong chi nam trong ma: nguoi doc bang chung la
        #    nguoi can phan biet "da thoa thuan" voi "lan nay tu quyet".
        kq["nguon_dinh_nghia_luot"] = l["nguon_dinh_nghia"]
        kq["nguon_that"] = {"ten": phim.name, "byte": phim.stat().st_size,
                            "thoi_luong": goc_s}
        kq["giay_do_ngoai"] = round(time.time() - t0, 1)
        luot.append(kq)
        # ⭐ GHI NGAY. Bang chung khong duoc phu thuoc vao phan quyet, va
        #    cung khong duoc phu thuoc vao viec bon luot con lai co chay xong.
        (ra_dir / f"luot_{l['ma']}.json").write_text(
            json.dumps(fx.sach_de_cong_bo({
                "schema": "asv.final.nghiem_thu_cuoi.1",
                "ghi_luc": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "may": _dang_ky_may(),
                "luot": kq,
            }), ensure_ascii=False, indent=2), encoding="utf-8")

    (ra_dir / "tat_ca.json").write_text(
        json.dumps(fx.sach_de_cong_bo({
            "schema": "asv.final.nghiem_thu_cuoi.1",
            "ghi_luc": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "may": _dang_ky_may(), "phim": phim.name, "goc_s": goc_s,
            "luot": luot,
        }), ensure_ascii=False, indent=2), encoding="utf-8")

    # ── Chot, sau khi bang chung da nam tren dia ────────────────────────────
    hong: list[str] = []
    for kq in luot:
        ma = kq["ma_luot"]
        if kq["trang_thai_run"] != "done":
            hong.append(f"{ma}: run {kq['trang_thai_run']} — "
                        f"{kq.get('vi_sao_hong')}")
            continue
        if not kq["ra"]:
            hong.append(f"{ma}: khong co tep ban giao")
            continue
        if not kq["qc"]["dat"]:
            hong.append(f"{ma}: QC do o {kq['qc']['muc_hong']}")
        ra_s = kq["ra"]["thoi_luong"]
        if ra_s > goc_s + 1.0:
            hong.append(f"{ma}: ban ra {ra_s:.2f}s DAI hon nguon {goc_s:.2f}s")
        if kq["preset"].endswith("preserve_picture") and abs(ra_s - goc_s) > 1.0:
            hong.append(f"{ma}: preset GIU HINH doi do dai "
                        f"{goc_s:.2f} -> {ra_s:.2f}")
        if kq["doi_soat"].get("khop") is False:
            hong.append(f"{ma}: so ke lech doi soat — {kq['doi_soat']}")
        # ⛔ Card: mot luot "xanh" ma khong pha nao duoc card la mot luot do
        #    KHUON, khong do san pham (xem `fx.khai_card`).
        card = kq.get("card") or {}
        if card.get("pha_doi_card") and not card.get("pha_duoc_card"):
            hong.append(f"{ma}: KHONG pha nao duoc card — moi con so giay cua "
                        f"luot nay la so cua CPU, khong phai cua san pham")
    assert not hong, "\n".join(hong) + f"\n\nBang chung: {ra_dir}"
