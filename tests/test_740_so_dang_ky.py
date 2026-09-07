"""HM-3 — sổ đăng ký **sinh ra**, không gõ tay.

## Mệnh đề trung tâm

Chi phí mở thêm một model phải là **hằng số**, không phải tuyến tính. `ho_so.py`
cũ giữ một bảng gõ tay cho hai model, nên mỗi model mới tốn một hồ sơ rút tay —
và đó là lý do đo được của độ phủ **2/225 = 0,9%**, chứ không phải vì WanGP khó.

## Hai phép kiểm ở đây làm việc khác nhau

- `test_khong_co_TEN_MODEL_nao_go_tay` và `test_khong_gan_co_chu_cai_bang_tay`
  canh **cách viết** — chúng đọc AST, và chúng đỏ ngay khi ai đó bắt đầu chép
  giá trị của WanGP vào mã ta.
- Phần còn lại canh **tính chất**: sổ đọc được 225 model thật, chỉ mục ngược
  khớp với `media_inputs` WanGP khai, và `settings()` không tự thêm cờ nào.

⭐ Cả hai đều cần. Phép kiểm cách viết bắt được ý định sai sớm; phép kiểm tính
  chất bắt được cái sai mà cách viết vẫn đúng.
"""
from __future__ import annotations

import ast
import inspect
import re

import pytest

from apps.lttvideo import so_dang_ky
from apps.lttvideo.cong.giao_uoc import LoiMay
from apps.lttvideo.cong.may_gia_lap import MayGiaLap


@pytest.fixture(scope="module")
def so():
    return so_dang_ky.nap(MayGiaLap())


# ══════════════════════════════════════════════════════════════════════════
#  1. Cach viet — doc AST, khong khop chuoi
# ══════════════════════════════════════════════════════════════════════════

_TEN_MODEL = re.compile(r"^(t2v|i2v|ti2v|vace|ltx2|hunyuan|flux|qwen|k5)_")


def test_khong_co_TEN_MODEL_nao_go_tay():
    """⛔ Một tên model hằng số trong mã là một giá trị **sẽ trôi** khi WanGP
    đổi bản — và nó trôi im lặng: model biến khỏi bản khai thì bảng vẫn trỏ tới
    nó, và lỗi hiện ra ở tận lúc chạy job.

    📌 Đọc AST chứ không `grep`: chú thích trong tệp **có** nhắc `t2v_2_2` để
       giải thích, và một bộ dò quét văn bản sẽ báo động trên chính đoạn giải
       thích nó — chuyện đã xảy ra bốn lần ở kho này.
    """
    cay = ast.parse(inspect.getsource(so_dang_ky))
    pham = [n.value for n in ast.walk(cay)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and _TEN_MODEL.match(n.value)]
    assert not pham, (
        f"ten model go tay trong so dang ky: {pham} — phai den tu "
        "`may.liet_ke_model()`")


def test_khong_gan_co_chu_cai_bang_tay():
    """⛔ `docs_API.md:330`: WanGP **tự điền** `S`/`E`/`V`/`I` khi chuẩn hoá tác
    vụ. Đặt tay ở phía ta là dựng một tầng dịch thứ hai — và tầng ấy chính là
    chi phí mỗi-model đã giữ độ phủ ở 0,9%.
    """
    cay = ast.parse(inspect.getsource(so_dang_ky))
    for n in ast.walk(cay):
        if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant):
            khoa = n.slice.value
            assert khoa not in ("image_prompt_type", "video_prompt_type"), (
                f"gan co {khoa!r} bang tay — WanGP tu dien")


# ══════════════════════════════════════════════════════════════════════════
#  2. Tinh chat — do tren ban ghi THAT
# ══════════════════════════════════════════════════════════════════════════

def test_doc_duoc_ca_225_model_that(so):
    """Đối chứng cho chính bản ghi: nếu nó teo lại thì mọi phép kiểm dưới đây
    vẫn xanh mà không canh gì. Con số chốt là **tập hợp có thật**, không phải
    một mốc ta tự đặt."""
    assert len(so) == 225, f"ban ghi co {len(so)} model, mong doi 225"


