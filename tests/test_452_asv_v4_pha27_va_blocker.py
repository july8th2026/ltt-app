"""Pha 27 — mot phep kiem tai hien cho MOI blocker da sua.

## Vi sao mot tep rieng thay vi rai vao cac tep san co

Chin phat hien cua pha 26 khong phai chin loi doc lap — kiem toan ket luan
chung la **mot thoi quen lap lai nam lan**: mot nang luc duoc viet xong, co test
don vi xanh, va khong bao gio duoc noi vao mot duong chay that. Rai cac phep
kiem nay vao chin tep khac nhau se lam mat dung dieu do.

⛔ Va tung phep kiem o day duoc viet de **DO** khi ban va bi go ra, khong phai
   de xanh khi ma "trong co ve dung". Moi phep kiem ghi kem cach tai hien
   khiem khuyet goc.
"""
from __future__ import annotations

import ast
import inspect
import json
from datetime import timedelta
from pathlib import Path

import pytest

from apps.auto_scan_video import (ai, assets, ban_bien_tap, che_do_render as cdr,
                                  giai_doan_ban_bien_tap as gdbbt,
                                  giai_doan_ket_xuat, hieu_canh as hc,
                                  ket_xuat, pipeline, thi_hanh)

GOC = Path(__file__).resolve().parents[1]
APP = GOC / "apps" / "auto_scan_video"


def _thuoc_tinh(ham) -> set[str]:
    """Ten moi thuoc tinh MA NGUON truy cap trong `ham`. Chu thich khong tinh.

    ⛔ Ly do ton tai: mot phep tim chuoi tren ma nguon bao dong tren chinh doan
       giai thich vi sao khiem khuyet da het — va doan cang viet ky thi phep
       kiem cang do. Bay nay da dinh ba lan trong kho nay.
    """
    cay = ast.parse(inspect.getsource(ham))
    return {n.attr for n in ast.walk(cay) if isinstance(n, ast.Attribute)}


def _ten_duoc_goi(ham) -> set[str]:
    """Ten moi thu duoc GOI trong `ham`."""
    cay = ast.parse(inspect.getsource(ham))
    ra = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.Call):
            f = n.func
            ra.add(f.id if isinstance(f, ast.Name) else getattr(f, "attr", ""))
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  B22-01 — VLM chua tung duoc hoi mot cau nao
# ══════════════════════════════════════════════════════════════════════════════

def test_EDIT_PLAN_THUC_SU_goi_VLM_chu_khong_truyen_hieu_rong():
    """Tai hien: truoc pha 27 than ham `chay` chua dung mot dong `hieu = ()`.

    ⭐ Doc bang AST chu khong bang chuoi: mot phep tim `"hieu = ()"` se xanh tro
       lai ngay khi ai do doi khoang trang, va do la mot phep kiem do chinh tri
       chinh ta cua ma nguon.
    """
    cay = ast.parse(inspect.getsource(gdbbt.chay))
    gan_hieu = [n for n in ast.walk(cay) if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "hieu"
                        for t in n.targets)]
    assert gan_hieu, "`chay` khong con gan `hieu` — phep kiem nay da lac"

    # ⭐ `hieu = ()` VAN dung o nhanh `PRESET_GIU_HINH`, va do la dung: preset
    #    giu hinh khong duoc phep cat, nen mot y kien ve viec nen cat gi la mot
    #    y kien khong duoc dung toi. Dieu phai sai la mot phep gan RONG **vo
    #    dieu kien** — tuc khong nhanh nao dan toi mot loi goi VLM.
    def _co_goi_doc_canh(nut) -> bool:
        return any(getattr(getattr(c, "func", None), "id", "") == "_doc_cac_canh"
                   or getattr(getattr(c, "func", None), "attr", "") == "_doc_cac_canh"
                   for c in ast.walk(nut) if isinstance(c, ast.Call))

    assert any(_co_goi_doc_canh(n) for n in gan_hieu), (
        "khong nhanh nao cua `chay` dan `hieu` toi mot loi goi VLM")

    assert "_doc_cac_canh" in _ten_duoc_goi(gdbbt.chay)
    assert "goi_tinh_tien" in _ten_duoc_goi(gdbbt._doc_cac_canh), (
        "duong doc canh khong di qua cua tra tien")


