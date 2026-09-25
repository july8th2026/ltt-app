"""B4 — HAI GIAI DOAN: cat cảnh nam SAU render, tren MP4 da xong.

Nam nhom, theo dung nam phep nghiem thu chu du an chot 25/09:

  A. Mot duong voice  — hai preset di Y HET o giai doan 1 (nghiem thu 1+2)
  B. Chuoi            — `image_finish` GIUA `render` va `qc`, va no la BAN GIAO
  C. Cat CUNG NHAU    — hinh va tieng qua CUNG mot `concat` (nghiem thu 4)
  D. Giu hinh         — preset `localize_preserve_picture` van KHONG cat gi
  E. Ai con dung ban_do_thoi_gian, va VI SAO (nghiem thu 5)
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from apps.auto_scan_video import (che_do_render as cdr, giai_doan_hinh_anh as gdha,
                                  hop_dong_v4, ke_cat as kc, pipeline as P,
                                  thoi_gian as tg)

GOC = Path(P.__file__).parent


# ══════════════════════════════════════════════════════════════════════════════
#  A. Mot duong voice cho CA HAI preset (nghiem thu 1 + 2)
# ══════════════════════════════════════════════════════════════════════════════

def test_giai_doan_1_KHONG_CO_mot_nhanh_preset_nao_tren_duong_voice():
    """🔴 Nghiem thu 2: *"hai preset dung CHUNG duong voice — ghim bang phep
    kiem, ⛔ khong bang giao uoc"*.

    ⭐ Chot bang **CAU TRUC** chu khong bang hai lan chay: mot phep do chi noi
       rang hai lan chay HOM NAY trung nhau; cay cu phap noi rang chung ⛔ khong
       co cho nao de tach ra.

    Bon module cua duong voice: lap ke hoach, tron ban phoi, va giai doan bao
    quanh chung. ⛔ Khong mot cai nao duoc doc `preset` hay `hop_dong_v4.PRESET*`.
    """
    for ten in ("thoi_gian.py", "giai_doan_thoi_gian.py", "am_master.py"):
        van = (GOC / ten).read_text(encoding="utf-8")
        cay = ast.parse(van)
        ten_doc = {n.attr for n in ast.walk(cay)
                   if isinstance(n, ast.Attribute)}
        xau = {t for t in ten_doc if t.startswith("PRESET")}
        assert not xau, f"{ten} doc {sorted(xau)} — duong voice phai mu preset"
        # `cai_dat.doc(run).preset` di qua truong `.preset`, nen chot ca no.
        assert "preset" not in ten_doc, f"{ten} doc truong `preset`"


def test_lap_ke_hoach_KHONG_CON_tham_so_ban_do():
    """Nghiem thu 1, nua thu hai: *"`lap_ke_hoach` ⛔ khong con nhanh preset"*."""
    tham = set(inspect.signature(tg.lap_ke_hoach).parameters)
    assert "ban_do" not in tham
    assert tham == {"muc", "thoi_luong_tieng", "tong_giay", "che_do", "nhom_gop"}


def test_ke_hoach_cua_hai_preset_LA_MOT__tren_cung_dau_vao():
    """⭐ Doi chung hanh vi cho phep kiem cau truc o tren.

    Ham ⛔ khong nhan preset, nen ⛔ khong co cach nao goi no "theo preset" — hai
    lan goi giong nhau la hai ke hoach giong nhau tung byte.
    """
    muc = [{"ma": f"seg_{i:04d}", "bat": i * 10.0, "ket": i * 10.0 + 2.0}
           for i in range(4)]
    dai = {m["ma"]: 1.5 for m in muc}
    a = tg.lap_ke_hoach(muc, dai, tong_giay=40.0)
    b = tg.lap_ke_hoach(muc, dai, tong_giay=40.0)
    assert a == b
    # Va do dai ra = do dai NGUON: giai doan 1 ⛔ khong cat gi.
    assert a["tong_ms"] == a["thoi_luong_nguon_ms"] == 40_000


# ══════════════════════════════════════════════════════════════════════════════
#  B. Chuoi — vi tri, va BAN GIAO
# ══════════════════════════════════════════════════════════════════════════════

def test_image_finish_nam_GIUA_render_va_qc():
    """⭐ Hai ranh gioi, hai ly do — xem chu thich o `pipeline.IMAGE_FINISH`."""
    thu_tu = {g.ten: i for i, g in enumerate(P.CHUOI)}
    assert thu_tu[P.RENDER] < thu_tu[P.IMAGE_FINISH] < thu_tu[P.QC]
    assert P.THEO_TEN[P.IMAGE_FINISH].sau == (P.RENDER,)
    assert P.THEO_TEN[P.QC].sau == (P.IMAGE_FINISH,)


def test_BAN_GIAO_la_image_finish__KHONG_con_la_render():
    """🔴 Thieu buoc chuyen nay thi video khach tai ve mang `HAN_TRUNG_GIAN`.

    ⛔ Doc AST chu khong chay: `la_ban_giao` quyet dinh `han=None`, va mot lan
       chay thu khong the phan biet "chua het han" voi "khong co han".
    """
    van = (GOC / "thi_hanh.py").read_text(encoding="utf-8")
    cay = ast.parse(van)
    gan = [n for n in ast.walk(cay)
           if isinstance(n, ast.Assign)
           and any(getattr(t, "id", "") == "la_ban_giao" for t in n.targets)]
    assert len(gan) == 1, "`la_ban_giao` phai duoc khai o DUNG mot cho"
    assert "IMAGE_FINISH" in ast.unparse(gan[0].value)
    assert "RENDER" not in ast.unparse(gan[0].value)


def test_khoa_ban_giao_doc_image_finish__ca_mp4_lan_srt():
    """⛔ `.srt` cua `render` nam tren truc GD1 ⇒ sau khi cat no TRE."""
    van = (GOC / "features.py").read_text(encoding="utf-8")
    cay = ast.parse(van)
    for ten in ("khoa_ket_qua", "khoa_phu_de"):
        ham = next(n for n in ast.walk(cay)
                   if isinstance(n, ast.FunctionDef) and n.name == ten)
        goi = ast.unparse(ham)
        assert "pipeline.IMAGE_FINISH" in goi, ten
        assert "pipeline.RENDER" not in goi, ten


def test_image_finish_khai_du_ba_truong_hop_dong():
    """I2/I4: mot giai doan moi ⛔ khong duoc lot vao chuoi voi o rong."""
    assert P.thieu_khai() == []
    g = P.THEO_TEN[P.IMAGE_FINISH]
    assert g.app_slug == "asv_media" and g.job_type == "asv_media.image_finish"
    assert len(g.tien_quyet) >= 4 and g.do


def test_manifest_asv_media_KHAI_job_type_va_tran_thoi_gian():
    """⛔ Thieu khai thi job nam `queued` MAI MAI, ⛔ khong loi nao bao."""
    from apps.asv_media.manifest import MANIFEST

    assert "asv_media.image_finish" in MANIFEST.job_types
    # `lat_cat.tran_giai_doan` doc chinh bang nay de dat timeout tien trinh con.
    assert MANIFEST.max_runtime_s["asv_media.image_finish"] > 0
    # ⭐ Xin GPU y het `render`: no cung ma hoa lai ca luong hinh.
    assert (MANIFEST.gpu_vram_mb["asv_media.image_finish"]
            == MANIFEST.gpu_vram_mb["asv_media.render"])


def test_van_tay_engine_cua_image_finish_bam_CA_chinh_sach_cat():
    """⛔ Doi tran hay thu tu uu tien ma van tay khong doi thi mot lan chay lai
    dung lai ban giao cat theo luat CU — im lang."""
    from apps.auto_scan_video import thi_hanh

    vt = thi_hanh.phien_ban_engine(P.IMAGE_FINISH)
    assert str(kc.PHIEN_BAN_KE_CAT) in vt
    assert str(gdha.PHIEN_BAN_HINH_ANH) in vt
    assert str(cdr.PHIEN_BAN_CHE_DO) in vt
    assert not vt.startswith("gia/"), "khong duoc roi xuong engine GIA"


# ══════════════════════════════════════════════════════════════════════════════
#  C. Cat CUNG NHAU — nghiem thu 4
# ══════════════════════════════════════════════════════════════════════════════

def test_loc_cat_hai_dong_TRIM_ca_hinh_lan_tieng_trong_MOT_concat():
    """🔴 Nghiem thu 4: *"hinh va tieng bi cat cung nhau — ⛔ khong doan tieng
    nao cut"*.

    ⭐ Menh de duoc chot o **cau truc chuoi loc**, va do la cho no thuc su dung:
       mot `concat=n=2:v=1:a=1` cho ra MOT do dai cho ca hai dong, nen ⛔ khong
       the co mot dong bi cat va dong kia thi khong.
    """
    loc = cdr.loc_cat_hai_dong([(0.0, 10.0), (20.0, 30.0)])
    assert loc.count("[0:v]trim=") == 2
    assert loc.count("[0:a]atrim=") == 2
    assert "concat=n=2:v=1:a=1" in loc
    assert f"[{cdr.NHAN_HINH_RA}][{cdr.NHAN_TIENG_RA}]" in loc
    # ⚠️ Thieu `asetpts` thi HINH va TIENG lech nhau dung bang phan da cat.
    assert loc.count("asetpts=PTS-STARTPTS") == 2
    assert loc.count("setpts=PTS-STARTPTS") == 4      # 2 hinh + 2 tieng


def test_loc_cat_noi_cua_GD1_van_CHI_cham_hinh():
    """⛔ Hai ham, hai hop dong. Gop chung lai la tron hai quyet dinh am thanh.

    `loc_cat_noi` (GD1) ⛔ khong duoc cho tieng di qua: ban phoi cua pha 16 da
    chuan am MOT lan theo dung nhung khoang do.
    """
    loc = cdr.loc_cat_noi([(0.0, 10.0), (20.0, 30.0)])
    assert "concat=n=2:v=1:a=0" in loc
    assert "atrim" not in loc


def test_dung_lenh_duong_CAT_map_ca_hai_dong_va_MA_HOA_LAI():
    """⛔ ⛔ KHONG `-c copy` khi co cat: GOP 8,333 giay ⇒ lech toi 8 giay."""
    cmd = gdha.dung_lenh("vao.mp4", "ra.mp4", khoang=[(0.0, 5.0), (10.0, 20.0)],
                         bo_ma_hoa="libx264", ffmpeg_bin="ffmpeg")
    assert "-filter_complex" in cmd
    assert cmd.count("-map") == 2
    assert f"[{cdr.NHAN_HINH_RA}]" in cmd and f"[{cdr.NHAN_TIENG_RA}]" in cmd
    assert "libx264" in cmd
    assert "-c" not in cmd or cmd[cmd.index("-c") + 1] != "copy"


def test_dung_lenh_KHONG_CAT_thi_REMUX__khong_ma_hoa_lai_vo_ich():
    """⭐ Mot lan ma hoa lai "cho nhat quan" tren tep khong bi cat la lay mot ban
    sao nguyen ven doi lay mot ban kem hon."""
    cmd = gdha.dung_lenh("vao.mp4", "ra.mp4", khoang=[(0.0, 30.0)],
                         bo_ma_hoa="", ffmpeg_bin="ffmpeg")
    assert "-c" in cmd and cmd[cmd.index("-c") + 1] == "copy"
    assert "-filter_complex" not in cmd
    assert "libx264" not in cmd


def test_kiem_do_dai_NEM_khi_tep_ra_khong_khop_ke_cat():
    """🔑 Cong DUY NHAT chung minh "cat cung nhau" da thuc su xay ra.

    ⛔ DOI CHUNG: neu cong nay chi la mot dong log thi phep kiem se xanh.
    """
    from apps.auto_scan_video.ket_xuat import KetXuatError

    gdha._kiem_do_dai(90.0, 90.1)              # trong dung sai — khong nem
    with pytest.raises(KetXuatError) as e:
        gdha._kiem_do_dai(100.0, 90.0)
    assert "90" in str(e.value) and "100" in str(e.value)


def test_van_tay_ban_giao_doi_theo_KE_CAT_va_theo_BO_MA_HOA():
    """⛔ Thieu `bo_ma_hoa` thi mot lan chay duoc cap card dung lai tep CPU."""
    ke_a = kc.chon([kc.UngVien(10.0, 12.0, 0.9)], thoi_luong=1000.0)
    ke_b = kc.chon([kc.UngVien(30.0, 32.0, 0.9)], thoi_luong=1000.0)
    goc = gdha.van_tay("k/abc.mp4", ke_a, None, "libx264")
    assert gdha.van_tay("k/abc.mp4", ke_b, None, "libx264") != goc
    assert gdha.van_tay("k/abc.mp4", ke_a, None, "h264_nvenc") != goc
    assert gdha.van_tay("k/abc.mp4", ke_a, (0.1, 0.9), "libx264") != goc
    assert gdha.van_tay("k/abc.mp4", ke_a, None, "libx264") == goc


# ══════════════════════════════════════════════════════════════════════════════
#  D. Preset giu hinh — loi hua KHONG bi noi long khi phep cat doi cho
# ══════════════════════════════════════════════════════════════════════════════

def test_GD2_chi_cat_o_duong_CAT__va_KHONG_tin_giao_dien():
    """🔴 `localize_preserve_picture` hua do dai ra bang do dai vao, va
    `THAO_TAC_CHO_PHEP` cua no la tuple RONG: *"⛔ KHONG DUOC lam"*.

    ⛔ Chuyen phep cat xuong giai doan 2 ⛔ khong duoc lam no rong ra. Ca hai loi
       goi — ke cat tu dong VA cua so cua khach — phai nam trong mot `if` so
       `cach` voi che do cat.
    """
    cay = ast.parse((GOC / "giai_doan_hinh_anh.py").read_text(encoding="utf-8"))
    trong_if: set[str] = set()
    for nut in ast.walk(cay):
        if not isinstance(nut, ast.If) or "CAT_MA_HOA_LAI" not in ast.unparse(nut.test):
            continue
        than = ast.unparse(ast.Module(body=nut.body, type_ignores=[]))
        if "_ke_cat(" in than:
            trong_if.add("_ke_cat")
        if "cat_dau_cuoi.giao" in than:
            trong_if.add("giao")
    assert trong_if == {"_ke_cat", "giao"}, sorted(trong_if)
    assert hop_dong_v4.THAO_TAC_CHO_PHEP[hop_dong_v4.PRESET_GIU_HINH] == ()


def test_che_do_cho_VAN_chi_nhan_preset__bang_gia_phang_khong_bi_dung_toi():
    """⚠️ `gia.py`: *"bien dieu khien la PRESET, ⛔ khong phai tap tinh nang"*.

    ⛔ b4 ⛔ khong duoc lam duong render thanh mot ham cua tap tinh nang — do la
       mot thay doi GIA, va gia thuoc chu du an.
    """
    assert list(inspect.signature(cdr.che_do_cho).parameters) == ["preset"]
    assert cdr.che_do_cho(hop_dong_v4.PRESET_GIU_HINH) == cdr.SAO_CHEP


# ══════════════════════════════════════════════════════════════════════════════
#  E. Ai con dung `ban_do_thoi_gian` — nghiem thu 5
# ══════════════════════════════════════════════════════════════════════════════

#: Module CON duoc doc `ban_do_thoi_gian`, kem LY DO. ⛔ Mot ten o day khong kem
#: ly do la mot phu thuoc khong ai quyet dinh.
CON_DUNG = {
    # 🔑 Chu so huu moi: phep doi moc cua GIAI DOAN 2. No doi moc tren MOT tep
    #    da xong, nen ⛔ khong con hai truc de ma lech.
    "ke_cat.py": "KeCat.ban_do() — chu so huu phep doi moc cua GD2",
    # 🔑 Doc `.srt` ben canh (⛔ khong duoc dot vao diem anh) sang truc ban giao.
    "giai_doan_hinh_anh.py": "doi moc su kien phu de + ban do cua khoang giu",
    # 🔑 Cho noi de hoi VLM — chung chi ton tai tren tep cua GD2.
    "giai_doan_qc_ai.py": "cac cho noi cua TEP BAN GIAO",
    # 🔑 Chuoi loc cat-noi: `_anh_xa_cua_so` doi cua so logo/vung/lop phu.
    "che_do_render.py": "anh xa cua so cua logo/vung/lop phu sang truc ban ra",
    # 🔑 Phan loai ngoai le. ⛔ Khong phai mot nguoi dung phep doi moc.
    "loi.py": "phan loai `BanDoError`",
}

#: ⛔ Module DA THOI doc no o b4. Chot su VANG MAT, vi mot phu thuoc quay lai la
#: mot lop loi quay lai.
DA_THOI = ("thoi_gian.py", "giai_doan_thoi_gian.py", "giai_doan_ban_dung.py",
           "am_master.py")


def test_ai_con_dung_ban_do_thoi_gian__va_ai_DA_THOI():
    """🔴 Nghiem thu 5. ⛔ Khong phai "no tro thanh thua" — no DOI CHU.

    Dieu phoi da noi ho *"tro thanh thua"* truoc khi `grep`; ⛔ no co MUOI nguoi
    dung. B4 khong xoa module, b4 doi nguoi dung cua no: tu *quan ly* mot sai so
    sang *⛔ khong cho no sinh ra*.
    """
    thay = {}
    for tep in sorted(GOC.glob("*.py")):
        van = tep.read_text(encoding="utf-8")
        cay = ast.parse(van)
        for n in ast.walk(cay):
            ten = ""
            if isinstance(n, ast.ImportFrom):
                ten = (n.module or "") + " " + " ".join(a.name for a in n.names)
            elif isinstance(n, ast.Import):
                ten = " ".join(a.name for a in n.names)
            if "ban_do_thoi_gian" in ten:
                thay.setdefault(tep.name, 0)
                thay[tep.name] += 1

    assert set(thay) == set(CON_DUNG), (
        f"chi con: {sorted(thay)}; bang khai: {sorted(CON_DUNG)}")
    for tep in DA_THOI:
        assert tep not in thay, (
            f"{tep} nhap lai `ban_do_thoi_gian` — o giai doan 1 ⛔ khong co phep "
            f"cat nao, nen ⛔ khong co moc nao phai doi")


def test_doi_moc_su_kien_BO_su_kien_bi_cat_va_DICH_su_kien_phia_sau():
    """⛔ Mot cau thoai thuoc phan da cat phai BIEN MAT, ⛔ khong duoc troi."""
    ke = kc.KeCat(cat=((10.0, 20.0),), thoi_luong=100.0)
    bd = ke.ban_do()
    goi = [{"start": 2.0, "end": 4.0, "text": "truoc"},
           {"start": 12.0, "end": 14.0, "text": "trong phan bi cat"},
           {"start": 30.0, "end": 32.0, "text": "sau"}]
    ra = gdha.doi_moc_su_kien(goi, bd)
    assert [x["text"] for x in ra] == ["truoc", "sau"]
    assert (ra[0]["start"], ra[0]["end"]) == (2.0, 4.0)
    # Lui dung 10 giay — bang phan da cat.
    assert (ra[1]["start"], ra[1]["end"]) == (20.0, 22.0)


def test_ung_vien_tu_ban_bien_tap_doc_do_tin_lam_DIEM_KEM():
    """🔑 `do_tin` cua de xuat BO **la** `diem_kem`: thu tu uu tien doc so do."""
    from apps.auto_scan_video.ban_bien_tap import BanBienTap, QuyetDinh
    from apps.auto_scan_video.canh import ChiMucCanh, Canh

    chi_muc = ChiMucCanh(canh=(Canh(ma="c1", bat=0.0, ket=5.0),
                               Canh(ma="c2", bat=5.0, ket=9.0)),
                         thoi_luong=100.0)
    ban = BanBienTap(
        preset=hop_dong_v4.PRESET_CAT_THONG_MINH,
        quyet_dinh=(QuyetDinh("c1", hop_dong_v4.THAO_TAC_GIU, "giu", 0.1, ()),
                    QuyetDinh("c2", hop_dong_v4.THAO_TAC_CAT, "bo", 0.93, ())),
        thoi_luong_nguon=100.0)
    uv = gdha.ung_vien_tu_ban_bien_tap(ban, chi_muc)
    assert [(u.bat, u.ket, u.diem_kem) for u in uv] == [(5.0, 9.0, 0.93)]


def test_thieu_ban_bien_tap_thi_KHONG_CAT_GI__mac_dinh_la_GIU():
    """⭐ *"bo la hanh dong phai co can cu"* — `ban_bien_tap._quyet_dinh_mot_canh`."""
    assert gdha.ung_vien_tu_ban_bien_tap(None, None) == []
    ke = kc.chon([], thoi_luong=100.0)
    assert ke.cat == () and ke.ban_do().thoi_luong_ra == 100.0
