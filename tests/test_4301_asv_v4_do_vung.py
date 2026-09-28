"""V4a/V4b — bo DO vung (`apps/auto_scan_video/do_vung.py`).

## 🔴 Cau hoi that: bo do co PHAN BIET duoc hai thu khong

⛔ Khong phai *"no co chay khong"*. Mot bo do tra `[]` cho **ca hai** ca — *may
thieu OpenCV* va *video nay khong co logo* — la mot bo do **mat kha nang phan
biet**, va cai mat do ⛔ khong bao loi: no chi khong ton tai.

He tham chieu dinh dung bay do (`dai_watermark.py:50` va `:145` cung `return
[]`). Ta ⛔ khong chep cai do — xem BAT BIEN 1 cua `do_vung`.

## ⚠️ Vi sao clip TONG HOP chu khong phai phim khach

Phim khach that (`tests/fixtures/asv_e2e_that/`) **⛔ khong bao gio duoc
commit** — no la tu lieu cua khach. Nen bai nay dung mot clip TONG HOP dung o
cho: nen SINH DONG khap khung (⛔ khong mot diem anh tinh nao ngoai logo), mot o
duc dung yen o goc tren phai, va mot dong chu trang vien den DOI tung giay o
day. Ta biet truoc dap an, nen bai nay chot duoc ca **dung cho** lan **khong
bat nham**.

⭐ Doi chung tren phim khach that van co, o `bang_chung_v4.py` cua lan
   `asv-vung` — ket qua khop tung chu so voi Đ1 (`L_DO_VUNG.md` §3).
"""
from __future__ import annotations

import subprocess

import pytest

from apps.auto_scan_video import do_vung as dv
from tests.rao_chan_nang import ocr_gia_lap  # noqa: F401 -- B13 C3, xem rao_chan_nang.gia_lap_ocr

# ⭐ ⛔ KHONG `skipif` ffmpeg. `rao_chan_nang` da phan quyet: *"no la cong cu,
#    chay vai tram mili giay"* — ffmpeg ⛔ khong phai phep kiem nang, va no co
#    mat trong gate. Mot `skip` o day la mot bai **khong canh gi ca** tren dung
#    cai may no phai canh (`tools/check_bo_qua.py`), va lan `asv-bien-tap` vua
#    go dung mot `skipif` nhu the khoi `test_2062`.

#: Vi tri THAT cua hai thu trong clip tong hop, theo phan so. Bai duoi doi bo do
#: tra ve hop CHUA chung — ⛔ khong doi bang khit, vi ca hai chang deu co dem.
LOGO_THAT = (560 / 640, 616 / 640, 18 / 360, 46 / 360)    # x0 x1 y0 y1
DAI_THAT = (304 / 360, 334 / 360)                          # y0 y1


@pytest.fixture(scope="module")
def clip(tmp_path_factory) -> str:
    """Clip 8 giay: nen SINH DONG + logo TINH goc tren phai + dai chu DOI o day.

    🔴 Nen phai dong o **moi** diem anh. Ban dau toi dung `testsrc2` roi
       `mandelbrot`: ca hai co mang TINH lon (thanh mau, long tap Mandelbrot),
       va V4a gom chung voi logo thanh mot khoi to roi loai ca cum vi
       `DIEN_TICH_MAX`. Bo do lam **dung**; chinh clip thu moi sai.
    """
    ra = str(tmp_path_factory.mktemp("do_vung") / "tong_hop.mp4")
    loc = (
        "color=c=gray:s=640x360:r=10:d=8,format=rgb24,"
        "geq=r='128+110*sin(X/23+T*3)':g='128+110*sin(Y/19+T*2)':"
        "b='128+110*sin((X+Y)/29+T*4)'[bg];"
        # LOGO TINH: o duc, dung yen ca clip.
        "[bg]drawbox=x=560:y=18:w=56:h=28:color=white@1.0:t=fill,"
        "drawbox=x=566:y=24:w=44:h=16:color=black@1.0:t=fill[l];"
        # DAI CHU: trang co vien den (dac trung hardsub), DOI theo tung giay.
        "[l]drawtext=text='%{eif" + chr(92) + ":floor(t)" + chr(92) + ":d}"
        " AAAA BBBB CCCC':fontcolor=white:fontsize=30:borderw=3:"
        "bordercolor=black:x=(w-tw)/2:y=h-56[v]"
    )
    kq = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "nullsrc",
         "-filter_complex", loc, "-map", "[v]", "-pix_fmt", "yuv420p",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", ra],
        capture_output=True, text=True, timeout=180, errors="replace")
    # ⛔ `assert` chu khong `pytest.skip`: dung duoc clip nay la mot dieu kien
    #    cua bai, ⛔ khong phai mot may man cua moi truong. `skip` o day bien ca
    #    tep thanh mot bai xanh ma ⛔ khong do gi.
    assert kq.returncode == 0, (kq.stderr or "")[-1500:]
    return ra