def test_chi_muc_nguoc_KHOP_voi_media_inputs_WanGP_khai(so):
    """🔑 Tính chất, không phải cách viết: với **mọi** model và **mọi** vai trò,
    model có mặt trong chỉ mục ⟺ nó khai vai trò ấy."""
    for mt, sieu in so.theo_model.items():
        khai = so_dang_ky._vai_tro(sieu)
        for vt in so.vai_tro_co_that():
            trong_chi_muc = mt in so.theo_vai_tro.get(vt, frozenset())
            assert trong_chi_muc == (vt in khai), (
                f"{mt}: chi muc noi {trong_chi_muc} nhung model khai "
                f"{vt in khai} cho vai tro {vt!r}")


def test_vai_tro_doc_DONG_chu_khong_tu_mot_danh_sach_co_dinh(so):
    """Một model khai thêm vai trò mới (WanGP lên bản) thì nó phải tự xuất hiện.

    ⭐ Đo bằng cách **bịa một vai trò chưa từng có** rồi kiểm nó lọt vào: nếu mã
      lọc theo một danh sách cố định thì vai trò ấy bị bỏ qua âm thầm."""
    gia = {"media_inputs": {"image": {"vai_tro_chua_tung_co": True}}}
    assert "image.vai_tro_chua_tung_co" in so_dang_ky._vai_tro(gia)


def test_bon_vai_tro_cua_VACE_deu_co_that(so):
    """Bốn vai trò mà bảng chấm điểm dựa vào phải **thật sự** có model khai —
    nếu không thì cả bảng ấy nói về một thứ không tồn tại."""
    for vt in ("image.reference", "image.background", "image.injected_frames",
               "video.control"):
        assert so.theo_vai_tro.get(vt), f"khong model nao khai {vt!r}"


def test_model_cho_KHONG_ANH_rong_hon_model_cho_CO_ANH(so):
    """Thêm một yêu cầu đầu vào chỉ có thể **thu hẹp** tập model. Nếu không thì
    chỉ mục đang hợp thay vì giao, và giao diện sẽ mời model không nhận nổi thứ
    người dùng đính kèm."""
    chi_chu = so.model_cho(())
    co_anh = so.model_cho(("image.reference",))
    assert set(co_anh) <= set(chi_chu)
    assert len(co_anh) < len(chi_chu)


def test_dat_hai_vai_tro_thi_phai_GIAO_chu_khong_HOP(so):
    a = set(so.model_cho(("image.background",)))
    b = set(so.model_cho(("video.control",)))
    ca_hai = set(so.model_cho(("image.background", "video.control")))
    assert ca_hai == a & b


# ══════════════════════════════════════════════════════════════════════════
#  3. settings() — lay tu WanGP, khong tu dung
# ══════════════════════════════════════════════════════════════════════════

def test_settings_lay_tu_get_default_settings_chu_khong_tu_dung():
    may = MayGiaLap()
    goc = may.mac_dinh("t2v_2_2")
    ra = so_dang_ky.settings(may, "t2v_2_2", prompt="mot dong song")
    for k, v in goc.items():
        if k in ("prompt", "model_type"):
            continue
        assert ra[k] == v, f"settings tu doi {k!r}: {v!r} -> {ra[k]!r}"


def test_settings_KHONG_tu_them_co_nao():
    """⭐ Đo ĐẦU RA, không đo mã. Nếu `mac_dinh` đã có sẵn `image_prompt_type`
    (WanGP tự đặt) thì giá trị ấy phải **giữ nguyên** — ta không chồng lên."""
    may = MayGiaLap()
    goc = may.mac_dinh("i2v_2_2")
    ra = so_dang_ky.settings(may, "i2v_2_2",
                             media={"image.start": "/pod/a.png"})
    assert ra.get("image_prompt_type") == goc.get("image_prompt_type")
    assert ra["image_start"] == "/pod/a.png"


def test_image_refs_la_DANH_SACH_va_giu_THU_TU():
    """Thứ tự **là** địa chỉ: ảnh #1 là bối cảnh khi model khai
    `image.background`. Gộp thành một chuỗi hay đảo thứ tự là đổi nghĩa."""
    may = MayGiaLap()
    ra = so_dang_ky.settings(
        may, "t2v_2_2", media={"image.reference": ["/pod/1.png", "/pod/2.png"]})
    assert ra["image_refs"] == ["/pod/1.png", "/pod/2.png"]