def test_loi_nhac_canh_GUI_KHUNG_HINH_that_dang_OpenAI():
    """🔴 Truoc pha 27 loi nhac chi NOI "co N khung hinh", khong gui khung nao.

    Tuc `can_thi_giac=True` chon model thi giac, roi ta hoi no mot cau ma mot
    model van ban tra loi duoc y het — va cau tra loi se "trong nhu that ve mot
    buc anh model chua bao gio nhin thay".
    """
    khung = (b"\xff\xd8\xff\xe0gia-lap-jpeg-1", b"\xff\xd8\xff\xe0gia-lap-jpeg-2")
    tin = hc.loi_nhac_canh("canh_0001", "xin chao", len(khung), {"a": 1}, khung)
    assert len(tin) == 1
    noi_dung = tin[0]["content"]
    assert isinstance(noi_dung, list), "tin nhan khong phai da phuong thuc"
    anh = [p for p in noi_dung if p.get("type") == "image_url"]
    assert len(anh) == len(khung), f"gui {len(anh)}/{len(khung)} khung"
    for p in anh:
        assert p["image_url"]["url"].startswith("data:image/jpeg;base64,")

    # Khong khung thi van gui duoc phan van ban — mot lan rut khung hong khong
    # duoc lam chet ca giai doan.
    chi_van = hc.loi_nhac_canh("canh_0001", "xin chao", 0, {}, ())
    assert isinstance(chi_van[0]["content"], str)


def test_MOT_hinh_dang_luoc_do_o_ca_BA_cho():
    """🔴 Ba ban mo ta tung lech nhau, va khong ban nao chay.

    Loi nhac hoi mot doi tuong PHANG · `DOC_CANH.truong_bat_buoc` khai
    `("canh",)` · `doc_hieu_canh` chiu ca hai hinh dang. Nen mot phan hoi lam
    **dung y nguyen loi dan** bi tu choi voi "thieu truong bat buoc ['canh']".
    """
    assert ai.DOC_CANH.truong_bat_buoc == ("de_xuat", "do_tin")

    phang = json.dumps({"loai": "canh", "chu_the": [], "hanh_dong": "",
                        "cam_xuc": "", "quan_trong": 0.2, "de_xuat": "bo",
                        "do_tin": 0.9, "ly_do": "khong co thoai",
                        "canh_bao": []})
    h = hc.doc_hieu_canh({"noi_dung": phang}, "canh_0001")
    assert h.de_xuat == hc.BO and h.do_tin == pytest.approx(0.9)

    # Va lop boc kia nay bi TU CHOI thay vi duoc chieu — mot hinh dang, mot lan.
    with pytest.raises(ai.LuocDoSai):
        hc.doc_hieu_canh({"noi_dung": json.dumps(
            {"canh": {"de_xuat": "bo", "do_tin": 0.9}})},
                         "canh_0001")


def test_diem_chot_theo_canh_doc_lai_duoc():
    """`sang_dict` -> `tu_dict` phai la mot vong tron kin, neu khong diem chot
    chi la mot dong ghi khong ai doc lai."""
    goc = hc.HieuCanh(ma_canh="canh_0007", loai="hoi thoai",
                      chu_the=("a", "b"), hanh_dong="noi", cam_xuc="vui",
                      quan_trong=0.75, de_xuat=hc.GIU, do_tin=0.9,
                      ly_do="co thoai", canh_bao=("mo",))
    assert hc.tu_dict(goc.sang_dict()) == goc