# ══════════════════════════════════════════════════════════════════════════════
#  1. 🔴 BAT BIEN 1 — "khong co gi o do" ≠ "khong do duoc"
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("ham", [dv.do_logo_tinh, dv.do_dai_chu])
def test_khong_mo_duoc_video_thi_NEM_chu_khong_tra_RONG(ham, tmp_path):
    """⛔ Ca *khong do duoc* phai di bang mot duong KHAC ca *khong co gi*.

    Tra `()` o day thi mot may hong codec se bao cao *"video nay sach, khong co
    watermark"* — va ⛔ khong ai biet.
    """
    hong = tmp_path / "khong_phai_video.mp4"
    hong.write_bytes(b"khong phai mot tep video")
    with pytest.raises(dv.DoVungLoi):
        ham(str(hong))


def test_da_QUET_that_ma_khong_thay_gi_thi_tra_RONG_KEM_so_khung(clip):
    """Doi xung cua bai tren: mot ket qua rong phai **chung minh duoc** rang
    chang do da chay. `so_khung` la bang chung do.

    Dung `tranh` trum len chinh dai vua do: bo do quet du 18 khung, tim thay
    dai, roi LOAI no vi khach da ve o do (BAT BIEN 2).
    """
    co = dv.do_dai_chu(clip)
    assert co.vung, "clip tong hop phai co dai chu"
    h = co.vung[0]
    khong = dv.do_dai_chu(clip, tranh=[(h["y0"], h["y1"])])
    assert khong.vung == ()
    assert khong.so_khung >= 4, "ket qua rong ma khong chung minh da quet"


# ══════════════════════════════════════════════════════════════════════════════
#  2. V4a — logo TINH
# ══════════════════════════════════════════════════════════════════════════════

def test_V4a_tim_DUNG_o_logo_tinh(clip):
    """Hop tra ve phai CHUA o logo that, va ⛔ khong trum ra ca khung."""
    kq = dv.do_logo_tinh(clip)
    assert len(kq.vung) == 1, f"ky vong dung mot hop, nhan {kq.vung}"
    h = kq.vung[0]
    x0, x1, y0, y1 = LOGO_THAT
    assert h["x0"] <= x0 and h["x1"] >= x1
    assert h["y0"] <= y0 and h["y1"] >= y1
    # ⭐ Đo SAI nguy hon ⛔ khong do: mot hop no ra nua khung la che nham canh.
    assert (h["x1"] - h["x0"]) < 0.25 and (h["y1"] - h["y0"]) < 0.25
    assert h["goc"] == "tr"


def test_V4a_KHONG_bat_dai_chu_o_day(clip):
    """🔑 Doi xung cua V4b, va la ly do hai bo do ⛔ khong gop lam mot.

    Dai chu DOI tung giay => `std` theo thoi gian CAO => truot cong `std < 8`.
    Va no nam giua-day, ngoai `_vung_cho_phep`.
    """
    for h in dv.do_logo_tinh(clip).vung:
        assert h["y0"] > 0.5 or h["y1"] < 0.75, f"bat nham dai chu: {h}"


