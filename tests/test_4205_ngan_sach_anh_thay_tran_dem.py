"""test_4205 - hai tran token ANH cua may A phai khop `llama-swap.yaml` cua may B.

## Vi sao tep nay ton tai

`apps/ltt_llm/ngan_sach.TOKEN_ANH_TOI_THIEU` / `TOKEN_ANH_TOI_DA` la **ban sao**
cua `--image-min-tokens` / `--image-max-tokens` trong
`llm_gateway/deploy/llama-swap.yaml` - dung cung hinh dang voi `engine_ctx`/`np`
o `HO_SO`.

⛔ Mot so chep sang ma khong ai doi chieu chinh la co che da lam bang o kho nay
   noi sai NAM LAN, va ca nam deu ve phia nguy hiem. `test_4204` canh rang tep
   yaml CO khai hai co ay; tep nay canh rang may A khai DUNG so ay.

## Vi sao DOI CHIEU chu khong IMPORT

May A KHONG doc yaml luc chay: tep yaml song tren may B, va `vat_ly` cua cong B
la noi doc no. Neu may A `import` gia tri tu yaml thi mot may A chay thieu tep
yaml (moi truong thu, may lap trinh vien) se khong dung duoc - va fail-closed o
day se chan ca duong CHU. Nen may A go so, va tep nay la nguoi canh.

## Bat bien "A ⊆ B"

May A dat cho bang DUNG phep may B dem: hai ban `anh_token.py` giong het tung
byte (`test_4203`), va hai tham so cua phep ay khop nhau (tep nay). Thieu mot
trong hai ve thi "A nhan ⇒ B nhan" khong con dung, va mot luot duoc A nhan co
the bi B tra 413 SAU khi da 200 - dung khuyet tat O-02 da xay ra voi phan chu.
"""
from __future__ import annotations

import pytest

from apps.ltt_llm import ngan_sach
from llm_gateway import vat_ly


@pytest.fixture(scope="module")
def ho_so_yaml() -> dict:
    return vat_ly.doc_tep(vat_ly.tim_yaml())


def test_moi_ho_so_A_khop_yaml_B(ho_so_yaml):
    """Tung hong so cua `HO_SO` phai khop dung hong so cung ten trong yaml."""
    thieu = [m for m in ngan_sach.HO_SO if m not in ho_so_yaml]
    assert not thieu, (
        f"ho so {thieu} co trong `HO_SO` cua may A ma KHONG co trong "
        f"llama-swap.yaml - may A dat cho cho mot engine khong ton tai")

    for m, h in ngan_sach.HO_SO.items():
        v = ho_so_yaml[m]
        assert h.token_anh_toi_thieu == v.token_anh_toi_thieu, (
            f"`{m}`: may A dat cho theo san {h.token_anh_toi_thieu} nhung engine "
            f"chay voi --image-min-tokens {v.token_anh_toi_thieu}")
        assert h.token_anh_toi_da == v.token_anh_toi_da, (
            f"`{m}`: may A dat cho theo tran {h.token_anh_toi_da} nhung engine "
            f"chay voi --image-max-tokens {v.token_anh_toi_da}. Lech theo chieu "
            f"A THAP hon B la dat cho THIEU - chieu ma mot lan tran `-kvu` giet "
            f"MOI slot (llama.cpp b10689)")


def test_hai_hang_A_la_MOT_nguon(ho_so_yaml):
    """⭐ Moi ho so phai doc CUNG hai hang, khong ho so nao go rieng mot so.

    Phep tiem nghich cho khuyet tat F-02 (`CUA_SO_MODEL` lich su): mot hang dung
    chung bi thay bang hai so go tay o hai ho so, va khong ai bat.
    """
    san = {h.token_anh_toi_thieu for h in ngan_sach.HO_SO.values()}
    tran = {h.token_anh_toi_da for h in ngan_sach.HO_SO.values()}
    assert san == {ngan_sach.TOKEN_ANH_TOI_THIEU}, san
    assert tran == {ngan_sach.TOKEN_ANH_TOI_DA}, tran