def test_ban_bien_tap_CAT_khi_co_bang_chung_du_manh():
    """Mach day du: co `HieuCanh` de xuat bo voi do tin tren nguong => CAT.

    ⚠️ Canh KHONG co loi thoai, nen nguong la `NGUONG_BO` chu khong phai
       `NGUONG_BO_CO_THOAI` — hai nguong khac nhau la mot chinh sach, va mot
       phep kiem dung nham nguong se xanh vi ly do khong lien quan.
    """
    from apps.auto_scan_video import canh as cn
    from apps.auto_scan_video.hop_dong_v4 import PRESET_CAT_THONG_MINH

    canh = tuple(cn.Canh(f"canh_{i:04d}", i * 10.0, i * 10.0 + 10.0)
                 for i in range(4))
    ci = cn.ChiMucCanh(canh, 40.0)
    hieu = [hc.HieuCanh(ma_canh="canh_0003", de_xuat=hc.BO,
                        do_tin=ban_bien_tap.NGUONG_BO + 0.05)]
    ban = ban_bien_tap.lap_ban(preset=PRESET_CAT_THONG_MINH, chi_muc=ci,
                              hieu_canh=hieu, ban_ghi={})
    assert "canh_0003" in ban.cac_ma_cat, ban.ghi_chu


# ══════════════════════════════════════════════════════════════════════════════
#  B24-01 — bo ma hoa phan cung khong voi toi duoc
# ══════════════════════════════════════════════════════════════════════════════

def test_asv_media_khai_VRAM_cho_render_va_KHONG_doi_them_nang_luc():
    """Khai `gpu_vram_mb` la thu lam `ctx.gpu_uuid` co gia tri.

    ⛔ Va no khong duoc keo theo `requires=("gpu",)`: `jobs.py` loc worker theo
       `requires`, nen mot app khai ca `ffmpeg` lan `gpu` se vo hinh voi moi
       worker tren doi hinh chia lan — dung cai bay ma docstring cua chinh
       `asv_media/manifest.py` mo ta.
    """
    from apps.asv_media.manifest import MANIFEST as M

    assert M.vram_for("asv_media.render") > 0, "RENDER khong xin duoc GPU nao"
    assert set(M.requires) == {"ffmpeg"}, (
        f"asv_media doi them nang luc {set(M.requires)} — se vo hinh voi worker")
    # Cac giai doan khong ma hoa thi khong duoc xin card.
    for jt in ("asv_media.compose", "asv_media.qc", "asv_media.timing_align"):
        assert M.vram_for(jt) == 0, f"{jt} xin GPU ma khong ma hoa gi"


def test_COMPOSE_khong_con_quyet_dinh_bo_ma_hoa_bang_lease_cua_chinh_no():
    """🔴 COMPOSE va RENDER la HAI job, va mot lease chet theo job.

    Nen `co_gpu = bool(ctx.gpu_uuid)` o COMPOSE hoi mot cau ma cau tra loi khong
    bao gio con hieu luc luc ffmpeg chay. Do la ly do B24-01 khong sua duoc bang
    mot dong khai bao.
    """
    from apps.auto_scan_video import giai_doan_ban_dung

    assert "gpu_uuid" not in _thuoc_tinh(giai_doan_ban_dung.chay), (
        "COMPOSE van doc `ctx.gpu_uuid` — mot lease no khong the giu toi RENDER")

    # Va no van phai ghi TRAN KHAI BAO, khong phai bo han quyet dinh.
    cay = ast.parse(inspect.getsource(giai_doan_ban_dung.chay))
    kw = [k for n in ast.walk(cay) if isinstance(n, ast.Call)
          for k in n.keywords if k.arg == "cho_phep_gpu"]
    assert kw and all(getattr(k.value, "value", None) is True for k in kw), (
        "COMPOSE khong ghi tran khai bao cua may")


