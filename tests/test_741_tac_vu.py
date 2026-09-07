"""HM-4 — danh mục tác vụ: quyết định của người, **được máy kiểm lại**.

## Vì sao hai phần, không phải một

Đo trên bản ghi thật: **150/225 model khai `text_to_video`**. Dữ liệu của WanGP
nói model nào *làm được*, nó **không** nói model nào *nên dùng*. Nên một tác vụ
gồm:

    dau_vao  — suy TU DU LIEU  (so_dang_ky loc ra tap ung vien)
    model    — QUYET DINH cua nguoi, kem can cu

⛔ Bỏ vế thứ hai để "tự động hoàn toàn" nghĩa là chọn bừa một trong 150 model,
   và người dùng trả tiền cho lựa chọn ấy.

⭐ Nhưng quyết định vẫn phải **kiểm được**, nếu không nó sẽ trôi: model bị đổi
  tên ở bản WanGP sau, hoặc thôi không khai vai trò mà tác vụ cần, và cả hai đều
  im lặng cho tới lúc một người dùng thật bấm nút.
"""
from __future__ import annotations

import pytest

from apps.lttvideo import so_dang_ky as sd
from apps.lttvideo import tac_vu as tv_mod
from apps.lttvideo.cong.may_gia_lap import MayGiaLap


@pytest.fixture(scope="module")
def so():
    return sd.nap(MayGiaLap())


@pytest.fixture(scope="module")
def may():
    return MayGiaLap()


CO_MODEL = [t for t in tv_mod.TAC_VU.values() if t.model]


# ══════════════════════════════════════════════════════════════════════════
#  1. Quyet dinh cua nguoi phai DUNG voi du lieu cua may
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("tv", CO_MODEL, ids=lambda t: t.ma)
def test_model_da_chon_CO_THAT_trong_ban_ghi(tv, so):
    """Model bị đổi tên ở bản WanGP sau thì phải đỏ **ở đây**, không phải ở lúc
    một người dùng thật bấm nút."""
    assert tv.model in so.theo_model, (
        f"tac vu {tv.ma!r} chon model {tv.model!r} khong co trong "
        f"{len(so)} model da ghi")


@pytest.mark.parametrize("tv", CO_MODEL, ids=lambda t: t.ma)
def test_model_da_chon_KHAI_DU_vai_tro_tac_vu_can(tv, so):
    """🔑 Phép kiểm trung tâm.

    ⛔ WanGP **bỏ qua media mà model không khai** — không lỗi, không cảnh báo.
       Ta chỉ biết khi xem video ra và không thấy ảnh của mình trong đó. Một
       thất bại không để lại dấu vết nào ở phía máy chủ.
    """
    khai = sd._vai_tro(so.sieu(tv.model))
    thieu = [x for x in tv.dau_vao if x not in khai]
    assert not thieu, (
        f"tac vu {tv.ma!r} can {thieu} nhung model {tv.model!r} khong khai — "
        "WanGP se BO QUA media do, im lang")


@pytest.mark.parametrize("tv", CO_MODEL, ids=lambda t: t.ma)
def test_moi_quyet_dinh_deu_kem_CAN_CU(tv):
    """Một quyết định không kèm căn cứ là một quyết định không ai dám đổi — và
    thứ không ai dám đổi thì ở lại mãi kể cả khi đã sai."""
    assert len(tv.can_cu) > 30, f"tac vu {tv.ma!r} thieu can cu"


# ══════════════════════════════════════════════════════════════════════════
#  2. Vai tro phai CO THAT — doi chung chong go sai
# ══════════════════════════════════════════════════════════════════════════

def test_moi_vai_tro_cua_moi_tac_vu_deu_co_model_khai(so):
    """⛔ Một vai trò gõ sai (`image.first` thay vì `image.start`) khớp **0
    model**, và tác vụ ấy sẽ **im lặng biến mất** khỏi giao diện. Không lỗi,
    không log — chỉ là một mục không bao giờ hiện ra."""
    co_that = so.vai_tro_co_that()
    for tv in tv_mod.TAC_VU.values():
        for vt in tv.dau_vao:
            assert vt in co_that, (
                f"tac vu {tv.ma!r}: vai tro {vt!r} khong model nao khai "
                "— go sai ten?")


@pytest.mark.parametrize("tv", list(tv_mod.TAC_VU.values()), ids=lambda t: t.ma)
def test_moi_tac_vu_khop_it_nhat_MOT_model(tv, so):
    assert so.model_cho(tv.dau_vao), f"tac vu {tv.ma!r} khong khop model nao"