def test_tran_phu_MOI_so_do_that():
    """Tran engine phai >= chi phi that cua moi co anh da do 28/09/2026.

    ⛔ Bang nay la so DO tren production (`tools/do_token_anh.py`, 14/14 o, ca hai
       model). KHONG sua de lam test xanh.

    🔴 Va day la cho hang cu 2.048 SAI: mot anh 2048x2048 an 4.098 token, tuc
       hang phang dat cho THIEU 2x - o dung co toi da client LTTCODE gui
       (`IMAGE_BUDGET.maxPixels = 2048**2`).
    """
    from platform_core.llm import anh_token as AT

    # So DO o SAN 8 - day la su that ve CONG THUC, khong ve cau hinh.
    do_o_san_8 = ((320, 240, 82), (512, 512, 258), (1024, 768, 770),
                  (1280, 720, 922), (1920, 1080, 2042), (2048, 2048, 4098),
                  (3840, 2160, 4082))
    san = ngan_sach.TOKEN_ANH_TOI_THIEU
    duoi_san = []
    for rong, cao, o_san_8 in do_o_san_8:
        that = AT.token_anh(rong, cao, toi_thieu=san,
                            toi_da=ngan_sach.TOKEN_ANH_TOI_DA) + AT.TOKEN_DAU_VISION
        if o_san_8 - AT.TOKEN_DAU_VISION < san:
            # Co nay nam DUOI san hien tai => phai bi kep len dung san.
            duoi_san.append((rong, cao))
            assert that == san + AT.TOKEN_DAU_VISION, (
                f"{rong}x{cao}: san {san} ma tinh ra {that}, mong "
                f"{san + AT.TOKEN_DAU_VISION} - phep kep san khong chay")
        else:
            assert that == o_san_8, (
                f"{rong}x{cao}: tinh {that}, do duoc {o_san_8} - co nay TREN san "
                f"nen san khong duoc cham vao no")
        assert ngan_sach.TOKEN_ANH_TOI_DA + AT.TOKEN_DAU_VISION >= that, (
            f"tran {ngan_sach.TOKEN_ANH_TOI_DA} THAP hon chi phi that {that}")
    # ⭐ Doi chung: phai CO it nhat mot co duoi san, neu khong phep tren khong
    #    thu phep kep bao gio - va no se xanh ca khi phep kep bi go.
    assert duoi_san, (
        f"san {san} thap hon MOI co trong bang, nen phep kep chua tung duoc thu")


def test_hang_phang_cu_KHONG_con_tren_duong_dat_cho():
    """⛔ `TOKEN_GIU_MOI_ANH = 2.048` khong duoc quay lai lam so dat cho.

    Hang ay CON TON TAI o `apps/ltt_llm/ngan_sach` (tai lieu lich su) va o
    `llm_gateway/ngan_sach` (duong lui khi KHONG doc duoc tran engine). Nhung
    KHONG hong so nao duoc mang no, va `AdmissionModel` khong duoc co truong cu.
    """
    from platform_core.registry import AdmissionModel

    assert not hasattr(AdmissionModel("thu", 1), "token_giu_moi_anh"), (
        "`AdmissionModel` con truong `token_giu_moi_anh` - mot hang phang moi anh "
        "da bi thay bang `f(rong, cao)`, giu truong cu la moi ai do dung lai no")
    for m, h in ngan_sach.HO_SO.items():
        assert not hasattr(h, "token_giu_moi_anh"), m
        assert ngan_sach.TOKEN_GIU_MOI_ANH not in (h.token_anh_toi_thieu,
                                                   h.token_anh_toi_da), m


def test_luat_cho_cong_token_anh_chu_khong_nhan():
    """`luat_cho` phai CONG tong da do, ⛔ khong nhan mot hang voi so anh.

    Phep tiem nghich: hai lan goi voi cung `token_anh` phai cho cung ket qua,
    va dat cho phai tang DUNG bang `token_anh` - neu ai nhan voi mot he so nao
    thi phep nay do.
    """
    from platform_core.llm import luat_nhan, tham_so_da_luot
    from platform_core.registry import AdmissionModel

    suc = AdmissionModel("thu", 4, 100_000, nguong_whale=50_000, dem_uoc=2_048,
                         token_anh_toi_thieu=8, token_anh_toi_da=4_096)
    khong = tham_so_da_luot.luat_cho(suc, lop=luat_nhan.TUONG_TAC,
                                     token_vao_uoc=1_000, xin_ra=100)
    co = tham_so_da_luot.luat_cho(suc, lop=luat_nhan.TUONG_TAC,
                                  token_vao_uoc=1_000, xin_ra=100, token_anh=4_098)
    assert co["token_dat_truoc"] - khong["token_dat_truoc"] == 4_098, (
        "dat cho khong tang DUNG bang `token_anh` - co ai dang nhan them he so")
