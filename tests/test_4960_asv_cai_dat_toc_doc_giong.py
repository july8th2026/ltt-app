"""B17 §4.1, lan P0-a — `cai_dat.toc_doc_giong` la settings DAN XUAT giai mot
CHU TRINH trong DAG: `content_process` (GD4) can neo do dai cau dich theo toc
doc CUA GIONG, nhung giong that chi duoc CHOT o `voice_synthesis` (GD6, chay
SAU). Neo Viral: `localize.py:1946 _wps_giong_that` + `:15109` (bang da do) +
`:15112-15117` (`min()` MOT CHIEU, nguyen van "CHI SIET, KHONG NOI").

Xem `docs/auto_scan_video_final/B17_PLAN_TRIEN_KHAI_THEO_VIRAL.md` §4.1 va
`docs/auto_scan_video_final/B17_THAM_CHIEU_VIRAL/W2_CONG_KET_NOI.md` §2.1.

Dai 4960-4966 (da dem, dai trong). Tep nay dung tinh THUAN tren `cai_dat.py`,
khong can DB/model — xem `test_4961_...py` cho phan tich hop `ho_so_dich.py`.
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import cai_dat, ngon_ngu

# ============================================================================
# 1) `min()` MOT CHIEU — phep kiem QUAN TRONG NHAT (bat dung loi cua Viral)
# ============================================================================


def test_giong_do_CHAM_hon_hang_so_NEO_BI_SIET():
    """Giong do CHAM hon hang so ca-ngon-ngu -> neo bi siet theo dung so do."""
    bang = {"giong_cham": 2.00}
    ket = cai_dat.toc_doc_giong("giong_cham", "vi", bang=bang)
    assert ket == 2.00
    assert ket < ngon_ngu.NHIP["vi"]


def test_giong_do_NHANH_hon_hang_so_NEO_KHONG_DUOC_NOI():
    """🔴 Phep kiem quan trong nhat: giong do NHANH hon hang so -> neo GIU
    NGUYEN hang so ca-ngon-ngu, ⛔ KHONG duoc noi len theo so do nhanh hon.

    Day chinh la ca `min()` MOT CHIEU cua Viral (`localize.py:15112-15117`,
    nguyen van "CHI SIET, KHONG NOI"): mot phien ban SAI (cai hai chieu, vd
    `max()` hoac gan thang `do_rieng`) se lam bai nay DO.
    """
    bang = {"giong_nhanh": 999.0}
    ket = cai_dat.toc_doc_giong("giong_nhanh", "vi", bang=bang)
    assert ket == ngon_ngu.NHIP["vi"], (
        "neo bi NOI theo giong nhanh hon — dung sai hinh dang min() mot chieu "
        "cua Viral: 'nới neo cho giọng nhanh sẽ đẻ ra bản dịch DÀI HƠN ⇒ nén "
        "NẶNG HƠN — đúng ngược ý'")
    assert ket != 999.0


def test_ca_hai_chieu_cung_mot_lan_kiem_tiem_nghich():
    """Phep tiem nghich: MOT bang co CA giong cham va giong nhanh, kiem dung
    huong cho TUNG giong trong CUNG mot lan goi (chong tinh huong "nhìn giống
    hệt nhau nếu không có bảng đối chứng" — bai hoc bánh-cóc 28/09)."""
    hang_so = ngon_ngu.NHIP["vi"]
    bang = {"cham": hang_so - 1.0, "nhanh": hang_so + 1.0}
    assert cai_dat.toc_doc_giong("cham", "vi", bang=bang) == hang_so - 1.0
    assert cai_dat.toc_doc_giong("nhanh", "vi", bang=bang) == hang_so


# ============================================================================
# 2) DUONG LUI TUONG MINH — khong bao gio tra 0
# ============================================================================


def test_khong_co_so_do_RIENG_cho_giong_nay_LUI_VE_hang_so_ngon_ngu():
    """Giong khong nam trong bang -> lui ve hang so ca-ngon-ngu (KHONG phai
    0) — day la ca "chua do", khac han ca "do duoc gia tri chinh xac bang
    khong" (khong bao gio xay ra tren duong that)."""
    ket = cai_dat.toc_doc_giong("mot_giong_chua_ai_do", "vi", bang={})
    assert ket == ngon_ngu.NHIP["vi"]
    assert ket != 0


def test_bang_MAC_DINH_RONG_hom_nay__moi_giong_deu_di_duong_lui():
    """`TOC_DOC_GIONG_DA_DO` hom nay RONG (chua do rieng giong nao) — day la
    trang thai TRUNG THUC, khong phai loi: goi KHONG truyen `bang` (dung mac
    dinh) phai cho CUNG ket qua voi bang rong tuong minh."""
    assert cai_dat.TOC_DOC_GIONG_DA_DO == {}
    assert (cai_dat.toc_doc_giong("giong_bat_ky", "vi")
            == cai_dat.toc_doc_giong("giong_bat_ky", "vi", bang={})
            == ngon_ngu.NHIP["vi"])


def test_ngon_ngu_dich_ngoai_hop_dong_NEM_khong_tra_0():
    """Dich ngoai `ngon_ngu.DICH_HOP_LE` (vd `fr`, ma Viral co nhung ta
    khong) -> nem `NgonNguError` cung mot cua voi `ngan_sach_do_dai`, ⛔
    KHONG bao gio tra ve `0` — 0 se gop hai trang thai "khong hop le" va "do
    ra bang khong" thanh mot."""
    with pytest.raises(ngon_ngu.NgonNguError):
        cai_dat.toc_doc_giong("giong_bat_ky", "fr")


def test_gia_tri_khong_hop_le_trong_bang_cung_di_duong_lui():
    """So do <= 0 (du lieu hong trong bang, vd tu mot lan nhap sai) khong
    duoc coi la "gia tri that" — di duong lui thay vi tra ve mot so am/khong
    vo nghia lam neo do dai."""
    ket = cai_dat.toc_doc_giong("giong_hong", "vi", bang={"giong_hong": -1.0})
    assert ket == ngon_ngu.NHIP["vi"]


# ============================================================================
# 3) VAN TAY / KHOA CACHE — co mat, ma KHONG can mot khoa rieng
# ============================================================================


def test_toc_doc_giong_NAM_TRONG_KHOA_DAN_XUAT():
    """He thong ghi khoa nay GIUA chuoi (`ho_so_dich.dung`, trong
    `content_process`) — no PHAI nam trong `KHOA_DAN_XUAT`, neu khong mot
    dong ghi giua chuoi se dat lai media_prepare/audio_prepare/transcribe
    (dung ca da do duoc khi viet lan nay, xem `cai_dat.voi_toc_doc_giong`)."""
    assert "toc_doc_giong" in cai_dat.KHOA_DAN_XUAT


def test_cho_van_tay_LOAI_BO_toc_doc_giong_giu_nguyen_cac_khoa_khac():
    tho = {"giong_id": "Minh Duc", "ngon_ngu_dich": "vi", "toc_doc_giong": 3.0}
    vt = cai_dat.cho_van_tay(tho)
    assert "toc_doc_giong" not in vt
    assert vt["giong_id"] == "Minh Duc"
    assert vt["ngon_ngu_dich"] == "vi"


def test_gia_tri_la_HAM_THUAN_cua_hai_truong_DA_NAM_trong_van_tay_long_tieng():
    """🔑 Vi sao KHONG can them mot khoa rieng vao `long_tieng.van_tay_long_
    tieng`: gia tri la ham THUAN cua dung hai truong ham do NHAN — `ma_giong`
    va `ngon_ngu_dich` — ca hai DA la tham so cua `van_tay_long_tieng`. Doi
    giong (voi mot so do rieng khac) hoac doi dich la DA lam van tay do doi
    theo, du `toc_doc_giong` khong duoc nhet them vao dau vao cua ham hash do.

    Bai nay CHUNG MINH tinh chat "ham thuan cua hai truong da duoc fingerprint"
    bang cach cho hai gia tri KHAC NHAU tren hai giong khac nhau, dich giu
    nguyen — tuc mot thay doi giong that su tao ra mot dau vao khac cho bat
    ky ham bam nao nhan `ma_giong` lam tham so.
    """
    bang = {"giong_a": 2.0, "giong_b": 3.0}
    a = cai_dat.toc_doc_giong("giong_a", "vi", bang=bang)
    b = cai_dat.toc_doc_giong("giong_b", "vi", bang=bang)
    assert a != b, "hai giong khac nhau phai cho toc doc khac nhau khi ca hai co so do rieng"


# ============================================================================
# 4) `voi_toc_doc_giong` — ghi vao ho so dict, KHONG duoc dinh dang lai gi khac
# ============================================================================


def test_voi_toc_doc_giong_CHI_them_dung_MOT_khoa():
    """🔴 Bai hoc do duoc khi viet lan nay: ban dau ham goi `chuan_hoa()` va
    lam VO mot phep kiem dau-cuoi that (`test_408::TestAnToanCuocGoiTraTien::
    test_giai_doan_hong_MO_HO_thi_job_KHONG_quay_lai_hang_doi`) vi no dinh
    dang lai CA nhung khoa khong lien quan (them `preset`/`timing_mode`/...
    mac dinh) — `cho_van_tay` doi theo va giai doan TRUOC content_process bi
    dat lai. Neo lai bang phep kiem: dau vao THO chi co dung nhung khoa da
    cho, dau ra chi THEM dung mot khoa `toc_doc_giong`.
    """
    tho = {"giong_id": "Minh Duc"}
    ra = cai_dat.voi_toc_doc_giong(tho)
    assert set(ra) == {"giong_id", "toc_doc_giong"}
    assert ra["giong_id"] == "Minh Duc"
    assert ra["toc_doc_giong"] == ngon_ngu.NHIP["vi"]  # ngon_ngu_dich rong -> mac dinh vi


def test_voi_toc_doc_giong_KHONG_dung_toi_chuan_hoa():
    """Neo CHO GOI: `voi_toc_doc_giong` khong duoc goi `chuan_hoa` — bai hoc
    o tren, chot bang AST de mot ban sua sau nay khong vo tinh dua no tro
    lai."""
    import ast
    import inspect

    cay = ast.parse(inspect.getsource(cai_dat.voi_toc_doc_giong))
    goi_ten = [n.func.id for n in ast.walk(cay)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
    assert "chuan_hoa" not in goi_ten, (
        "voi_toc_doc_giong goi chuan_hoa() — xem docstring ham nay va "
        "test_giai_doan_hong_MO_HO_thi_job_KHONG_quay_lai_hang_doi ve vi sao "
        "dieu nay tung lam vo mot phep kiem dau-cuoi that")


def test_voi_toc_doc_giong_goi_lai_nhieu_lan_CUNG_dau_vao_ra_CUNG_ket_qua():
    """VONG SUA cua content_process co the goi lai ham nay nhieu lan — ket
    qua phai ON DINH (ham thuan, khong canh gac nhung cung khong duoc lech)."""
    tho = {"giong_id": "x", "ngon_ngu_dich": "en"}
    a = cai_dat.voi_toc_doc_giong(tho)
    b = cai_dat.voi_toc_doc_giong(a)
    assert a["toc_doc_giong"] == b["toc_doc_giong"] == ngon_ngu.NHIP["en"]


def test_voi_toc_doc_giong_rong_van_hoat_dong():
    ra = cai_dat.voi_toc_doc_giong(None)
    assert ra["toc_doc_giong"] == ngon_ngu.NHIP["vi"]


# ============================================================================
# 5) `CaiDat.toc_doc_giong` — truong doc, phan biet "chua tinh" voi 0
# ============================================================================


def test_tu_ho_so_CHUA_CO_khoa_tra_None_khong_phai_0():
    cd = cai_dat.tu_ho_so({"giong_id": "x"})
    assert cd.toc_doc_giong is None


def test_tu_ho_so_DOC_DUNG_gia_tri_da_ghi():
    tho = cai_dat.voi_toc_doc_giong({"giong_id": "x", "ngon_ngu_dich": "en"})
    cd = cai_dat.tu_ho_so(tho)
    assert cd.toc_doc_giong == ngon_ngu.NHIP["en"]


# ============================================================================
# 6) `KHOA_THUA` — chuan_hoa() giu khoa nay khi CO, bo khi KHONG (Thua that)
# ============================================================================


def test_chuan_hoa_GIU_toc_doc_giong_khi_co():
    ra = cai_dat.chuan_hoa({"toc_doc_giong": 3.35})
    assert ra.get("toc_doc_giong") == 3.35


def test_chuan_hoa_KHONG_them_toc_doc_giong_khi_khong_co():
    """Cung luat voi `ho_so_noi_dung`/`vung`/`phu_de`: mot lan chay CHUA qua
    `content_process` thi KHONG mang khoa nay — khong duoc dien mac dinh."""
    ra = cai_dat.chuan_hoa({"giong_id": "x"})
    assert "toc_doc_giong" not in ra
