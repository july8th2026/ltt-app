"""ASV final — lan ocr: DINH TUYEN nguon loi embedded -> OCR -> ASR, co provenance.

Runner OCR gia (`chay=`) tra DUNG hinh dang cua `ocr_khung.py`; ffmpeg/ffprobe
la that (phu de nhung duoc mux that vao mp4).
"""
from __future__ import annotations

import subprocess

import pytest

from apps.asv_gpu.do_luong.venv import KhongKhaDung
from apps.auto_scan_video import ban_ghi, cai_dat, nguon_loi as nl
from tests.fixtures.asv_media import require_ffmpeg, tiny_mp4

SRT = """1
00:00:00,000 --> 00:00:01,200
<i>即使遇到暴风雨</i>

2
00:00:01,300 --> 00:00:02,500
圆拱形状内部的空间
更是相当宽敞
"""


@pytest.fixture(scope="module")
def video_tron(tmp_path_factory):
    return str(tiny_mp4(tmp_path_factory.mktemp("v") / "tron.mp4", duration_s=3))


@pytest.fixture(scope="module")
def video_co_phu_de(tmp_path_factory):
    thu = tmp_path_factory.mktemp("s")
    goc = tiny_mp4(thu / "goc.mp4", duration_s=3)
    srt = thu / "a.srt"
    srt.write_text(SRT, encoding="utf-8")
    ra = thu / "co_phu_de.mp4"
    subprocess.run([require_ffmpeg(), "-v", "error", "-y", "-i", str(goc), "-i", str(srt),
                    "-map", "0", "-map", "1", "-c", "copy", "-c:s", "mov_text",
                    "-metadata:s:s:0", "language=chi", str(ra)], check=True)
    return str(ra)


def _runner_gia(chu_moi_khung=None, *, loi=None):
    """pass1 (khong `cat`): 20 khung, phu de doi chu o day; pass2: dai 5 fps."""
    chu_moi_khung = chu_moi_khung or (["即使遇到暴风雨"] * 6 + ["圆拱形状内部的空间"] * 6)
    goi = []

    def chay(script, dv, **kw):
        goi.append(dv)
        if loi:
            raise loi
        if not dv.get("cat"):
            khung = [{"t": float(i), "dong": [
                {"hop": [300, 515, 560, 564], "chu": f"第{i}句", "diem": 0.99}]}
                for i in range(20)]
        else:
            khung = [{"t": i / 5, "dong": [
                {"hop": [300, 515, 560, 564], "chu": c, "diem": 0.97}]}
                for i, c in enumerate(chu_moi_khung)]
        return {"rong": 864, "cao": 576, "khung": khung, "engine": "rapidocr/gia",
                "ms_moi_khung": 1.0}
    chay.goi = goi
    return chay


# ══ 1. Phu de nhung ═════════════════════════════════════════════════════════

def test_doc_srt_bo_the_va_ghep_dong():
    seg = nl.doc_srt(SRT)
    assert [s["text"] for s in seg] == ["即使遇到暴风雨", "圆拱形状内部的空间 更是相当宽敞"]
    assert seg[0]["start"] == 0.0 and seg[1]["end"] == 2.5


def test_auto_UU_TIEN_phu_de_nhung_va_KHONG_goi_OCR(video_co_phu_de):
    chay = _runner_gia()
    tho, dt = nl.dinh_tuyen(video_co_phu_de, che_do="auto", ngon_ngu_khai="",
                            thoi_luong=3, chay=chay)
    assert dt["nguon_loi"] == "embedded" and dt["codec"] == "mov_text"
    assert tho["language"] == "zh" and len(tho["segments"]) == 2
    assert chay.goi == []


def test_phu_de_nhung_KHAC_ngon_ngu_khai_thi_bo_qua(video_co_phu_de):
    tho, dt = nl.dinh_tuyen(video_co_phu_de, che_do="auto", ngon_ngu_khai="en",
                            thoi_luong=3, chay=_runner_gia())
    assert dt["nguon_loi"] == "asr" and "khong_co_phu_de_nhung" in dt["ly_do"]


def test_EP_embedded_ma_khong_co_thi_bao_khach(video_tron):
    with pytest.raises(nl.KhongCoNguon):
        nl.dinh_tuyen(video_tron, che_do="embedded", ngon_ngu_khai="",
                      thoi_luong=3, chay=_runner_gia())


# ══ 2. Hardsub ══════════════════════════════════════════════════════════════

def test_auto_co_hardsub_chu_Han_thi_nguon_la_OCR(video_tron):
    chay = _runner_gia()
    tho, dt = nl.dinh_tuyen(video_tron, che_do="auto", ngon_ngu_khai="",
                            thoi_luong=3, chay=chay)
    assert dt["nguon_loi"] == "ocr"
    assert [s["text"] for s in tho["segments"]] == ["即使遇到暴风雨", "圆拱形状内部的空间"]
    assert all(s["confidence"] == pytest.approx(0.97) for s in tho["segments"])
    # Pass 2 cat DUNG dai tim o pass 1, fps doc ghim.
    assert chay.goi[1]["cat"][1] < 515 and chay.goi[1]["fps"] == nl.FPS_DOC
    ban = ban_ghi.chuan_hoa(tho, thoi_luong_nguon=3, nguon_loi=dt["nguon_loi"],
                            dinh_tuyen=dt)
    assert ban["nguon_loi"] == "ocr" and ban["doan"][0]["do_tin"] == pytest.approx(0.97)
    assert ban_ghi.tom_tat(ban)["nguon_loi"] == "ocr"


