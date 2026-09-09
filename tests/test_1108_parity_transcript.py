"""Parity App `transcript` <-> bot legacy, do tren job THAT.

Nen cua tep nay la mot phep do tren **1.932 luot job that** o kho vang
`output/<drive_folder_id>/` cua `Bot_Whisper_FULL` (moi thu muc mot cap
`transcript_raw_temp.json` -> `transcript.json`). Ba con so quan trong:

    engine GOC  so voi dau ra CUA CHINH NO : 1850/1932 = 95,76%
    ban CHUYEN  so voi cung dau ra do      : 1845/1932 = 95,50%

🔴 Con so 95,76% cua BAN GOC moi la phat hien. `make_timeline_v2` goi
   `random.uniform` (`segment/silence.py::split_silence_segments_random_2_5`) de
   cat khoang lang dai thanh chunk 2-5 giay — CO CHU Y, de B-ROLL khong deu dan
   may moc. Nen **cung mot dau vao cho ra ket qua khac nhau moi luot goi**, va
   "dau ra trung khop tung byte" la mot muc tieu BAT KHA VE NGUYEN TAC.

   Khong co doi chung do, 95,50% cua ban chuyen doc ra la "thieu 4,5%" va se co
   nguoi di san mot khiem khuyet **khong ton tai**. Bon luot rut moi ben cho
   goc 95,19-95,76% va chuyen 94,93-95,70%; o mot luot ban chuyen VUOT ban goc.

⇒ Bon mau duoi day duoc **CHON**, khong phai lay bua: chung nam trong nhom job
  ma engine chay 20/20 luot ra cung mot ket qua, va ket qua do trung tuyet doi
  voi tep bot da giao that. Nho vay phep kiem nay khang dinh CHINH XAC chu khong
  phai thong ke, va no khong chop chop trong gate.

⚠️ `audio_duration` khong nam trong tep dau vao (no doc tu chinh tep audio, thu
   ta khong con giu). Doc engine thi no cham DUY NHAT doan lang cuoi
   (`word_scene_builder::_assemble_timeline`); moi doan khac sinh tu `words`.
   Nen o day no duoc lay lai tu `vang[-1]["end"]` — cho duy nhat no quan sat
   duoc — va viec do chi anh huong dung doan cuoi.
"""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib

import pytest

from apps.transcript.services import phien_am
from apps.transcript.services.engine.segment import make_timeline_v2
from apps.transcript.services.engine.segment.silence import (
    split_silence_segments_random_2_5,
)

GOC = pathlib.Path(__file__).resolve().parent / "golden" / "parity_transcript"

#: Doc tu `configs/bot_config_whisper.json` DANG CHAY tren may bot, khong phai
#: mac dinh trong ma: `segment.min_s` that la 1.5 con mac dinh cua ham la 3.0.
#: Lay nham mot trong hai la lech parity ngay tu tham so.
THAM_SO = dict(target_min=1.5, target_max=6.0, silence_threshold=2.0,
               silence_text="[B-ROLL / PAUSE]")

#: Hai tang `round(..., 2)` doc lap nhau cong don toi da 0.02. Nguong 0.011 tung
#: bao mot job "dut quang" trong khi CHINH TEP VANG dut y het o dung chi so do,
#: va engine goc tai hien 10/10 luot — tuc nguong sai, khong phai ma sai.
DUNG_SAI = 0.021


def _mau() -> list[pathlib.Path]:
    return sorted(d for d in GOC.iterdir() if d.is_dir())


def _doc(d: pathlib.Path) -> tuple[list[dict], list[dict]]:
    tho = json.loads((d / "transcript_raw_temp.json").read_text(encoding="utf-8"))
    vang = json.loads((d / "transcript.json").read_text(encoding="utf-8"))
    return tho["segments"], vang


def _chay(tho: list[dict], audio_duration: float) -> list[dict]:
    return phien_am._chieu_schema(
        make_timeline_v2(copy.deepcopy(tho), audio_duration=audio_duration,
                         **THAM_SO))


def _bam(x: object) -> str:
    return hashlib.sha256(json.dumps(x, sort_keys=True).encode()).hexdigest()


def test_bo_mau_phu_du_TRUC_khong_phai_nhieu_ban_sao_mot_truong_hop() -> None:
    """Bo mau phai phu cac TRUC, khong phai nam ban sao cua mot truong hop.

    Truc: ngon ngu (vi/en) x kieu ket (noi/lang) x co dung chu lang cau hinh.
    Mau 05 duoc them SAU khi do ra rang bon mau dau **deu truot** nhanh chot cua
    `smart_silence_tag`, tuc tham so `silence_text` khong he duoc ghim boi phep
    kiem nao — trong khi tren toan kho no chiem 13,00% so doan lang.
    """
    st = json.loads((GOC / "so_tay.json").read_text(encoding="utf-8"))
    cap = st["cap"]
    assert len(cap) == 5 == len(_mau())
    assert {c["ngon_ngu"] for c in cap} == {"vi", "en"}
    assert {c["loai_doan_cuoi"] for c in cap} == {"speech", "silence"}
    # Ket bang LANG la truong hop duy nhat `audio_duration` thuc su lam gi do.
    assert sum(c["loai_doan_cuoi"] == "silence" for c in cap) >= 2
    # Va it nhat mot mau phai di qua nhanh chot cua `smart_silence_tag`.
    co_chu = [d for d in _mau()
              if "[B-ROLL / PAUSE]" in (d / "transcript.json").read_text(encoding="utf-8")]
    assert co_chu, "khong mau nao ghim `silence_text` cua cau hinh"