def test_doi_chung_bo_loc_KHONG_phai_luon_luon_khop(so):
    """⛔ Đối chứng cho phép kiểm trên. Nếu `model_cho` trả mọi model bất kể hỏi
    gì thì mọi phép kiểm ở đây xanh vĩnh viễn mà không canh gì."""
    assert so.model_cho(("image.vai_tro_bia_ra",)) == []


# ══════════════════════════════════════════════════════════════════════════
#  3. Cua truoc khop cua sau
# ══════════════════════════════════════════════════════════════════════════

def test_tac_vu_CHUA_MO_thi_tu_choi_chu_khong_chay():
    """Bài học đã trả giá: ô chọn tệp mời MP4 mà đường job từ chối, nên người
    dùng bị **giữ credit → job hỏng → hoàn credit**."""
    tv = tv_mod.TAC_VU["nhieu_anh_tham_chieu"]
    with pytest.raises(tv_mod.LoiTacVu, match="chua mo"):
        tv_mod.kiem_dinh_kem(tv, 2)


def test_dinh_kem_qua_so_luong_thi_tu_choi():
    tv = tv_mod.TAC_VU["anh_thanh_video"]
    with pytest.raises(tv_mod.LoiTacVu, match="toi da"):
        tv_mod.kiem_dinh_kem(tv, 2)


def test_tac_vu_can_anh_ma_khong_dinh_kem_thi_tu_choi():
    tv = tv_mod.TAC_VU["anh_thanh_video"]
    with pytest.raises(tv_mod.LoiTacVu):
        tv_mod.kiem_dinh_kem(tv, 0)


def test_chu_thanh_video_KHONG_doi_dinh_kem():
    tv_mod.kiem_dinh_kem(tv_mod.TAC_VU["chu_thanh_video"], 0)


# ══════════════════════════════════════════════════════════════════════════
#  4. Thu tu LA dia chi
# ══════════════════════════════════════════════════════════════════════════

def test_hai_vai_tro_thi_tep_DAU_la_boi_canh_phan_con_lai_la_nhan_vat():
    """🔑 Đúng cách WanGP đọc `image_refs` khi cờ chứa `K`
    (`wan_handler.py:825-832`): ảnh #1 giữ nền, #2..N bị **cắt nền tự động**.

    Đảo thứ tự là đổi nghĩa — không phải một chi tiết trình bày.
    """
    tv = tv_mod.TAC_VU["boi_canh_va_nhan_vat"]
    ra = tv_mod.media_cho(tv, ["/pod/cho.png", "/pod/nguoi.png", "/pod/den.png"])
    assert ra["image.background"] == "/pod/cho.png"
    assert ra["image.reference"] == ["/pod/nguoi.png", "/pod/den.png"]


def test_mot_vai_tro_mot_tep_thi_KHONG_boc_thanh_danh_sach():
    """`image_start` nhận **một** đường dẫn, không phải một danh sách một phần
    tử — WanGP đọc hai kiểu ấy khác nhau."""
    tv = tv_mod.TAC_VU["anh_thanh_video"]
    assert tv_mod.media_cho(tv, ["/pod/a.png"]) == {"image.start": "/pod/a.png"}


# ══════════════════════════════════════════════════════════════════════════
#  5. Noi voi so dang ky: mot luot tron ven, KHONG can pod
# ══════════════════════════════════════════════════════════════════════════

def test_mot_luot_TRON_VEN_tu_tac_vu_toi_settings(may):
    """Nếu chuỗi này không chạy hết trong test thì HM-5/HM-6 vẫn phải chờ pod,
    và cả kế hoạch "giả lập trước" mất ý nghĩa."""
    tv = tv_mod.TAC_VU["anh_thanh_video"]
    tv_mod.kiem_dinh_kem(tv, 1)
    media = tv_mod.media_cho(tv, ["/pod/vao.png"])
    ra = sd.settings(may, tv.model, media=media, prompt="mot dong song",
                     video_length="5s")
    assert ra["model_type"] == "i2v_2_2"
    assert ra["image_start"] == "/pod/vao.png"
    assert ra["prompt"] == "mot dong song"


