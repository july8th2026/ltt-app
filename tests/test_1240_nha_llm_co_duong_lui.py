"""test_1240 — `nha_llm` PHAI CO DUONG LUI. Su co L-07, 13/09/2026.

## Su co that ma bo nay sinh ra de chan

`ltt-3.8` tra **429 cho moi yeu cau suot 32 phut**. Chuoi su kien:

    04:57:29  mot job anh vao hang
    04:57:34  gpu_residency: xa_llm -> nha_llm    (LLM da roi card)
    04:57:37+ moi ~3 giay, vo tan:
              "khong bat lai duoc ComfyUI => KHONG vao anh ... thu lai luot sau"
    05:29:41  phai can thiep TAY vao CSDL moi go duoc

Goc: cong render may B chay ban cu, thieu `/v1/nha_comfy` => `chay_comfy()` 404
=> khong bao gio vao duoc `ANH`. Va `CHUYEN_HOP_LE[NHA_LLM]` chi co `{ANH}`:
**mot trang thai vao duoc ma khong ra duoc**.

⛔ Sua cong render lam su co AY het, nhung KHONG lam ngo cut ay het. Lan sau
   ComfyUI hong that (o dia day, driver loi, dich vu khong bat duoc) thi ket qua
   van la 3090 nam khong vo han. Do la khuyet tat ve **HINH DANG**, va bo nay
   canh chinh hinh dang do.

## Bon menh de

| # | menh de | vi sao no can |
|---|---|---|
| 1 | moi trang thai deu RA duoc | bat bien chung, khong chi cho `nha_llm` |
| 2 | viec anh rut het ⇒ lui ve `NAP_LLM` | doi xung voi `XA_LLM`, cho dung ca su co |
| 3 | khong mo duoc cua so anh du lan ⇒ tra card | mot ben chay duoc hon hai ben cung chet |
| 4 | va khi da the thi **dung nha lai** | khong co ve 4, duong lui thanh VONG LAP |
"""
import pytest

from platform_core.llm import residency as R


def _qs(**ghi_de):
    """Quan sat MAC DINH: khong ai cho, khong ai chay, may B tra loi duoc."""
    d = dict(lease_llm=0, lease_anh=0, job_anh_cho=0, anh_bat_dau_trong_cua_so=0,
             nguoi_cho_llm=0, han_chot_llm_s=None, gateway_inflight_llm=0,
             llm_da_nap=False, vram_3090_mib=200, nap_ket_qua="",
             lan_vao_anh_hong=0)
    d.update(ghi_de)
    return R.QuanSat(**d)


def _tt(ten, tu_luc=0.0, cua_so_bat_dau=0.0):
    return R.TrangThai(ten=ten, tu_luc=tu_luc, cua_so_bat_dau=cua_so_bat_dau)


# -- 1. Bat bien chung: khong trang thai nao la ngo cut --------------------

@pytest.mark.parametrize("ten", R.TRANG_THAI)
def test_moi_trang_thai_deu_ra_duoc(ten):
    """Moi trang thai phai co it nhat mot duong ra.

    🔴 Day la phep kiem da KHONG ton tai truoc 13/09, va vi the `nha_llm` di
       vao san pham voi dung mot duong ra phu thuoc mot lenh mang co the hong.
       Mot bang chuyen doc tu tren xuong trong rat hop ly; chi khi hoi tung o
       *"tu day di dau duoc"* thi cho thung moi lo ra.
    """
    ra = R.CHUYEN_HOP_LE.get(ten, frozenset())
    assert ra, f"{ten!r} khong co duong ra nao — do la mot ngo cut"


def test_nha_llm_lui_duoc_ve_nap_llm():
    """Chot dung canh cua da thieu. Xoa no khoi bang la bo nay do."""
    assert R.NAP_LLM in R.CHUYEN_HOP_LE[R.NHA_LLM]


# -- 2. Viec anh rut het trong luc dang nha -------------------------------

def test_viec_anh_rut_het_thi_nha_llm_lui_ve_nap_llm():
    """Doi xung voi `xa_llm`, va day la ca su co L-07.

    Luc 05:2x toi huy job anh — va may KHONG go duoc, vi duong huy chi ton tai
    o buoc TRUOC (`xa_llm`). Mot duong huy dung mot buoc truoc cho can no.
    """
    tt = _tt(R.NHA_LLM, tu_luc=100.0)
    moi, lenh = R.buoc_thuan(tt, _qs(job_anh_cho=0), R.ThamSoResidency(), 200.0)
    assert moi.ten == R.NAP_LLM
    assert R.NAP_LLM_LENH in lenh, "phai PHAT lenh nap, khong chi doi ten trang thai"


