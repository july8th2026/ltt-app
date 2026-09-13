"""test_1245 — bo dem `lan_vao_anh_hong` phai TU NHAT DI. Su co L-10, 13/09/2026.

## Ban va cho mot ngo cut, de lai mot ngo cut khac

`test_1240` chan L-07: `nha_llm` phai co duong lui. Ban va ay them mot PHANH o
`LLM` — dung, vi khong co phanh thi duong lui thanh vong quay. Nhung phanh ay
viet thang la `lan_vao_anh_hong < tran`, va bo dem chi duoc xoa o **dung mot
cho**: sau mot `chay_comfy()` thanh cong. Ma `chay_comfy()` nam sau chinh cai
phanh do.

⇒ Cham tran 3 lan la phia anh bi KHOA NGOAI vinh vien.

Do tren may that (13/09, ca bon dich vu may B song):

    vong 1  ComfyUI Disabled  -> llm -> nha_llm -> nap_llm -> llm  (46,7 s)
    vong 2  ComfyUI Automatic -> nop job anh moi
            -> residency KHONG HE roi `llm` suot 120 s, job o `queued`

Khong mot dong log, khong mot bao dong. Chi khoi dong lai worker moi go duoc.

## Vi sao bo nay ton tai rieng thay vi them ve vao test_1240

`test_1240` van XANH nguyen ven voi ma hong — no dung `bay_gio` trong khoang
100–200 con nhip lui la 300 s, nen vi tu moi tra ve cung ket qua voi bieu thuc
cu. Tuc no xanh nho mot **gia tri dong ho tinh co**, khong phai nho kiem dung
thu can kiem. Mot bo kiem xanh ca truoc lan sau ban va thi khong bao ve ban va.

## Nam menh de

| # | menh de | no chan dieu gi |
|---|---|---|
| 1 | cham tran + vua hong ⇒ VAN phanh | khong pha mat chong-vong-quay cua L-07 |
| 2 | cham tran + du gio ⇒ THU LAI | L-10: khoa ngoai vinh vien |
| 3 | `nha_llm` doc CUNG vi tu voi `llm` | thu lai ma khong goi noi `chay_comfy()` |
| 4 | nhip lui gap doi va co TRAN | mot may B hong ca buoi khong bi tra gia mai |
| 5 | khong bao gio co "cho mai mai" | bat bien: moi phanh phai co han |
"""
import pytest

from platform_core.llm import residency as R

TS = R.ThamSoResidency()


def _qs(**ghi_de):
    d = dict(lease_llm=0, lease_anh=0, job_anh_cho=5, anh_bat_dau_trong_cua_so=0,
             nguoi_cho_llm=0, han_chot_llm_s=None, gateway_inflight_llm=0,
             llm_da_nap=False, vram_3090_mib=200, nap_ket_qua="",
             lan_vao_anh_hong=TS.tran_vao_anh_hong, luc_anh_hong_cuoi=0.0)
    d.update(ghi_de)
    return R.QuanSat(**d)


def _tt(ten, tu_luc=0.0, cua_so_bat_dau=0.0):
    return R.TrangThai(ten=ten, tu_luc=tu_luc, cua_so_bat_dau=cua_so_bat_dau)


# -- 1. Vua hong xong thi VAN phai phanh -------------------------------------

def test_vua_hong_xong_thi_khong_nha_card_lai_ngay():
    """Ve chong-vong-quay cua L-07 phai con nguyen.

    Khong co ve nay, ban va L-10 bien duong lui thanh dung cai vong quay ma
    `test_1240` sinh ra de chan: nha -> khong mo duoc -> lui -> nha lai -> ...
    moi vong ton mot luot nap 16,3 s va khong ai duoc phuc vu.
    """
    luc = 10_000.0
    qs = _qs(luc_anh_hong_cuoi=luc)
    moi, lenh = R.buoc_thuan(_tt(R.LLM), qs, TS, luc + 1.0)
    assert moi.ten == R.LLM, "vua hong 1 giay truoc ma da nha card lai"
    assert lenh == ()