def test_RENDER_chi_duoc_HA_bo_ma_hoa_khong_bao_gio_duoc_NANG():
    ban_nvenc = {"hinh": {"bo_ma_hoa": "h264_nvenc"}}
    assert ket_xuat.bo_ma_hoa_thuc_te(ban_nvenc, co_gpu=True) == "h264_nvenc"
    assert ket_xuat.bo_ma_hoa_thuc_te(ban_nvenc, co_gpu=False) == cdr.LUI_VE

    # ⛔ Duoc cap card KHONG duoc nang mot ban dung da khai CPU: van tay cua ban
    #    dung gom `bo_ma_hoa`, nen tra ve mot tep ma hoa bang thu khac voi thu da
    #    khai la mot cache se tra sai ve sau.
    ban_cpu = {"hinh": {"bo_ma_hoa": cdr.LUI_VE}}
    assert ket_xuat.bo_ma_hoa_thuc_te(ban_cpu, co_gpu=True) == cdr.LUI_VE
    assert ket_xuat.bo_ma_hoa_thuc_te({"hinh": {}}, co_gpu=True) == ""


def test_ffmpeg_duoc_GHIM_vao_card_duoc_cap():
    """Duoc cap card ma khong ghim thi nen tang giu cho mot dang, ffmpeg dung
    mot neo — va hai job "duoc xep cho tu te" van dam nhau."""
    assert "env" in inspect.signature(ket_xuat._chay_co_tien_do).parameters
    assert "gpu_env()" in inspect.getsource(giai_doan_ket_xuat)


# ══════════════════════════════════════════════════════════════════════════════
#  B23-01 + A26-01 — cache chua tung trung, va van tay khong mang danh tinh model
# ══════════════════════════════════════════════════════════════════════════════

def test_cache_giai_doan_KHONG_con_doan_tu_TEN_TEP():
    """🔴 **Khiem khuyet nay co HAI tang, va ban va dau tien cua toi chi cham tang mot.**

    Tang mot: loc bang `f"/{van_tay}." in storage_key` voi van tay 64 ky tu,
    trong khi `dat_khoa` cat con 32. Cat cho khop la du de dong tang do — va toi
    da ghi B23-01 la FIXED sau khi lam dung nhu the.

    Tang hai, va la tang that: khoa mang van tay cua **TUNG ARTIFACT**, khong
    phai cua GIAI DOAN. Do that: mot lan `media_prepare` ghi hai artifact duoi
    hai van tay khac nhau. Nen **khong** gia tri don nao trong `storage_key` tra
    loi duoc cau hoi dang hoi. `xfail(strict)` o `test_449` van do, va no dung.

    ⇒ Cau hoi "giai doan nay da chay xong voi van tay nay chua" duoc hoi o cho
      duy nhat ghi lai dieu do: `AsvStage.fingerprint`.
    """
    goc = _ten_duoc_goi(assets.cache_dung_duoc)
    thuoc = _thuoc_tinh(assets.cache_dung_duoc)
    assert "fingerprint" in thuoc, "cache khong doc van tay cua GIAI DOAN"
    assert "storage_key" in thuoc, "cache khong doi chieu danh sach artifact"
    # ⛔ Va no khong duoc quay lai doan tu ten tep: khong cat chuoi, khong so
    #    khop chuoi con.
    cay = ast.parse(inspect.getsource(assets.cache_dung_duoc))
    assert not [n for n in ast.walk(cay) if isinstance(n, ast.Compare)
                and any(isinstance(o, ast.In) for o in n.ops)
                and isinstance(n.left, ast.JoinedStr)], (
        "cache van doan quan he giai doan/artifact bang mot phep so khop chuoi")
    assert "DAI_VAN_TAY_TRONG_KHOA" not in goc | thuoc

    # Va `dat_khoa` VAN cat — de nguoi doc sau khong tuong hai thu da bang nhau.
    van_tay = "a" * 64
    khoa = assets.dat_khoa(owner_id="u1", run_id="r1", stage="edit_plan",
                           van_tay=van_tay, duoi="json")
    assert f"/{van_tay}." not in khoa
    assert f"/{van_tay[:assets.DAI_VAN_TAY_TRONG_KHOA]}." in khoa