def test_xa_llm_van_lui_ve_llm_chu_khong_qua_nap_llm():
    """⛔ Hai buoc lui KHAC nhau, va khac biet ay la vat chat.

    O `xa_llm` model VAN NAM tren card ⇒ lui ve `llm` la mien phi.
    O `nha_llm` model DA ROI card ⇒ phai NAP lai (16,3 s).

    Nhay thang `nha_llm -> llm` la khai "LLM dang cu tru" trong khi card trong —
    dung thu bang chuyen cam o `tra_anh -> llm`.
    """
    moi, _ = R.buoc_thuan(_tt(R.XA_LLM, tu_luc=10.0), _qs(job_anh_cho=0),
                          R.ThamSoResidency(), 20.0)
    assert moi.ten == R.LLM
    assert R.LLM not in R.CHUYEN_HOP_LE[R.NHA_LLM]


# -- 3. Phia anh khong dung duoc ------------------------------------------

def test_khong_mo_duoc_cua_so_anh_du_lan_thi_tra_card_cho_llm():
    """Job anh VAN cho, nhung khong mo noi cua so ⇒ tra card cho LLM.

    Mot ben chay duoc tot hon han hai ben cung chet. Truoc 13/09 ket cuc la ca
    hai cung chet, va no keo dai 32 phut.
    """
    ts = R.ThamSoResidency()
    tt = _tt(R.NHA_LLM, tu_luc=100.0)
    qs = _qs(job_anh_cho=5, lan_vao_anh_hong=ts.tran_vao_anh_hong)
    moi, lenh = R.buoc_thuan(tt, qs, ts, 200.0)
    assert moi.ten == R.NAP_LLM
    assert R.NAP_LLM_LENH in lenh


def test_chua_du_lan_thi_van_kien_nhan_cho():
    """Doi chung cua phep tren: mot lan hong thoang qua KHONG duoc lam mat cua
    so anh. Thieu phep nay thi mot `tran_vao_anh_hong = 0` cung xanh."""
    ts = R.ThamSoResidency()
    qs = _qs(job_anh_cho=5, llm_da_nap=False,
             lan_vao_anh_hong=ts.tran_vao_anh_hong - 1)
    moi, _ = R.buoc_thuan(_tt(R.NHA_LLM, tu_luc=100.0), qs, ts, 200.0)
    assert moi.ten == R.ANH, "chua du nguong thi van phai co gang vao cua so anh"


def test_dang_ve_anh_thi_KHONG_phat_lenh_nap():
    """⛔ Cung ly do `LOI_NAP` siet: lenh `nap_llm` tu day khong di qua nhanh
    kiem VRAM cua `TRA_ANH`, nen no se nap 16 GB len mot card DANG VE.

    ⚠️ Ban dau phep kiem nay khang dinh `moi.ten == NHA_LLM` — va no do, ĐÚNG.
       Voi `llm_da_nap is False` thi may di vao `ANH`, va do la hanh vi DUNG:
       anh dang ve thi mo cua so anh. Toi da chot mot TRANG THAI cu the thay vi
       chot TINH CHAT AN TOAN that su can — mot phep kiem "manh hon thu no do".

    ⇒ Menh de dung: du da qua nguong, **khong luot bao nhieu**, da ve anh thi
      KHONG duoc phat `nap_llm`. Dung `llm_da_nap=None` (khong hoi duoc) de
      nhanh `ANH` khong che mat nhanh dang xet.
    """
    ts = R.ThamSoResidency()
    qs = _qs(job_anh_cho=5, lease_anh=1, llm_da_nap=None,
             lan_vao_anh_hong=ts.tran_vao_anh_hong)
    moi, lenh = R.buoc_thuan(_tt(R.NHA_LLM, tu_luc=100.0), qs, ts, 200.0)
    assert R.NAP_LLM_LENH not in lenh, "dang ve — khong duoc nap de len card"
    assert moi.ten == R.NHA_LLM


# -- 4. Duong lui KHONG duoc bien thanh vong lap --------------------------

def test_da_tra_card_thi_LLM_khong_nha_lai_ngay():
    """🔴 MENH DE QUAN TRONG NHAT CUA BO NAY.

    Sau khi lui ve `llm`, job anh VAN xep hang. Khong co phanh thi may quay:

        llm -> xa_llm -> nha_llm -> (khong mo duoc) -> nap_llm -> llm -> ...

    moi vong ton mot luot nap 16,3 s va KHONG ai duoc phuc vu. Doi mot ngo cut
    lay mot vong lap la hong theo kieu khac, khong phai het hong.
    """
    ts = R.ThamSoResidency()
    qs = _qs(job_anh_cho=5, llm_da_nap=True,
             lan_vao_anh_hong=ts.tran_vao_anh_hong)
    moi, lenh = R.buoc_thuan(_tt(R.LLM, tu_luc=0.0), qs, ts, 100.0)
    assert moi.ten == R.LLM, "phia anh dang hong thi dung nha card nua"
    assert not lenh


def test_phia_anh_lanh_lai_thi_nha_card_binh_thuong():
    """Doi chung: phanh tren phai NHA khi bo dem ve 0, khong thi mot lan hong
    se khoa viec sinh anh vinh vien."""
    qs = _qs(job_anh_cho=5, llm_da_nap=True, lan_vao_anh_hong=0)
    moi, _ = R.buoc_thuan(_tt(R.LLM, tu_luc=0.0), qs, R.ThamSoResidency(), 100.0)
    assert moi.ten == R.XA_LLM
