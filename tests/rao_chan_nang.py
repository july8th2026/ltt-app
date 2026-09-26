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


# ══════════════════════════════════════════════════════════════════════════════
#  Gia lap demucs — de mot phep kiem chay HET chuoi ma khong nap model
# ══════════════════════════════════════════════════════════════════════════════

def gia_lap_demucs(monkeypatch):
    """Thay tien trinh con demucs bang mot ham sinh stem hop le trong tich tac.

    🔴 **Vi sao can:** rao chan o tep nay duoc dan len nhung phep kiem GOI THANG
       demucs. Pha 13 tim ra `test_406::test_cong_thoat_ban_nen_...` voi toi
       demucs **gian tiep qua hang doi job**, nen no khong bi rao va da nap model
       THAT 16 giay moi luot gate.

    ⭐ Nhung cau tra loi khong phai "rao not phep kiem do lai". Phep kiem do dang
       kiem mot thu THAT SU quan trong — ca chuoi tu hang doi den artifact, tron
       nen, chuan am luong, dong lineage. Rao no lai la mat phep kiem do.

    ⇒ Nen thay vi bo, ta **thay dung mot mieng**: mieng nang duy nhat (model) la
      gia, moi thu con lai — ffmpeg that, kho that, CSDL that, worker that — van
      chay that. Do la cai phep kiem do dinh do ngay tu dau.

    ⛔ Stem gia phai la WAV PCM 16-bit THAT, dung tan so, dung do dai: buoc tron
       nen va buoc kiem thoi luong o sau no la that va se bat moi cho lam au.
    """
    import json
    import subprocess
    import wave
    from pathlib import Path

    from apps.auto_scan_video import demucs_runner, tach_tieng

    def gia(cmd, *, timeout, hoi_huy, moi_truong):
        vao, thu_muc = cmd[-2], Path(cmd[-1])
        thu_muc.mkdir(parents=True, exist_ok=True)
        with wave.open(vao, "rb") as f:
            kenh, tan_so, so_khung = f.getnchannels(), f.getframerate(), f.getnframes()
            khung = f.readframes(so_khung)
        duong = {}
        for i, ten in enumerate(demucs_runner.NGUON_MONG_DOI):
            d = thu_muc / f"{ten}.wav"
            with wave.open(str(d), "wb") as w:
                w.setnchannels(kenh); w.setsampwidth(2); w.setframerate(tan_so)
                # Nguon dau giu nguyen tieng, ba nguon sau im lang: tong lai van
                # dung do dai va dung dinh dang, tuc buoc kiem sau no van co viec.
                w.writeframes(khung if i == 0 else b"\x00" * len(khung))
            duong[ten] = str(d)
        ra = json.dumps({"nguon": list(demucs_runner.NGUON_MONG_DOI),
                         "duong": duong, "tan_so": tan_so,
                         "thiet_bi": "gia_lap", "so_khoi": 1})
        return subprocess.CompletedProcess(cmd, 0, ra.encode("utf-8"), b"")

    monkeypatch.setattr(tach_tieng, "_chay_kem_moi_truong", gia)