def test_van_tay_CONTENT_PROCESS_mang_DANH_TINH_MODEL_dang_chay():
    """🔴 No tung doc `dich_thuat.MODEL_CHINH` — mot hang so RONG cua mot module
    khong con nguoi goi tu pha 14, trong khi `qwen38-api` moi la thu dang chay.

    ⇒ Doi model that thi van tay khong doi, nen khong gi bi vo hieu; con sua cai
      hang so chet kia thi LAI vo hieu ca cache ma khong co gi that su doi.
    """
    v = thi_hanh.phien_ban_engine(pipeline.CONTENT_PROCESS)
    model = ai.model_cho(ai.CHUYEN_LOI_THOAI)
    assert model and model in v, f"van tay {v!r} khong chua model {model!r}"

    assert "MODEL_CHINH" not in _thuoc_tinh(thi_hanh.phien_ban_engine), (
        "van tay van doc hang so cua module da chet")
    assert "ban_do_model" in _ten_duoc_goi(thi_hanh.phien_ban_engine), (
        "van tay khong hoi ban do model SONG")


# ══════════════════════════════════════════════════════════════════════════════
#  A26-02 — `revision` duoc hua la mot chot, va chua tung la
# ══════════════════════════════════════════════════════════════════════════════

def test_danh_dau_xong_dung_UPDATE_CO_DIEU_KIEN_theo_revision():
    from apps.auto_scan_video import su_dung

    goi = _ten_duoc_goi(su_dung.danh_dau_xong)
    assert "update" in goi, (
        "`danh_dau_xong` van ghi de bang mot phep gan ORM tran")
    assert "XungDotDonVi" in goi, "mot cuoc dua van ket thuc trong im lang"
    assert "revision" in _thuoc_tinh(su_dung.danh_dau_xong)


# ══════════════════════════════════════════════════════════════════════════════
#  A26-03 — duong tai len truc tiep doc ca tep vao RAM
# ══════════════════════════════════════════════════════════════════════════════

def test_duong_tai_len_KHONG_doc_ca_tep_vao_RAM_va_ap_tran_TRONG_luc_chay():
    """G6 nguyen van: *"production path does not `await read()` entire large
    video into RAM"*.

    ⛔ Va te hon ca viec cap phat: tran 90 MB tung duoc kiem o dong NGAY SAU
       `read()`, tuc mot tep 100 MB van duoc cap phat du 100 MB truoc khi bi tu
       choi — mot quyet dinh "co nhan khong" dat sau hanh dong ma no le ra phai
       chan.
    """
    from apps.auto_scan_video import features, routes

    cay = ast.parse(inspect.getsource(routes.tao))
    for nut in ast.walk(cay):
        if (isinstance(nut, ast.Await) and isinstance(nut.value, ast.Call)
                and getattr(nut.value.func, "attr", "") == "read"):
            assert nut.value.args, (
                "`await video.read()` khong tham so — doc ca tep vao RAM")

    assert "KHOI_TAI_LEN" in {n.id for n in ast.walk(cay)
                             if isinstance(n, ast.Name)}, (
        "route khong chay theo khoi")
    # Va tang nghiep vu nhan mot DUONG DAN, khong nhan bytes.
    tham_so = inspect.signature(features.tao_run_tu_tai_len).parameters
    assert "duong_tep" in tham_so and "du_lieu" not in tham_so


# ══════════════════════════════════════════════════════════════════════════════
#  B25-01 — han luu tru duoc khai, chua tung duoc quet
# ══════════════════════════════════════════════════════════════════════════════

def test_app_KHAI_viec_bao_tri_va_no_KHONG_NEM():
    """Nen tang da co moc `AppManifest.bao_tri` tu 24/08; app chua tung khai.

    ⛔ Hop dong doi ham nay khong duoc nem: nen tang bat va ghi log, nhung mot
       app nem moi luot la mot dong log rac moi gio, va no che nhung loi that.
    """
    from apps.auto_scan_video.manifest import MANIFEST as M

    assert M.bao_tri is not None, "app khong khai viec nen — khong ai quet han"
    assert M.bao_tri_moi_giay >= 60
    M.bao_tri()          # khong CSDL, khong kho: van phai im lang tro ve


