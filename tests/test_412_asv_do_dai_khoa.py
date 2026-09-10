"""Do dai duong luu tru — bat bien DO DUOC, khong phai mot con so chon cho dep.

Tach thanh tep rieng vi no khong kiem vong doi artifact ma kiem mot rang buoc
cua **he dieu hanh** ma thiet ke khoa phai song chung.
"""
from __future__ import annotations

from apps.auto_scan_video import assets, pipeline

#: Ngan sach that: goc luu tru cua production (`C:\LTTPlatform\data\storage\`)
#: cong hau to `.part<pid>` ma `platform_core/storage.py:227` them vao. De rong
#: rai cho ca may khach co duong sau hon may chu.
GOC_GIA_DINH = 120
HAU_TO_PART = len(".part") + 7          # PID tren Windows toi 7 chu so


def test_khoa_artifact_du_ngan_de_khong_cham_MAX_PATH_windows():
    """Khoa dai lam vo `Storage.put` tren Windows — va vo theo kieu te nhat.

    🔴 Da xay ra that ngay 02/09. Van tay sha256 **day du** (64 ky tu hex) trong
       ten tep lam duong dai 262 ky tu, MAX_PATH la 260. Trieu chung:

         chay MOT MINH   -> 252 ky tu -> XANH
         chay trong gate -> xdist chen `popen-gwN\\` (10 ky tu) -> 262 -> DO

       Tuc mot loi that trong ma nhung chi lo ra khi chay song song. Rat de bi
       doc nham thanh "test chap chon" roi chay lai cho toi khi tra xanh — va
       tren may khach co duong luu tru sau hon thi no hong ca khi chay mot minh.

    ⭐ Chot o day chu khong chot bang mot lan chay: phep kiem nay no NGAY khi ai
       do nang `DAI_VAN_TAY_TRONG_KHOA` hay them mot doan vao khoa, chu khong
       doi toi luc gap mot may co duong du sau.
    """
    #: Dau vao xau nhat THAT SU. 🔴 Ban dau cho o day la `owner_id="uA"` — 2 ky
    #: tu — va phep kiem xanh trong khi loi van con: `owner_id` that la UUID
    #: **36 ky tu** (`AsvRun.owner_id` la `String(36)`).
    owner = "3f2a1b7c-9d4e-4a01-8b6f-0c5d2e7a9b13"
    assert len(owner) == 36, "dau vao thu phai dung hinh dang cot that"
    run = "asvr_" + "0" * 32
    van_tay = "f" * 64                      # ban day du, TRUOC khi bi cat

    dai_nhat, thu_pham = 0, ""
    for stage in pipeline.TEN_GIAI_DOAN:
        khoa = assets.khoa_staging(owner_id=owner, run_id=run, stage=stage,
                                   van_tay=van_tay, duoi="wav")
        dai = GOC_GIA_DINH + len(khoa) + HAU_TO_PART
        if dai > dai_nhat:
            dai_nhat, thu_pham = dai, khoa

    assert dai_nhat < 260, (
        f"duong dai nhat {dai_nhat} >= MAX_PATH 260 ({thu_pham}) — "
        f"`Storage.put` se nem FileNotFoundError o `open(tmp,'wb')`, "
        f"va no se CHI do khi chay song song")


def test_van_tay_DAY_DU_van_duoc_giu_lai():
    """Cat ten tep khong duoc phep cat ca bang chung.

    Neu ban day du bien mat cung, thi ta da doi 128 bit chong dung lay 32 ky tu
    duong dan — mot mon hoi khac han, va khong ai co y doi.
    """
    van_tay = "ab" * 32
    khoa = assets.dat_khoa(owner_id="uA", run_id="asvr_x", stage="compose",
                           van_tay=van_tay, duoi="json")
    assert van_tay[:assets.DAI_VAN_TAY_TRONG_KHOA] in khoa
    assert van_tay not in khoa, "khoa van dang van tay day du"
    assert assets.DAI_VAN_TAY_TRONG_KHOA >= 32, (
        "duoi 32 ky tu hex (128 bit) thi lap luan chong dung khong con dung")


def test_khoa_van_mang_chu_so_huu_du_da_bi_cat():
    """Cat khong duoc lam mat tinh chat ma `dat_khoa` vien dan: khoa mang chu so
    huu, nen mot ro ri doi hoi ai do CO Y ghep duong dan cua nguoi khac."""
    owner = "3f2a1b7c-9d4e-4a01-8b6f-0c5d2e7a9b13"     # UUID that, 36 ky tu
    khoa = assets.dat_khoa(owner_id=owner, run_id="asvr_x", stage="compose",
                           van_tay="c" * 64, duoi="json")
    assert owner[:assets.DAI_OWNER_TRONG_KHOA] in khoa
    khac = assets.dat_khoa(owner_id="9a8b7c6d-0000-4a01-8b6f-0c5d2e7a9b13",
                           run_id="asvr_x", stage="compose",
                           van_tay="c" * 64, duoi="json")
    assert khoa != khac, "hai chu so huu khac nhau van ra cung khoa"


def test_cat_van_tay_la_XAC_DINH_nen_tra_cuu_van_khop():
    """Cat khong xac dinh se lam hong dedup: cung noi dung ra hai khoa khac nhau,
    va cache khong bao gio trung — mot lan chay lai se tinh tien lai tu dau."""
    v = "9" * 64
    a = assets.dat_khoa(owner_id="uA", run_id="asvr_x", stage="compose",
                        van_tay=v, duoi="json")
    b = assets.dat_khoa(owner_id="uA", run_id="asvr_x", stage="compose",
                        van_tay=v, duoi="json")
    assert a == b


def test_hai_van_tay_KHAC_nhau_van_ra_hai_khoa_khac_nhau():
    """Chot chieu nguoc lai: cat qua tay se lam hai artifact khac nhau dung mot
    khoa, va cai sau de len cai truoc — mat du lieu, khong loi nao bao."""
    a = assets.dat_khoa(owner_id="uA", run_id="asvr_x", stage="compose",
                        van_tay="a" * 64, duoi="json")
    b = assets.dat_khoa(owner_id="uA", run_id="asvr_x", stage="compose",
                        van_tay="b" * 64, duoi="json")
    assert a != b