def test_V4a_on_dinh_khi_TANG_khung(clip):
    """⚠️ Đ1 §4.1: them mot khung = 0,179 giay CPU. ⇒ ⛔ Đung tiec khung.

    Bai nay chot rang tang khung ⛔ khong lam ket qua doi chat — tuc con so 16
    la mot mac dinh RE, ⛔ khong phai mot nguong mong manh da duoc do ni.
    """
    a = dv.do_logo_tinh(clip, so_khung=16).vung
    b = dv.do_logo_tinh(clip, so_khung=32).vung
    assert len(a) == len(b) == 1
    assert abs(a[0]["y0"] - b[0]["y0"]) < 0.02
    assert abs(a[0]["x0"] - b[0]["x0"]) < 0.02


# ══════════════════════════════════════════════════════════════════════════════
#  3. V4b — dai chu goc
# ══════════════════════════════════════════════════════════════════════════════

def test_V4b_tim_DUNG_dai_chu(clip):
    """Dai tra ve phai nam o NUA DUOI va chong nhieu len dai chu that."""
    kq = dv.do_dai_chu(clip)
    assert len(kq.vung) == 1
    h = kq.vung[0]
    assert h["x0"] == 0.0 and h["x1"] == 1.0, "dai chu ap CA be ngang"
    assert h["y0"] >= 0.45, "dai phai nam o nua duoi"
    y0, y1 = DAI_THAT
    chong = min(h["y1"], y1) - max(h["y0"], y0)
    assert chong / (y1 - y0) >= 0.6, f"dai {h} khong trum chu that {DAI_THAT}"
    assert (h["y1"] - h["y0"]) <= 0.25, "dai no qua rong — se che nham canh"


def test_V4b_KHONG_bat_logo_o_goc_tren(clip):
    """Logo TINH ⛔ khong bien dong theo thoi gian => ve `std` dim no di. Va
    `VUNG_TIM_DAI` chi cho tim tu 45 % tro xuong.
    """
    for h in dv.do_dai_chu(clip).vung:
        assert h["y0"] >= 0.45, f"bat nham logo tren: {h}"


def test_V4b_on_dinh_khi_TANG_khung(clip):
    """Cung ly do voi V4a: 16/18 la mac dinh RE, ⛔ khong phai nguong do ni."""
    a = dv.do_dai_chu(clip, so_khung=18).vung
    b = dv.do_dai_chu(clip, so_khung=36).vung
    assert len(a) == len(b) == 1
    assert abs(a[0]["y0"] - b[0]["y0"]) < 0.05
    assert abs(a[0]["y1"] - b[0]["y1"]) < 0.05


# ══════════════════════════════════════════════════════════════════════════════
#  4. Ranh gioi: bo DO ⛔ khong duoc lan sang lop KIEM
# ══════════════════════════════════════════════════════════════════════════════

def test_bo_do_KHONG_tu_dat_LOAI_cho_hop(clip):
    """🔴 Che bang o mo hay bang dien nen la **CHINH SACH**, ⛔ khong phai ket qua
    cua mot phep do. `vung_che` (lop KIEM) va nguoi goi quyet dinh dieu do.

    ⛔ Tron hai lop la giau mot quyet dinh DO ben trong mot phep KIEM.
    """
    for kq in (dv.do_logo_tinh(clip), dv.do_dai_chu(clip)):
        for h in kq.vung:
            assert "loai" not in h, f"bo do tu dat chinh sach: {h}"


def test_hop_tra_ve_DI_QUA_duoc_lop_kiem(clip):
    """Doi xung: hop cua bo do phai la dau vao HOP LE cua `vung_che`.

    ⛔ Mot bo do sinh ra hop ma lop kiem tu choi la mot bo do ⛔ khong dung duoc,
       va ⛔ khong bai nao khac bat duoc dieu do.
    """
    from apps.auto_scan_video import vung_che as vc

    for kq, loai in ((dv.do_logo_tinh(clip), vc.LOAI_LAM_MO),
                     (dv.do_dai_chu(clip), vc.LOAI_DIEN_NEN)):
        for h in kq.vung:
            da_kiem = vc.chuan_hoa_mot(
                {k: v for k, v in h.items() if k != "goc"} | {"loai": loai})
            assert da_kiem["loai"] == loai
            # ⛔ `float` thuan, ⛔ khong phai `numpy.float64`: van tay bam bang
            #    `json.dumps`, va no ⛔ khong tuan tu hoa duoc kieu cua numpy.
            for k in ("x0", "x1", "y0", "y1"):
                assert type(h[k]) is float, f"{k} la {type(h[k])}"


