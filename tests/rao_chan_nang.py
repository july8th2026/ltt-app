"""Rao chan cho phep kiem NANG — thu khoi dong mot model that.

## Vi sao tep nay ton tai

`tests/test_406::test_tach_nguon_ra_du_BON_stem` goi **demucs that**, khong
marker, khong bien moi truong, khong skip. `tools/test_nhanh.py` chay
`pytest -n auto` = 20 worker tren may nay, va may nay **dang phuc vu khach**
(`C:\\LTTPlatform` ton tai: LTTStudioWeb, Worker, Voice, Codex deu chay).

Ngay 02/09 chu du an phai **reset cung may hai lan**. Phien `lttstudiosapp-a1`
truy ra: tai khong CONG ma NHAN, vi mot model nang chay ben trong mot worker cua
mot bo test da song song.

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
    "Mac dinh bo qua vi may nay dang phuc vu khach va bo test chay 20 worker "
    "song song — xem tests/rao_chan_nang.py")


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