# -- 2. Du gio thi PHAI thu lai — day la chinh L-10 ---------------------------

def test_du_gio_thi_thu_lai_du_bo_dem_van_cham_tran():
    luc = 10_000.0
    qs = _qs(luc_anh_hong_cuoi=luc)
    sau = luc + R.lui_anh_s(qs, TS) + 0.1
    moi, _ = R.buoc_thuan(_tt(R.LLM), qs, TS, sau)
    assert moi.ten == R.XA_LLM, (
        "cham tran roi thi khong bao gio thu lai nua => phia anh khoa ngoai "
        "vinh vien (L-10), ke ca khi ComfyUI da lanh tu lau")


def test_bo_dem_cao_bao_nhieu_cung_van_co_luc_duoc_thu_lai():
    """Bat bien: khong ton tai so lan hong nao lam phanh thanh VINH VIEN.

    Quet nay la thu ma mot phep kiem mot-diem khong lam duoc: no noi ve MOI n,
    ke ca nhung n chua ai nghi toi.
    """
    for n in range(TS.tran_vao_anh_hong, TS.tran_vao_anh_hong + 12):
        qs = _qs(lan_vao_anh_hong=n, luc_anh_hong_cuoi=1_000.0)
        han = R.lui_anh_s(qs, TS)
        assert han < float("inf")
        moi, _ = R.buoc_thuan(_tt(R.LLM), qs, TS, 1_000.0 + han + 0.1)
        assert moi.ten == R.XA_LLM, f"n={n} bi phanh vinh vien"


def test_khong_biet_hong_luc_nao_thi_cho_thu_chu_khong_khoa():
    """`luc_anh_hong_cuoi = 0` ⇒ cho thu. Huong hong an toan, co chu dich.

    Thua mot luot 47 s thi lan hong ke tiep ghi lai moc that va tu sua. Khoa
    nham thi khong co gi tu sua ca — do la bai hoc cua chinh L-10.
    """
    qs = _qs(luc_anh_hong_cuoi=0.0)
    moi, _ = R.buoc_thuan(_tt(R.LLM), qs, TS, 50_000.0)
    assert moi.ten == R.XA_LLM


# -- 3. `nha_llm` phai doc CUNG vi tu -----------------------------------------

def test_du_gio_thi_nha_llm_di_toi_anh_chu_khong_quay_dau():
    """Cai bay that su cua ban va nay.

    O `NHA_LLM`, duong lui 2 duoc kiem TRUOC nhanh vao `ANH`. Noi rieng ve o
    `LLM` thi luot thu lai se nha card roi nap lai ngay ma **khong he goi
    `chay_comfy()`** — ton tron 47 giay de khong hoi duoc cau duy nhat can hoi.
    """
    luc = 10_000.0
    qs = _qs(luc_anh_hong_cuoi=luc, llm_da_nap=False)
    sau = luc + R.lui_anh_s(qs, TS) + 0.1
    moi, _ = R.buoc_thuan(_tt(R.NHA_LLM, tu_luc=luc), qs, TS, sau)
    assert moi.ten == R.ANH, (
        "het han lui ma `nha_llm` van quay dau ve `nap_llm` => luot thu lai "
        "khong bao gio goi toi `chay_comfy()`, tuc khong bao gio xoa duoc bo dem")


def test_chua_du_gio_thi_nha_llm_van_tra_card_cho_llm():
    """Doi xung cua ve tren: con trong han lui thi duong lui 2 van phai chay."""
    luc = 10_000.0
    qs = _qs(luc_anh_hong_cuoi=luc, llm_da_nap=False)
    moi, lenh = R.buoc_thuan(_tt(R.NHA_LLM, tu_luc=luc), qs, TS, luc + 1.0)
    assert moi.ten == R.NAP_LLM
    assert R.NAP_LLM_LENH in lenh