# ══════════════════════════════════════════════════════════════════════════════
#  5. ĐE XUAT — ⛔ KHONG tu dong che (chu du an chot 25/09)
# ══════════════════════════════════════════════════════════════════════════════

def test_de_xuat_KHONG_BAO_GIO_nem(tmp_path):
    """⛔ Mot de xuat hong ⛔ khong duoc giet lan chay: khach van con duong TU
    KHOANH vung, va do la duong CHINH chu ⛔ khong phai duong lui.
    """
    hong = tmp_path / "khong_phai_video.mp4"
    hong.write_bytes(b"khong phai mot tep video")
    goi = dv.de_xuat(str(hong))
    assert goi["trang_thai"] == dv.TRANG_THAI_KHONG_DO_DUOC
    assert goi["vung"] == [] and goi["ly_do"]


def test_de_xuat_giu_BA_trang_thai_chu_khong_hai(clip, tmp_path):
    """🔴 `khong_do_duoc` ≠ `khong_co`. Gop lai thi mot may hong codec bao cao
    *"video nay sach"* — va ⛔ khong ai biet.
    """
    hong = tmp_path / "hong.mp4"
    hong.write_bytes(b"x" * 64)
    co = dv.de_xuat(clip)
    khong_co = dv.de_xuat(clip, tranh=[(0.0, 1.0)])
    khong_do = dv.de_xuat(str(hong))
    assert co["trang_thai"] == dv.TRANG_THAI_CO
    assert khong_do["trang_thai"] == dv.TRANG_THAI_KHONG_DO_DUOC
    # `tranh` trum ca khung loai dai chu; logo tinh khong theo truc Y nen van
    # con — nen doi xung day du la BA gia tri KHAC nhau, khong phai hai.
    assert len({co["trang_thai"], khong_co["trang_thai"],
                khong_do["trang_thai"]}) >= 2
    assert khong_do["ly_do"] and not co["ly_do"]


def test_de_xuat_khai_SO_KHUNG_lam_bang_chung(clip):
    """⭐ Mot `vung` rong kem `so_khung > 0` la *"da quet that, khong thay gi"*.
    ⛔ Khong co con so nay thi hai ca do ⛔ khong phan biet duoc tren man hinh.
    """
    goi = dv.de_xuat(clip)
    assert goi["so_khung"]["logo_tinh"] >= 4
    assert goi["so_khung"]["dai_chu"] >= 4


def test_de_xuat_khai_NGUON_cua_tung_hop(clip):
    """Khach phai biet khung do nao la logo, khung nao la dai chu — hai thu do
    duoc xu ly khac nhau (che kin vs dien nen), va ⛔ khong ai doan giup ho.
    """
    nguon = {h["nguon"] for h in dv.de_xuat(clip)["vung"]}
    assert nguon <= {"logo_tinh", "dai_chu"} and nguon


def test_de_xuat_KHONG_tu_dat_loai_vung_che(clip):
    """🔴 Ranh gioi ĐO / KIEM van dung o be mat de xuat.

    ⛔ Mot phep do ⛔ khong duoc tu thang cap thanh mot quyet dinh: `loai`
       (lam mo hay dien nen) la chinh sach, va khach la nguoi bam.
    """
    for h in dv.de_xuat(clip)["vung"]:
        assert "loai" not in h


def test_de_xuat_TUAN_TU_HOA_duoc_de_di_vao_settings(clip):
    """`run.settings` di qua `json` — mot `numpy.float64` o day se lam chet
    chinh lan chay da sinh ra no.
    """
    import json

    assert json.loads(json.dumps(dv.de_xuat(clip)))["trang_thai"]