def test_so_tac_vu_dang_mo_KHOP_voi_so_ban_ghi_mac_dinh_da_co():
    """⭐ Bất biến nối hai thứ dễ trôi khỏi nhau: một tác vụ `mo=True` mà thiếu
    `mac_dinh__<model>.json` thì nó hiện trên giao diện rồi hỏng lúc chạy."""
    import pathlib

    goc = (pathlib.Path(tv_mod.__file__).parent / "ban_ghi")
    for tv in tv_mod.dang_mo():
        tep = goc / f"mac_dinh__{tv.model}.json"
        assert tep.is_file(), (
            f"tac vu {tv.ma!r} dang MO nhung thieu {tep.name} — no se hien tren "
            "giao dien roi hong luc chay")


# ══════════════════════════════════════════════════════════════════════════
#  6. Menh de CHUYEN NHA tu `test_729_lttvideo_chon_model.py` (da go)
#
#  🔴 Duong di THAT cua mot nguoi dung tai MP4 len khi cua truoc va cua sau
#     lech nhau:
#         chon MP4 -> nen tang GIU CREDIT -> job chay -> job nem loi
#                  -> credit duoc hoan
#     Tien tra lai, nhung thoi gian va niem tin thi khong. Va cai sai KHONG nam
#     o job — job tu choi la DUNG. Cai sai la CUA TRUOC moi nguoi ta vao mot
#     canh cua khoa.
# ══════════════════════════════════════════════════════════════════════════

def test_o_chon_tep_KHONG_moi_kieu_tep_ma_duong_job_TU_CHOI():
    """Mọi MIME ô chọn tệp mời phải có một **tác vụ đang mở** nhận được nó."""
    import inspect
    import pathlib
    import re

    from apps.lttvideo import routes

    goc = pathlib.Path(inspect.getsourcefile(routes)).parent / "templates"
    html = chr(10).join(f.read_text(encoding="utf-8")
                        for f in sorted(goc.glob("*.html")))
    m = re.search(r'accept="([^"]+)"', html)
    assert m, "khong tim thay o chon tep nao"
    moi = [x.strip() for x in m.group(1).split(",") if x.strip()]

    vai_tro_dang_mo = {v for t in tv_mod.dang_mo() for v in t.dau_vao}
    for mime in moi:
        loai = mime.split("/", 1)[0]          # "image" | "video" | "audio"
        assert any(v.startswith(f"{loai}.") for v in vai_tro_dang_mo), (
            f"o chon tep moi {mime!r} nhung khong tac vu DANG MO nao nhan "
            f"loai {loai!r} — nguoi dung se mat credit va hai muoi phut")


def test_tu_choi_video_noi_RO_LY_DO_chu_khong_noi_chung_chung():
    """Một lời từ chối không nói vì sao là một lời từ chối người dùng sẽ thử
    lại — và thử lại đúng cách vừa hỏng."""
    import inspect

    from apps.lttvideo import routes

    ma = inspect.getsource(routes._luu_media)
    assert "chưa mở" in ma or "chua mo" in ma


def test_MA_NGUON_cua_so_dang_ky_khong_nhac_ten_model_nao():
    """Mệnh đề chuyển nhà: tên model chỉ được xuất hiện ở **danh mục tác vụ**
    (nơi nó là một quyết định có căn cứ), không ở tầng sinh settings."""
    import ast
    import inspect

    from apps.lttvideo import so_dang_ky as sd_mod

    cay = ast.parse(inspect.getsource(sd_mod))
    for n in ast.walk(cay):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            assert not n.value.startswith(("t2v_", "i2v_", "vace_")), n.value


def test_gui_ANH_toi_model_khong_nhan_anh_thi_BI_CHAN(so):
    """⛔ WanGP **bỏ qua** media mà model không khai — không lỗi, không cảnh
    báo. Ta chỉ biết khi xem video ra và không thấy ảnh của mình trong đó.

    Hàng rào nay nằm ở `test_model_da_chon_KHAI_DU_vai_tro`, nhưng phép kiểm
    này chốt thêm chiều **âm**: model chỉ-chữ phải thật sự không khai khe ảnh,
    nếu không thì cả hàng rào ấy đo một thứ không tồn tại.
    """
    khai_t2v = sd._vai_tro(so.sieu("t2v_2_2"))
    assert not any(v.startswith("image.") for v in khai_t2v), (
        "t2v_2_2 nay CO khai khe anh — hang rao chon model can xem lai")
    khai_i2v = sd._vai_tro(so.sieu("i2v_2_2"))
    assert "image.start" in khai_i2v
