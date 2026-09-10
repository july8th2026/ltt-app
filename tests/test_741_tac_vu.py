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

import json as _json

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


def _html_da_dung() -> str:
    """HTML **đã dựng** — thứ người dùng thật sự thấy, không phải mã nguồn."""
    from tests.test_734_lttvideo_gui import _dung  # noqa: PLC0415

    return _dung(False)


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
    """Mọi MIME ô chọn tệp **thật sự hiện ra** phải có một tác vụ đang mở nhận
    được nó.

    🔴 Viết lại 08/09. Bản trước đọc **văn bản** template, nên nó không thấy
       hàng rào `{% if %}` bao quanh mục đính kèm — và nó đỏ đúng lúc mã đã
       đúng. Một phép kiểm về *thứ người dùng thấy* phải đo **HTML đã dựng**,
       không đo mã nguồn sinh ra nó.

    ⭐ Và đây là mệnh đề **tương đương**, không phải "không được có ô chọn tệp":
       ô chọn tệp hiện ra ⟺ có tác vụ đang mở nhận tệp. Đúng ở cả hai thế giới,
       nên nó tự đúng lại vào ngày `i2v_2_2` được tải về.
    """
    import re as _re

    html = _html_da_dung()
    m = _re.search(r'accept="([^"]+)"', html)
    nhan_tep = {v.split(".", 1)[0] for t in tv_mod.dang_mo() for v in t.dau_vao}

    if not nhan_tep:
        assert m is None, (
            f"o chon tep HIEN RA ({m.group(1) if m else None}) nhung khong tac "
            "vu dang mo nao nhan tep — nguoi dung se mat credit va hai muoi phut")
        return

    assert m, "co tac vu nhan tep nhung khong o chon tep nao hien ra"
    for mime in m.group(1).split(","):
        loai = mime.strip().split("/", 1)[0]
        assert loai in nhan_tep, (
            f"o chon tep moi {mime!r} nhung khong tac vu DANG MO nao nhan "
            f"loai {loai!r}")

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


# ══════════════════════════════════════════════════════════════════════════
#  7. CUA THU BA — ban khai co, trong so KHONG
# ══════════════════════════════════════════════════════════════════════════

def test_tac_vu_dang_mo_deu_CO_TRONG_SO_tren_dia():
    """🔴 Cửa thứ ba, tìm ra 08/09 khi máy ghi lấy được `kha_dung` thật.

    Đo trên máy: **1/225 model** có trọng số (`t2v_2_2`), 4 phần, **220 thiếu**
    — trong đó có `i2v_2_2`, model của một tác vụ khi ấy đang `mo=True`.

    ⭐ Hai cửa ta canh trước đó **đều xanh** cho tác vụ ấy:
         1. ô chọn tệp mời gì   ↔  tác vụ nhận gì
         2. tác vụ cần vai trò  ↔  model khai vai trò
       Nhưng có **bản khai** không có nghĩa là có **trọng số**. Người dùng bấm,
       nền tảng giữ credit, rồi máy dựng đi tải ~30 GB giữa lượt — hoặc hỏng.

    ⛔ Bài học rộng hơn một lỗi: một bất biến "cửa trước khớp cửa sau" chỉ đúng
       khi ta **đếm đủ số cửa**. Hai cửa đầu là hai cửa ta *nghĩ ra*; cửa thứ ba
       chỉ lộ ra khi hỏi máy thật.
    """
    for tv in tv_mod.dang_mo():
        assert tv_mod.co_trong_so(tv.model), (
            f"tac vu {tv.ma!r} dang mo nhung model {tv.model!r} CHUA co trong so")


def test_thieu_ban_ghi_kha_dung_thi_COI_NHU_KHONG_CO_chu_khong_doan_la_co(
        tmp_path, monkeypatch):
    """⛔ Đoán "có" khi thiếu dữ liệu là mở một cánh cửa khoá. Đoán "không" thì
    tệ nhất là ẩn mất một tác vụ chạy được — và cái đó **nhìn thấy được**.

    🔴 Bản đầu của phép kiểm này **xoá rồi khôi phục `kha_dung.json` trong cây
       kho**. Đúng cái bẫy đã ghi ở HM-1 và vừa dẫm lại: một phép kiểm ghi vào
       cây tự phá lượt gate chứa nó (`cay_da_doi_giua_chung`) — và nếu nó hỏng
       giữa chừng thì bản ghi thật **mất hẳn**.

    ⇒ Trỏ thư mục bản ghi sang `tmp_path`, không đụng cây.
    """
    from apps.lttvideo.cong import may_gia_lap

    monkeypatch.setattr(may_gia_lap, "GOC_BAN_GHI", tmp_path)
    assert tv_mod.co_trong_so("t2v_2_2") is False, "thieu ban ghi ma van doan CO"

    (tmp_path / "kha_dung.json").write_bytes(_json.dumps(
        {"nguon": "ghi_tu_may", "sha_wangp": "x",
         "du_lieu": {"t2v_2_2": {"available": True}}}).encode("utf-8"))
    assert tv_mod.co_trong_so("t2v_2_2") is True

def test_khong_con_ban_ghi_nao_la_KHUON():
    """HM-7/B4: sau khi ghi từ máy thật, không bản ghi nào được còn `khuon`.

    Một khuôn sót lại trông **y hệt** dữ liệu thật, chỉ khác là nó sai."""
    import pathlib

    goc = pathlib.Path(tv_mod.__file__).parent / "ban_ghi"
    con = {t.name: _json.loads(t.read_text(encoding="utf-8"))["nguon"]
           for t in goc.glob("*.json")}
    khuon = [k for k, v in con.items() if v != "ghi_tu_may"]
    assert not khuon, f"con ban ghi la khuon: {khuon}"
    assert len(con) >= 4, f"qua it ban ghi: {con}"