def gia_lap_asr(monkeypatch):
    """Thay engine ASR that bang mot ban ghi xac dinh.

    🔴 **Vi sao can, va vi sao no giong het cau chuyen cua demucs.** Pha 13 tim
       ra `test_406::test_cong_thoat_ban_nen_...` goi demucs **gian tiep qua hang
       doi**, nen rao chan — dan len nhung nguoi goi THANG — khong thay no. Pha
       23 tim ra rang **cung phep kiem do** cung voi toi ASR that theo dung cach
       do: no chay het hang doi voi nang luc `gpu`, va `transcribe` la mot giai
       doan `gpu`.

    ⛔ Va lan nay cai gia cao hon mot lan nap model: `autosubvideo._get_faster_model`
       mac dinh `device="cuda"`, va tren may nay duong CUDA cua faster-whisper
       **treo**. Do duoc o pha 22: hon bay phut khong ket qua va khong loi, so
       voi 7,5 giay tren CPU. Mot phep kiem treo vo han thi khong con la mot phep
       kiem cham — no la mot luot gate khong bao gio ket thuc.

    ⭐ Xac nhan bang chinh tien trinh dang treo: no da nap `ctranslate2.dll`,
       `cudnn64_9.dll` va `nvcuda.dll`.

    ⇒ Mieng NANG duy nhat (model) la gia; hang doi, worker, ffmpeg, kho, CSDL,
      lineage van that — dung nguyen tac cua `gia_lap_demucs`.
    """
    from apps.auto_scan_video import giai_doan_chep_loi
    from tests.fixtures.asv_media import ban_ghi_gia

    monkeypatch.setattr(giai_doan_chep_loi, "chep_loi",
                        lambda duong_tieng, **kw: ban_ghi_gia())


def gia_lap_do_luong(monkeypatch):
    """Giai doan `qc_do_luong` (22/09) nap whisper + SQUIM trong `qc-venv`.

    ⭐ Khong gia lap ket qua: tro `LTT_QC_PYTHON` toi mot duong KHONG ton tai, tuc
       dung canh "may chua cai venv do luong". Giai doan di dung nhanh san pham
       that cua no — moi bo do `khong_kha_dung`, giai doan van `succeeded`, vong
       sua khong co gi de doc — ma khong nap mot trong so nao.
    """
    from pathlib import Path

    monkeypatch.setenv("LTT_QC_PYTHON",
                       str(Path(__file__).parent / "_khong_co_qc_venv" / "python.exe"))


# ⛔ `gia_lap_ocr` DA XOA 26/09 (Task 21). Rao do ton tai vi TRANSCRIBE o che do
#    `auto` chay OCR (RapidOCR trong venv do luong) TREN VIDEO NGUON truoc ASR,
#    nen moi phep kiem chuoi tren may da cai venv do luong se nap model OCR that.
#
# ⭐ Nay TRANSCRIBE chi doc BAN TIENG (mot duong duy nhat voice->voice), nen
#    ⛔ khong con duong nao nap model OCR ⇒ khong con gi de rao. Xoa rao la dung;
#    giu lai mot `monkeypatch.setattr` tro vao mot ham khong ton tai se nem
#    `AttributeError` o MOI tep test da nap fixture nay.


@pytest.fixture(autouse=True)
def demucs_gia_lap(monkeypatch):
    """Fixture AUTOUSE **pham vi tep** — nap vao mot tep test bang mot dong:

        from tests.rao_chan_nang import demucs_gia_lap   # noqa: F401

    ⛔ Co y KHONG dat o `tests/conftest.py`: dau tep do noi thang "dung them
       `autouse` moi vao day tru khi no that su dung cho MOI test", va no chi ra
       dung khuon nay — tep test cua mot mien tu boc lay minh. Mot fixture
       autouse toan cuc la mot khoan thue thu tren ca bo test de phuc vu mot app.

    🔴 **Pha 13 do ra pham vi that cua van de:** khong phai mot phep kiem nap
       demucs that, ma **31 phep kiem trong 9 tep** — deu la kiem chuoi tu dau
       den cuoi (QC, vong doi artifact, vo hieu ha nguon, tiem loi...), va
       **khong tep nao trong so do noi ve demucs**. Chung cham toi model chi vi
       chuoi di qua `audio_prepare`.

    ⭐ Chung khong bi bat vi rao chan cu duoc dan len hai HAM GOI THANG demucs.
       Mot rao dat o nguoi goi chi thay nhung nguoi goi no biet.

    Muon chay that: `set LTT_TEST_NANG=1` — khi do fixture nay tu tranh ra.
    """
    if bat():
        yield
        return
    gia_lap_demucs(monkeypatch)
    gia_lap_do_luong(monkeypatch)
    yield