def test_bo_quet_chi_cham_thu_DA_HET_HAN(tmp_path):
    """⛔ `don_theo_run` xoa MOI artifact cua mot lan chay — ke ca ban giao.
    Bo quet han phai la mot ham KHAC, va no chi doc `expires_at`."""
    assert "expires_at" in _thuoc_tinh(assets.quet_het_han)
    assert "don_theo_run" not in _ten_duoc_goi(assets.quet_het_han), (
        "bo quet han goi ham xoa CA lan chay — ke ca ban giao cho khach")
    # Chan tren mot luot: bo quet chay duoi lease `bao_tri`, giu no qua lau la
    # chan moi viec nen khac cua ca cum.
    assert "toi_da" in inspect.signature(assets.quet_het_han).parameters


def test_BAN_GIAO_khong_co_han_con_ban_trung_gian_thi_co():
    """🔑 Hai thay doi phai di cung nhau.

    Truoc pha 27, `HAN_TRUNG_GIAN` dong len MOI thu ke ca tep khach tai ve — vo
    hai theo mot cach rat xau, vi khong bo quet nao ton tai. Noi bo quet vao ma
    khong sua dong nay la bien mot cai nhan vo hai thanh mot lenh **xoa video
    cua khach sau 30 ngay**, va no im lang trong 30 ngay truoc khi lo ra.
    """
    cay = ast.parse(inspect.getsource(thi_hanh.chay_giai_doan))
    han = [k for n in ast.walk(cay) if isinstance(n, ast.Call)
           for k in n.keywords if k.arg == "han"]
    assert han, "`promote_va_ghi` duoc goi khong kem `han` — moi thu deu 30 ngay"
    assert any(isinstance(k.value, ast.IfExp) for k in han), (
        "`han` khong phu thuoc vao viec day co phai ban giao hay khong")
    assert isinstance(assets.HAN_TRUNG_GIAN, timedelta)

# ══════════════════════════════════════════════════════════════════════════════
#  A29-06 · P1 · id cua lan chay phai VUA cot so tien
# ══════════════════════════════════════════════════════════════════════════════

def test_ma_lan_chay_VUA_cot_job_id_cua_so_credit():
    """🔴 **Mot ky tu, va no lam luot chay TRA TIEN dau tien chet o production.**

        AsvRun.id             = "asvr_" + 32 hex = 37 ky tu
        credit_entries.job_id = VARCHAR(36)      <- truoc ban va

    `features.py` truyen `run.id` vao `credit.giu_cho(...)`. PostgreSQL cuong
    che do dai cot; SQLite coi no la mot **goi y**. Moi bai test cua Auto Scan
    chay tren SQLite, production chay PostgreSQL, va Auto Scan chua tung chay o
    production — nen khong con duong nao khac de bat duoc no.

    ⭐ Phep kiem nay do QUAN HE giua hai lo so, khong go lai con so nao. Doi
       `sinh_id` cho dai hon, hay ha cot xuong, deu lam no do — va do la dung
       hai huong ma khiem khuyet nay co the quay lai.
    """
    from platform_core.models import CreditEntry
    from apps.auto_scan_video.tables import sinh_id

    cot = CreditEntry.__table__.c.job_id.type.length
    assert cot, "credit_entries.job_id khong khai do dai"

    # Sinh nhieu lan: mot lo id co the doi dai theo tung lan (vd base62).
    for _ in range(20):
        ma = sinh_id()
        assert len(ma) <= cot, (
            f"ma lan chay dai {len(ma)} ky tu, cot job_id chi chua {cot} — "
            "mot but toan credit se hong tren PostgreSQL")