def test_vai_tro_khong_co_khe_thi_NEM_chu_khong_bo_qua():
    """⛔ Bỏ qua âm thầm nghĩa là người dùng đính một tệp, trả credit, và tệp ấy
    **không bao giờ tới engine** — job chạy như thể không có đính kèm."""
    may = MayGiaLap()
    with pytest.raises(LoiMay, match="chua co khe"):
        so_dang_ky.settings(may, "t2v_2_2", media={"image.khong_co_that": "/x"})


def test_thieu_ban_ghi_mac_dinh_thi_NEM():
    """225 model có sơ đồ, nhưng chỉ 2 model có `get_default_settings` đã ghi.
    Model thứ ba phải **kêu** chứ không chạy với settings rỗng."""
    may = MayGiaLap()
    with pytest.raises(LoiMay, match="chua co ban ghi"):
        so_dang_ky.settings(may, "vace_14B", prompt="x")


# ══════════════════════════════════════════════════════════════════════════
#  4. Hai tep cu DA BI GO
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("ten", ["ho_so", "chon_model"])
def test_mo_dun_cu_DA_BI_GO(ten):
    """Gỡ import mà để tệp lại là để một tầng chết nằm chờ ai đó import lại."""
    import pathlib

    kho = pathlib.Path(__file__).resolve().parents[1]
    assert not (kho / "apps" / "lttvideo" / f"{ten}.py").exists()