@pytest.mark.parametrize("d", _mau(), ids=lambda p: p.name)
def test_tham_so_cua_CAU_HINH_SONG_la_thu_ganh_ket_qua(d: pathlib.Path) -> None:
    """Lay mac dinh trong MA thay vi cau hinh dang chay la lech parity ngay.

    `segment.min_s` tren may bot la **1.5**; mac dinh cua `make_timeline_v2` la
    **3.0**. Hai so nay khac nhau, va khong co gi trong ma noi ra dieu do — chi
    doc `configs/bot_config_whisper.json` moi biet. Phep kiem nay giu cho lan
    don dep sau khong "gian luoc" ve mac dinh.
    """
    tho, vang = _doc(d)
    ad = float(vang[-1]["end"])
    assert _chay(tho, ad) == vang
    for ten, doi in (("target_min", 3.0), ("target_max", 5.5)):
        khac = dict(THAM_SO, **{ten: doi})
        ra = phien_am._chieu_schema(
            make_timeline_v2(copy.deepcopy(tho), audio_duration=ad, **khac))
        assert ra != vang, f"doi {ten} thanh {doi} ma ket qua khong doi"


@pytest.mark.parametrize("d", _mau(), ids=lambda p: p.name)
def test_khop_TUYET_DOI_voi_dau_ra_bot_da_giao_that(d: pathlib.Path) -> None:
    tho, vang = _doc(d)
    assert _chay(tho, float(vang[-1]["end"])) == vang


@pytest.mark.parametrize("d", _mau(), ids=lambda p: p.name)
def test_bon_mau_nay_TAT_DINH_qua_20_luot(d: pathlib.Path) -> None:
    """Dieu kien de bon mau tren duoc chon — va la thu se do neu ai doi engine."""
    tho, vang = _doc(d)
    ad = float(vang[-1]["end"])
    assert len({_bam(_chay(tho, ad)) for _ in range(20)}) == 1


@pytest.mark.parametrize("d", _mau(), ids=lambda p: p.name)
def test_dong_thoi_gian_lien_tuc_trong_dung_sai_hai_lan_lam_tron(
        d: pathlib.Path) -> None:
    tho, vang = _doc(d)
    ra = _chay(tho, float(vang[-1]["end"]))
    for i in range(1, len(ra)):
        ho = abs(float(ra[i]["start"]) - float(ra[i - 1]["end"]))
        assert ho <= DUNG_SAI, f"ho {ho:.4f}s tai doan {i}"


@pytest.mark.parametrize("d", _mau(), ids=lambda p: p.name)
def test_moi_doan_ra_dung_sau_khoa_va_khong_bao_gio_co_words(
        d: pathlib.Path) -> None:
    tho, vang = _doc(d)
    for doan in _chay(tho, float(vang[-1]["end"])):
        assert set(doan) == set(phien_am.KHOA_DAY_DU)
        assert "words" not in doan


def test_engine_THAT_SU_ngau_nhien_nen_mau_phai_duoc_CHON() -> None:
    """Vi sao bon mau tren khong the lay bua.

    `split_silence_segments_random_2_5` la nguon ngau nhien, va no CO CHU Y. Neu
    mot ngay nao do ai do "sua" no thanh tat dinh, phep kiem nay do — va ho doc
    duoc ngay tai day rang dau ra cua bot that KHONG tat dinh, nen moi ket luan
    parity dung tren gia dinh nguoc lai deu sai.
    """
    khe = [{"start": 0.0, "end": 60.0}]
    ket = {_bam(split_silence_segments_random_2_5(khe, min_silence_keep=2.0))
           for _ in range(20)}
    assert len(ket) > 1, "engine da thanh tat dinh — doc lai docstring tep nay"


@pytest.mark.parametrize("d", _mau()[:1], ids=lambda p: p.name)
def test_phep_so_sanh_BIET_BAO_DO(d: pathlib.Path) -> None:
    """Doi chung: mot phep so khong bao gio do thi khong chung minh duoc gi.

    Tiem ba kieu hong vao ban vang roi doi hoi phep so tu choi ca ba.
    """
    tho, vang = _doc(d)
    ra = _chay(tho, float(vang[-1]["end"]))
    assert ra == vang

    lech_moc = copy.deepcopy(vang)
    lech_moc[0]["end"] = float(lech_moc[0]["end"]) + 0.5
    assert ra != lech_moc

    lech_chu = copy.deepcopy(vang)
    lech_chu[0]["text"] = str(lech_chu[0]["text"]) + " x"
    assert ra != lech_chu

    thieu_doan = copy.deepcopy(vang)[:-1]
    assert ra != thieu_doan


def test_bo_mau_KHONG_mang_theo_drive_folder_id() -> None:
    """Ten thu muc goc la Drive folder ID — CLAUDE.md cam chep di.

    So tay chi giu SHA-256, du de truy nguoc bang cach quet lai cay production
    ma khong xuat ban chinh id do.
    """
    st = json.loads((GOC / "so_tay.json").read_text(encoding="utf-8"))
    for c in st["cap"]:
        assert len(c["bam_id_nguon"]) == 64
        assert not c["ten"].startswith("1")   # id Drive deu bat dau bang "1"
    van = "\n".join(p.read_text(encoding="utf-8", errors="ignore")
                    for p in GOC.rglob("*.json"))
    assert "drive.google.com" not in van