def test_moi_ID_CO_TIEN_TO_cua_ASV_deu_vua_cot_no_di_qua():
    """⛔ Cung mot cau hoi, hoi cho MOI bang cua ASV mang khoa ngoai kieu chuoi.

    ⚠️ Doc do dai tu CHINH cac cot, khong go lai: mot phep kiem go lai con so se
       van xanh sau khi ai do ha mot cot xuong.
    """
    from apps.auto_scan_video.tables import (AsvAsset, AsvRun, AsvStage,
                                             AsvUsage, AsvWorkItem, sinh_id)

    ma = sinh_id()
    for bang, cot in ((AsvRun, "id"), (AsvStage, "run_id"), (AsvAsset, "run_id"),
                      (AsvUsage, "run_id"), (AsvWorkItem, "run_id")):
        dai = bang.__table__.c[cot].type.length
        assert dai and len(ma) <= dai, (
            f"{bang.__tablename__}.{cot} chua duoc {dai} ky tu, "
            f"ma lan chay dai {len(ma)}")


# ══════════════════════════════════════════════════════════════════════════════
#  B22-01 lan hai: luoc do KHAI khong khop luoc do LOI NHAC DOI
# ══════════════════════════════════════════════════════════════════════════════

def test_phan_hoi_TUAN_THU_LOI_NHAC_phai_duoc_chinh_ta_CHAP_NHAN():
    """🔴 **Mot phan hoi tuan thu DUNG loi nhac cua ta tung bi CHINH TA tu choi.**

        loi nhac doi : {"doan": {"<ma>": {"dat": ..., "ly_do": ...}}}
        khai bao     : truong_bat_buoc = ("dat", "ly_do")
        `doc_json`   : kiem o TANG NGOAI CUNG  ->  `t not in ra`

    `dat`/`ly_do` nam o tang TRONG, moi ma mot ban. Nen mot model ngoan ngoan
    nhat cung bi `LuocDoSai: thieu truong bat buoc ['dat', 'ly_do']`.

    ⭐ Dung khiem khuyet pha 27 sua cho `DOC_CANH` (khai `("canh",)` — mot hinh
       dang khong ai san xuat). Lan nay no nam trong duong QC ngu nghia, **chua
       tung chay**, nen no doi den luot goi TRA TIEN dau tien moi lo ra.

    🔑 Bai nay dung phan hoi **dung tu chinh loi nhac**, khong go lai hinh dang:
       doi loi nhac ma quen doi khai bao thi bai nay do, va do la ca muc dich.
    """
    import json
    import re

    from apps.auto_scan_video import ai, qc_ai

    tin = qc_ai.loi_nhac_ngu_nghia(
        [{"ma": "seg_0001", "goc": "Good morning", "chu": "Chao buoi sang"}])
    he_thong = next(t["content"] for t in tin if t["role"] == "system")

    # Hinh dang loi nhac TU KHAI: lay khoa tang ngoai tu chinh cau "Tra ve DUY NHAT".
    m = re.search(r'Tra ve DUY NHAT:\s*\{"([a-z_]+)"', he_thong)
    assert m, ("loi nhac khong con cau `Tra ve DUY NHAT: {\"...\"` — bai nay doc "
               "hinh dang tu do, nen phai sua bai truoc khi sua loi nhac")
    khoa_ngoai = m.group(1)

    assert khoa_ngoai in ai.QC_NGU_NGHIA.truong_bat_buoc, (
        f"loi nhac doi tang ngoai la {khoa_ngoai!r}, nhung ThaoTac khai "
        f"{ai.QC_NGU_NGHIA.truong_bat_buoc!r} — mot phan hoi tuan thu se bi tu choi")

    # Va chot bang HANH VI, khong chi bang so sanh hai khai bao.
    tuan_thu = json.dumps(
        {khoa_ngoai: {"seg_0001": {"dat": True, "do_tin": 0.9, "ly_do": ""}}})
    ra = ai.doc_json(tuan_thu, ai.QC_NGU_NGHIA)
    assert khoa_ngoai in ra

    # Va no phai doc duoc bang chinh ham doc cua `qc_ai`.
    phan = qc_ai.doc_ngu_nghia(ra, {"seg_0001"})
    assert phan and phan[0]["ma"] == "seg_0001" and phan[0]["dat"] is True