def test_KHONG_AI_con_import_hai_mo_dun_cu():
    """Đo bằng AST trên toàn cây — `grep` khớp cả chú thích nhắc tới chúng."""
    import pathlib

    kho = pathlib.Path(__file__).resolve().parents[1]
    pham = []
    for tep in list((kho / "apps").rglob("*.py")) + \
               list((kho / "tests").rglob("*.py")) + \
               list((kho / "tools").rglob("*.py")):
        if tep.name == pathlib.Path(__file__).name:
            continue
        try:
            cay = ast.parse(tep.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for n in ast.walk(cay):
            if isinstance(n, ast.ImportFrom):
                mo = n.module or ""
                if mo.endswith(("lttvideo.ho_so", "lttvideo.chon_model")):
                    pham.append(f"{tep.relative_to(kho)}:{n.lineno}")
                if mo.endswith("apps.lttvideo") or mo == ".":
                    pham += [f"{tep.relative_to(kho)}:{n.lineno}"
                             for a in n.names if a.name in ("ho_so", "chon_model")]
    assert not pham, f"con import mo dun da go: {pham}"


# ══════════════════════════════════════════════════════════════════════════
#  5. Menh de CHUYEN NHA tu `test_720_lttvideo_ho_so.py` (da go)
#
#  ⛔ Khong menh de nao bi xoa theo `ho_so.py`. Chung canh nhung thu VAN DUNG
#     sau khi so dang ky duoc sinh ra thay vi go tay — chi khac noi chua.
# ══════════════════════════════════════════════════════════════════════════

def test_moi_ban_ghi_deu_NEO_vao_mot_SHA_wangp():
    """🔑 Bất biến trung tâm, giữ nguyên từ `ho_so.py`.

    Tham số chỉ có nghĩa với **đúng phiên bản engine** sinh ra chúng. Một bản
    ghi không neo SHA là một bản ghi nói về "WanGP nói chung" — và không có
    "WanGP nói chung".
    """
    import json
    import pathlib

    from tools.wangp.ghi_ban_ghi import WANGP_SHA

    goc = pathlib.Path(so_dang_ky.__file__).parent / "ban_ghi"
    tep = list(goc.glob("*.json"))
    assert tep, "khong co ban ghi nao"
    for t in tep:
        d = json.loads(t.read_text(encoding="utf-8"))
        assert d.get("sha_wangp") == WANGP_SHA, (
            f"{t.name} neo SHA {d.get('sha_wangp')!r}, lech voi {WANGP_SHA!r}")


def test_khoa_NGOAI_danh_sach_cho_phep_bi_TU_CHOI_chu_khong_bi_BO_QUA():
    """⛔ Mệnh đề chuyển nhà từ `test_720`, và nó là một hàng rào **về tiền**.

    Ranh giới thật: "người dùng chọn độ phân giải" khác hẳn "người dùng đặt
    `num_inference_steps=200`" — cái sau đi thẳng vào hoá đơn GPU.

    Và phải **ném**, không được bỏ qua: một tham số sai bị bỏ qua âm thầm vẫn
    đi tới GPU, chỉ là đi kèm một kết quả không ai giải thích được.
    """
    may = MayGiaLap()
    with pytest.raises(so_dang_ky.KhoaKhongDuocPhep, match="num_inference_steps"):
        so_dang_ky.settings(may, "t2v_2_2", prompt="x", num_inference_steps=200)


def test_sau_khoa_nguoi_dung_doi_duoc_deu_di_TOI_settings():
    """Đối chứng cho phép kiểm trên: hàng rào không được chặn nhầm thứ hợp lệ.
    Một ô nhập nhận giá trị rồi không gửi đi là kiểu thất bại tệ nhất — người
    dùng tin là mình đã điều khiển được."""
    may = MayGiaLap()
    ra = so_dang_ky.settings(
        may, "t2v_2_2", prompt="p", negative_prompt="n", seed=7,
        resolution="832x480", video_length="5s", prompt_enhancer="T")
    assert ra["prompt"] == "p" and ra["negative_prompt"] == "n"
    assert ra["seed"] == 7 and ra["video_length"] == "5s"
    assert ra["resolution"] == "832x480" and ra["prompt_enhancer"] == "T"


def test_KHONG_bat_wangp_TU_CHON_model():
    """Mệnh đề chuyển nhà: `model_type` luôn được nói rõ. Để WanGP tự chọn là
    để một quyết định về tiền nằm ngoài tầm nhìn của ta."""
    may = MayGiaLap()
    ra = so_dang_ky.settings(may, "t2v_2_2", prompt="x")
    assert ra["model_type"] == "t2v_2_2"


def test_doc_duoc_CA_HAI_khuon_metadata():
    """🔴 Lỗi thật, tìm ra khi bản ghi từ máy sống thay khuôn (HM-7).

    WanGP có **hai** hàm liệt kê, và chúng trả **hai khuôn khác nhau**:

        list_model_defs()      -> {model_type, name, metadata: {media_inputs…}}
        list_model_metadata()  -> {model_type, name, media_inputs, …}   PHẲNG

    Ví dụ ở `docs_API.md:262` là của hàm **thứ nhất**; tôi áp khuôn ấy cho hàm
    thứ hai. Hậu quả: mọi `metadata` đều rỗng, chỉ mục ngược rỗng theo, và **225
    model mà không model nào khai một vai trò nào**.

    ⭐ Vì sao nó lọt qua tất cả phép kiểm trước đó: bản ghi cũ do **tôi** dựng
      từ ảnh chụp, nên nó mang đúng khuôn tôi tưởng. Phép kiểm và dữ liệu cùng
      sai một kiểu thì chúng khớp nhau hoàn hảo. Chỉ dữ liệu **từ máy thật** mới
      phá được sự khớp giả ấy — đó chính là việc HM-7 sinh ra để làm.
    """
    class _MayHaiKhuon:
        def __init__(self, ds): self._ds = ds
        def liet_ke_model(self, **_): return self._ds

    KHE = {"image": {"start": True}}
    phang = _MayHaiKhuon([{"model_type": "a", "media_inputs": KHE,
                           "main_output": ["video"]}])
    long = _MayHaiKhuon([{"model_type": "a", "metadata": {
        "media_inputs": KHE, "main_output": ["video"]}}])

    for ten, may in (("phang", phang), ("long", long)):
        so = so_dang_ky.nap(may)
        assert so.model_cho(("image.start",)) == ["a"], f"khuon {ten} doc sai"


def test_ban_ghi_THAT_va_anh_chup_CU_cho_cung_mot_ket_qua():
    """⭐ Đối chứng chéo hai nguồn độc lập.

    Ảnh chụp cũ (chuyển đổi 07/09) và bản ghi từ máy sống (08/09) là hai lần
    đo cách nhau một ngày, qua hai đường khác nhau. Chúng phải cho **cùng** số
    model khai mỗi vai trò — nếu lệch thì một trong hai đã trôi, và ta biết
    ngay thay vì biết lúc một người dùng bấm nút.
    """
    so = so_dang_ky.nap(MayGiaLap())
    assert len(so) == 225
    assert len(so.model_cho(("image.start",))) == 83
    assert len(so.model_cho(("image.reference",))) == 70
    assert len(so.model_cho(("image.background",))) == 51
    assert len(so.model_cho(("video.control",))) == 82
    assert len(so.model_cho(("video.continue",))) == 113