@pytest.mark.parametrize("trang_thai", [R.LLM, R.NHA_LLM])
def test_go_vi_tu_thi_ca_hai_cho_deu_doi_hanh_vi(monkeypatch, trang_thai):
    """DOI CHUNG: chung minh phep kiem that su rang buoc ca hai cho.

    Neu mot cho nao do khong doc `duoc_thu_anh` thi `monkeypatch` duoi day se
    khong lam no doi hanh vi, va ve tuong ung se do.
    """
    luc = 10_000.0
    qs = _qs(luc_anh_hong_cuoi=luc, llm_da_nap=False)
    sau = luc + R.lui_anh_s(qs, TS) + 0.1

    truoc, _ = R.buoc_thuan(_tt(trang_thai, tu_luc=luc), qs, TS, sau)
    monkeypatch.setattr(R, "duoc_thu_anh", lambda *a, **k: False)
    sau_khi_go, _ = R.buoc_thuan(_tt(trang_thai, tu_luc=luc), qs, TS, sau)
    assert truoc.ten != sau_khi_go.ten, (
        f"{trang_thai!r} khong doc `duoc_thu_anh` => mot nua ban va L-10 khong "
        "duoc rang buoc boi phep kiem nao")


# -- 4. Nhip lui: gap doi, va co TRAN ----------------------------------------

def test_nhip_lui_gap_doi_roi_cham_tran():
    t = TS.tran_vao_anh_hong
    goc = TS.lui_anh_hong_s
    assert R.lui_anh_s(_qs(lan_vao_anh_hong=t), TS) == goc
    assert R.lui_anh_s(_qs(lan_vao_anh_hong=t + 1), TS) == goc * 2
    assert R.lui_anh_s(_qs(lan_vao_anh_hong=t + 2), TS) == goc * 4
    assert R.lui_anh_s(_qs(lan_vao_anh_hong=t + 3), TS) == goc * 8
    # tran: tu day tro di khong tang nua
    assert R.lui_anh_s(_qs(lan_vao_anh_hong=t + 4), TS) == goc * 8
    assert R.lui_anh_s(_qs(lan_vao_anh_hong=t + 40), TS) == goc * 8


def test_tran_anh_thap_hon_tran_nap_vi_hai_ben_mat_thu_khac_nhau():
    """Mot bat dang thuc giua hai tham so, chot lai de khong ai chinh le mot ben.

    `lui_nap_s` lui toi 480 s vi luc do LLM da chet han — lui lau khong mat them
    gi. `lui_anh_s` thi khac: LLM van dang phuc vu, thu dang cho la hang job anh.
    Nen tran ben anh phai la mot con so ma NGUOI con doi duoc.
    """
    tran_anh = TS.lui_anh_hong_s * 8
    assert tran_anh <= 40 * 60, "hang job anh cho qua 40 phut thi can nguoi, khong can may thu tiep"


# -- 5. Bo dem mang theo MOC THOI GIAN ---------------------------------------

def test_quan_sat_co_cho_ghi_luc_hong_cuoi():
    """Mot bo dem khong kem moc gio thi khong the tu nhat di.

    Ve nay khong kiem mot nhanh `if` nao — no chot rang du lieu CO CHO de chua
    su that ay. Bo truong nay di thi moi ve tren deu do theo, nhung ve nay do
    truoc va noi dung ly do.
    """
    qs = R.QuanSat(lease_llm=0, lease_anh=0, job_anh_cho=0,
                   anh_bat_dau_trong_cua_so=0, nguoi_cho_llm=0,
                   han_chot_llm_s=None, gateway_inflight_llm=0,
                   llm_da_nap=False, vram_3090_mib=200)
    assert hasattr(qs, "luc_anh_hong_cuoi")
    assert qs.luc_anh_hong_cuoi == 0.0
