"""Rao chan cho phep kiem NANG — thu khoi dong mot model that.

## Vi sao tep nay ton tai

`tests/test_406::test_tach_nguon_ra_du_BON_stem` goi **demucs that**, khong
marker, khong bien moi truong, khong skip. Va no chay giua mot luot gate, tren
mot may **dang phuc vu khach** (`C:\\LTTPlatform` ton tai: LTTStudioWeb, Worker,
Voice, Codex deu chay).

⚠️ **MOT DINH CHINH, giu lai vi ban dau toi viet sai o day.**

   Doan nay ban dau noi gate chay `pytest -n auto` = 20 worker, va rang tai
   "khong CONG ma NHAN". **Khong con dung.** `gate.py:490` truyen
   `-n str(loi_bo_test)` voi `ngan_sach_loi() = cpu_count() - 6` = **14** tren
   may nay, va `tests/test_394:324` co mot phep kiem chot rang `-n auto` khong
   duoc quay lai.

   Toi doc `gate.py:72` — mot **chu thich mo ta co che CU**, nam trong khoi giai
   thich vi sao no da duoc sua — roi doc no thanh hien trang. Phien
   `lttstudiosapp-73` chi ra, va ho dung.

⭐ Con so doi, ly do thi khong. `--dist loadfile` gui tron mot tep cho mot worker
   nen demucs **khong nhan len**; nhung mot model ML that van nap trong so va an
   het phan CPU con lai cua mot may dang phuc vu khach, giua mot luot do dat
   tien. Rao no lai van dung — chi la dung vi mot ly do nho hon ly do toi tuong.

⛔ Va bai hoc chung hon, vi no lap lai nam lan trong phien nay: **mot chu thich
   noi ve luc no duoc viet, khong noi ve luc ban doc no.**

`pipeline.CHUOI` da khai `tai_nguyen="tach_nguon_cuc_bo"` de nen tang dieu tiet
— nhung do la o **hang doi**. pytest khong di qua hang doi. Nen o day can mot
rao khac.

## Rao la BIEN MOI TRUONG, khong phai mot co `-m`

Mot marker chi loc khi co nguoi go `-m "not nang"`. Ai quen go la model that
chay lai. `skipif` doc bien moi truong thi **mac dinh la bo qua**, va muon chay
thi phai noi ra:

    set LTT_TEST_NANG=1
    python -m pytest tests/test_406_asv_tach_tieng.py -q

⭐ Marker `nang` VAN duoc dat kem, nhung de **chon** (`-m nang`) chu khong de
   **chan**. Hai viec khac nhau, va gop chung lai la cach mat ca hai.

## Cai gi tinh la "nang"

Nap trong so model len RAM/VRAM, hoac goi mot dich vu sinh noi dung that.
`ffmpeg` KHONG tinh: no la cong cu, chay vai tram mili giay, va moi giai doan
media deu can no — rao no lai la lam ca bo test vo nghia.
"""
from __future__ import annotations

import os

import pytest

#: Bat bang `set LTT_TEST_NANG=1`. Bat ky gia tri khac rong deu tinh la bat.
BIEN = "LTT_TEST_NANG"

LY_DO = (
    f"phep kiem NANG (nap model that). Bat bang {BIEN}=1. "
    "Mac dinh bo qua vi may nay dang phuc vu khach — xem tests/rao_chan_nang.py")


def bat() -> bool:
    return bool(os.environ.get(BIEN, "").strip())


#: Dat CA HAI len mot phep kiem nang:
#:
#:     @rao_chan_nang.NANG
#:     @rao_chan_nang.CHI_KHI_BAT
#:     def test_...():
#:
#: `NANG` de chon duoc; `CHI_KHI_BAT` de mac dinh khong chay.
NANG = pytest.mark.nang
CHI_KHI_BAT = pytest.mark.skipif(not bat(), reason=LY_DO)