def test_hardsub_KHONG_phai_chu_Han_thi_auto_ve_ASR_co_ly_do(video_tron):
    tho, dt = nl.dinh_tuyen(video_tron, che_do="auto", ngon_ngu_khai="",
                            thoi_luong=3,
                            chay=_runner_gia(["hello world"] * 6 + ["good bye"] * 6))
    assert tho is None and dt["nguon_loi"] == "asr"
    assert "ocr_khong_phai_chu_han" in dt["ly_do"]


def test_nguon_khai_en_thi_auto_KHONG_chay_OCR(video_tron):
    chay = _runner_gia()
    _, dt = nl.dinh_tuyen(video_tron, che_do="auto", ngon_ngu_khai="en",
                          thoi_luong=3, chay=chay)
    assert dt["nguon_loi"] == "asr" and "ocr_chi_do_cho_zh" in dt["ly_do"]
    assert chay.goi == []


def test_OCR_khong_kha_dung_auto_ve_ASR_CO_GHI_ly_do(video_tron):
    _, dt = nl.dinh_tuyen(video_tron, che_do="auto", ngon_ngu_khai="",
                          thoi_luong=3, chay=_runner_gia(loi=KhongKhaDung("x")))
    assert dt["nguon_loi"] == "asr" and "ocr_khong_kha_dung" in dt["ly_do"]


def test_EP_ocr_ma_bo_OCR_khong_kha_dung_thi_BAO_khong_lui_im(video_tron):
    with pytest.raises(nl.KhongCoNguon):
        nl.dinh_tuyen(video_tron, che_do="ocr", ngon_ngu_khai="", thoi_luong=3,
                      chay=_runner_gia(loi=KhongKhaDung("x")))


def test_che_do_asr_khong_doc_video():
    chay = _runner_gia()
    tho, dt = nl.dinh_tuyen("khong-ton-tai.mp4", che_do="asr", ngon_ngu_khai="",
                            thoi_luong=3, chay=chay)
    assert tho is None and dt["nguon_loi"] == "asr" and chay.goi == []


def test_doan_chu_viet_cho_luong_khong_gan_the():
    assert nl.doan_chu_viet("即使遇到暴风雨") == "zh"
    assert nl.doan_chu_viet("Xin chào các bạn đã đến") == "vi"
    assert nl.doan_chu_viet("Hello there") == "en"
    assert nl.doan_chu_viet("こんにちは") == ""


# ══ 3. Thiet lap ════════════════════════════════════════════════════════════

def test_thiet_lap_auto_KHONG_ghi_vao_ho_so_va_van_tay_cu_giu_nguyen():
    tho = {"giong_id": "g", "preset": "x"}
    assert "nguon_loi" not in cai_dat.chuan_hoa({**tho, "nguon_loi": "auto"})
    assert cai_dat.van_tay({**tho, "nguon_loi": "auto"}) == cai_dat.van_tay(tho)
    assert cai_dat.tu_ho_so(tho).nguon_loi == "auto"


def test_thiet_lap_ep_nguon_duoc_ghi_va_doc_lai():
    ho_so = cai_dat.chuan_hoa({"nguon_loi": "ASR"})
    assert ho_so["nguon_loi"] == "asr"
    assert cai_dat.tu_ho_so(ho_so).nguon_loi == "asr"
    assert cai_dat.tu_ho_so({"nguon_loi": "rac"}).nguon_loi == "auto"


def test_CUA_KHACH_ghi_nguon_loi_vao_ho_so_chu_khong_chi_duyet_roi_bo():
    """🔴 **Do that, nghiem thu cuoi 23/09: mot dieu khien CHET.**

    `dich_vu_tao.dung_cai_dat` duyet `nguon_loi` (dong 132-133) roi **khong**
    dat no vao `cai_dat` — ba lan nop `nguon_loi=asr` tren phim khach that, ca
    ba lan `transcribe.tom_tat` ghi `dinh_tuyen.che_do: "auto"` va chay OCR.

    ⛔ Hai phep kiem tren (`test_thiet_lap_*`) goi THANG `cai_dat.chuan_hoa`,
       nen ca hai xanh trong khi duong khach di thi dut. Day dung la
       "hai cho khai cung mot dieu, khong ai bat khop": cua nhan gia tri, kho
       biet luu gia tri, va khong ai doi chieu rang cua CO dua gia tri cho kho.
    """
    from apps.auto_scan_video import dich_vu_tao

    # AUTO_MATCH + giong_id rong: khong tra cuu kho giong, nen phep kiem nay
    # van la mot phep kiem DON VI cua cua tao — khong can CSDL.
    tho = {"preset": "localize_preserve_picture", "che_do_giong": "AUTO_MATCH",
           "giong_id": "", "ngon_ngu_nguon": "zh", "ngon_ngu_dich": "vi"}
    ho_so = dich_vu_tao.dung_cai_dat(None, owner_id="u", tho={**tho, "nguon_loi": "asr"})
    assert ho_so.get("nguon_loi") == "asr", ho_so
    assert cai_dat.tu_ho_so(ho_so).nguon_loi == "asr"

    # ⭐ Va `auto` van KHONG duoc ghi (`KHOA_THUA`): mot ho so mang mot khoa
    #    bang mac dinh la mot van tay doi ma cau hinh thi khong.
    mac_dinh = dich_vu_tao.dung_cai_dat(None, owner_id="u", tho={**tho, "nguon_loi": "auto"})
    assert "nguon_loi" not in mac_dinh
    assert cai_dat.tu_ho_so(mac_dinh).nguon_loi == "auto"
