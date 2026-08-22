"""
test_259 — chuẩn hoá hai bộ ảnh trước khi dựng lô so mù. (H37/G6b)

⚠️ Đánh số 259 chứ không 256: **ba phiên đang chạy song song trên repo này**
và đã trùng số từ 250 tới 258. Trước khi thêm tệp test, `ls tests/test_2*`
để xem số nào còn trống — số trùng không làm pytest hỏng, nhưng nó phá cái
mà quy ước đánh số sinh ra để làm: một chỉ mục tra được.

Không mạng, không GPU.

Bước này tồn tại vì **hai** lý do, và test ở đây chốt cả hai — cái thứ hai nặng hơn:
công bằng (ảnh to hơn trông nét hơn bất kể model) và **tính mù** (đuôi tệp khác nhau
là đủ để người chấm đoán ra nguồn).
"""
from __future__ import annotations

import json

import pytest

from tools import chuan_hoa_anh as C


def _ghi(thu_muc, ten: str, rong: int, cao: int, dinh_dang: str = "PNG"):
    from PIL import Image
    thu_muc.mkdir(parents=True, exist_ok=True)
    duoi = {"PNG": ".png", "JPEG": ".jpg"}[dinh_dang]
    p = thu_muc / (ten + duoi)
    Image.new("RGB", (rong, cao), (120, 60, 30)).save(p, format=dinh_dang)
    return p


def _kich_co(p):
    from PIL import Image
    with Image.open(p) as im:
        return im.width, im.height


# ═══════════ ① công bằng: hạ về cùng cạnh dài ═══════════════════════════════
def test_ha_ca_hai_ve_CUNG_canh_dai(tmp_path):
    """Cảnh thật 22/08: Gemini 1376×768, phía ta 2560×1440."""
    a, b = tmp_path / "gemini", tmp_path / "ta"
    for i in range(2):
        _ghi(a, f"p{i}", 1376, 768, "JPEG")
        _ghi(b, f"p{i}", 2560, 1440, "PNG")
    bk = C.chuan_hoa([a, b], tmp_path / "ra")
    # 1365 chu khong phai 1376: anh Gemini rong hon ti le dich, nen sau khi cat giua
    # ve 16:9 no chi con 1365 canh dai. Lay 1376 la phai PHONG TO no len.
    assert bk["canh_dai_chung"] == 1365
    for ben in ("gemini", "ta"):
        for m in bk["sau"][ben]:
            assert (m["rong"], m["cao"]) == (1365, 768)


def test_MOI_anh_ra_CUNG_MOT_KHUNG_khong_lech_du_mot_pixel(tmp_path):
    """⛔ Dấu vết hệ thống thứ hai, tinh vi hơn đuôi tệp. Gemini khai "16:9" nhưng
    trả 1376×768 = **1,7917**; phía ta 2560×1440 = **1,7778**. Khớp riêng cạnh dài
    cho ra 1376×768 và 1376×**774** — lệch 6 pixel chiều cao, **y hệt trên mọi
    cặp**. Người chấm nhận ra sau vài cặp là biết bên nào là bên nào."""
    a, b = tmp_path / "gemini", tmp_path / "ta"
    for i in range(3):
        _ghi(a, f"p{i}", 1376, 768, "JPEG")
        _ghi(b, f"p{i}", 2560, 1440, "PNG")
    C.chuan_hoa([a, b], tmp_path / "ra")
    khung = {_kich_co(p) for p in (tmp_path / "ra").rglob("*.png")}
    assert len(khung) == 1, f"con nhieu hon mot khung: {khung}"


def test_khung_chung_lay_ti_le_HEP_NHAT_de_khong_phai_chen_vien():
    """Chèn viền là thay một dấu vết bằng một dấu vết khác."""
    dai, ngan = C.khung_chung([(1376, 768), (2560, 1440)])
    assert abs(dai / ngan - 2560 / 1440) < 0.002, (dai, ngan)


def test_KHONG_ben_nao_bi_PHONG_TO_du_mot_pixel(tmp_path):
    """⛔ Bẫy tôi tự sa vào rồi mới thấy: cạnh dài chung đo TRƯỚC khi cắt cho ra
    1376×774, nên ảnh Gemini bị cắt còn 1365 rồi **phóng lên** 1376. Phóng 0,8 % làm
    ảnh mềm đi, và nó chỉ xảy ra với MỘT bên ⇒ thiên lệch có hệ thống.

    Cạnh dài chung phải đo **sau** khi cắt về tỉ lệ đích."""
    dai, ngan = C.khung_chung([(1376, 768), (2560, 1440)])
    # Gemini sau khi cat ve ti le 16:9 chi con 1365 canh dai.
    assert dai <= 1365, f"khung dich {dai} lon hon canh dai that sau khi cat"

    a, b = tmp_path / "gemini", tmp_path / "ta"
    _ghi(a, "p1", 1376, 768, "JPEG"); _ghi(b, "p1", 2560, 1440, "PNG")
    bk = C.chuan_hoa([a, b], tmp_path / "ra")
    for ben, goc in (("gemini", (1376, 768)), ("ta", (2560, 1440))):
        m = bk["sau"][ben][0]
        assert m["rong"] <= goc[0] and m["cao"] <= goc[1], (ben, m, goc)


def test_anh_DOC_khong_bi_xoay(tmp_path):
    """Khung đích phải theo hướng của từng ảnh. Xoay ảnh của ai đó là đổi hẳn thứ
    đang được chấm."""
    a, b = tmp_path / "a", tmp_path / "b"
    _ghi(a, "p1", 768, 1376); _ghi(b, "p1", 1440, 2560)
    C.chuan_hoa([a, b], tmp_path / "ra")
    for p in (tmp_path / "ra").rglob("*.png"):
        w, h = _kich_co(p)
        assert h > w, f"anh doc bi xoay thanh ngang: {p.name} {w}x{h}"


def test_cat_GIUA_chu_khong_cat_mep(tmp_path):
    """Chủ thể gần như luôn ở giữa; cắt lệch là bỏ đi đúng thứ đang được chấm."""
    from PIL import Image
    im = Image.new("RGB", (200, 100), (0, 0, 0))
    for x in range(90, 110):
        for y in range(40, 60):
            im.putpixel((x, y), (255, 255, 255))     # dom trang o CHINH GIUA
    ra = C._cat_giua(im, 1.0)                        # 200x100 -> 100x100
    assert (ra.width, ra.height) == (100, 100)
    assert ra.getpixel((50, 50)) == (255, 255, 255), "dom giua da bi cat mat"


def test_KHONG_BAO_GIO_phong_to_anh_nho(tmp_path):
    """⛔ Phóng ảnh nhỏ lên cho bằng ảnh to là **bịa ra chi tiết chưa từng có**, và
    người chấm sẽ chấm cái mờ do nội suy chứ không chấm model."""
    a, b = tmp_path / "nho", tmp_path / "to"
    _ghi(a, "p1", 800, 450); _ghi(b, "p1", 2560, 1440)
    bk = C.chuan_hoa([a, b], tmp_path / "ra")
    assert bk["canh_dai_chung"] == 800
    assert all(m["rong"] <= 800 for ds in bk["sau"].values() for m in ds)


def test_canh_dai_chung_lay_MIN_qua_ca_hai_ben():
    assert C.canh_dai_chung([(1376, 768), (2560, 1440)]) == 1376
    assert C.canh_dai_chung([(768, 1376), (1440, 2560)]) == 1376   # anh doc
    with pytest.raises(C.LoiChuanHoa):
        C.canh_dai_chung([])


def test_dua_ve_cung_khung_bang_cach_cat_giua(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    _ghi(a, "p1", 1000, 1000); _ghi(b, "p1", 2000, 1000)
    C.chuan_hoa([a, b], tmp_path / "ra")
    # Ti le hep nhat la 1:1 (anh vuong), nen anh 2:1 bi cat giua ve vuong.
    assert _kich_co(tmp_path / "ra" / "a" / "p1.png") == (1000, 1000)
    assert _kich_co(tmp_path / "ra" / "b" / "p1.png") == (1000, 1000)


# ═══════════ ② TÍNH MÙ: một đuôi tệp duy nhất ═══════════════════════════════
def test_MOI_anh_ra_deu_la_PNG_du_vao_khac_dinh_dang(tmp_path):
    """⛔ Lý do nặng nhất của cả tệp này. Một bên `.jpg`, một bên `.png` thì người
    chấm nhìn **tên tệp** là biết nguồn — không cần mở ảnh."""
    a, b = tmp_path / "gemini", tmp_path / "ta"
    _ghi(a, "p1", 1376, 768, "JPEG"); _ghi(b, "p1", 2560, 1440, "PNG")
    C.chuan_hoa([a, b], tmp_path / "ra")
    duoi = {p.suffix for p in (tmp_path / "ra").rglob("*")
            if p.is_file() and p.suffix != ".json"}
    assert duoi == {".png"}


def test_ghi_lo_TU_CHOI_lo_co_hai_duoi_khac_nhau(tmp_path):
    """Bánh cóc ở đầu kia: kể cả ai đó quên chạy chuẩn hoá, bộ dựng lô cũng phải
    **từ chối** thay vì lặng lẽ tạo ra một lô trông có vẻ mù."""
    from tools import cham_mu as M

    a = _ghi(tmp_path / "a", "p1", 100, 100, "JPEG")
    b = _ghi(tmp_path / "b", "p1", 100, 100, "PNG")
    caps = M.tao_lo([str(a)], [str(b)], ty_le_bay=0.0)
    with pytest.raises(ValueError) as e:
        M.ghi_lo(caps, tmp_path / "lo", nhan_a="A", nhan_b="B")
    assert "mu" in str(e.value).lower()


def test_ghi_lo_van_chay_khi_hai_ben_CUNG_duoi(tmp_path):
    """Không được chặn nhầm: cùng đuôi thì phải chạy bình thường."""
    from tools import cham_mu as M

    a = _ghi(tmp_path / "a", "p1", 100, 100, "PNG")
    b = _ghi(tmp_path / "b", "p1", 100, 100, "PNG")
    caps = M.tao_lo([str(a)], [str(b)], ty_le_bay=0.0)
    M.ghi_lo(caps, tmp_path / "lo", nhan_a="A", nhan_b="B")
    assert (tmp_path / "lo" / "anh").is_dir()


def test_chuan_hoa_roi_thi_ghi_lo_chay_duoc(tmp_path):
    """Đường đi trọn vẹn: hai bộ lệch cả kích thước lẫn định dạng → chuẩn hoá →
    dựng lô thành công."""
    from tools import cham_mu as M

    a, b = tmp_path / "gemini", tmp_path / "ta"
    for i in range(3):
        _ghi(a, f"p{i}", 1376, 768, "JPEG")
        _ghi(b, f"p{i}", 2560, 1440, "PNG")
    C.chuan_hoa([a, b], tmp_path / "chuan")
    ra_a = sorted(str(p) for p in (tmp_path / "chuan" / "gemini").glob("*.png"))
    ra_b = sorted(str(p) for p in (tmp_path / "chuan" / "ta").glob("*.png"))
    caps = M.tao_lo(ra_a, ra_b, ty_le_bay=0.0)
    M.ghi_lo(caps, tmp_path / "lo", nhan_a="gemini", nhan_b="ta")
    ten = [p.name for p in (tmp_path / "lo" / "anh").iterdir()]
    assert ten and all(n.endswith(".png") for n in ten)
    assert not any("gemini" in n or "ta_" in n for n in ten)


# ═══════════ bản kê phải tự nói ra giới hạn ═════════════════════════════════
def test_ban_ke_GIU_so_do_TRUOC_khi_ha(tmp_path):
    """Khác biệt như-giao (Gemini 1376×768 JPEG vs ta 2560×1440 PNG) là một sự thật
    về **sản phẩm**. Hạ kích thước xong mà không giữ số cũ là xoá mất nó."""
    a, b = tmp_path / "gemini", tmp_path / "ta"
    _ghi(a, "p1", 1376, 768, "JPEG"); _ghi(b, "p1", 2560, 1440, "PNG")
    bk = C.chuan_hoa([a, b], tmp_path / "ra")
    assert bk["truoc"]["gemini"][0]["rong"] == 1376
    assert bk["truoc"]["gemini"][0]["dinh_dang"] == "jpeg"
    assert bk["truoc"]["ta"][0]["rong"] == 2560
    d = json.loads((tmp_path / "ra" / "ban_ke_chuan_hoa.json").read_text(encoding="utf-8"))
    assert d["truoc"] == bk["truoc"]


def test_ban_ke_NOI_RO_thu_KHONG_chua_duoc(tmp_path):
    """Ảnh Gemini đã qua JPEG một lần ở nguồn; hạ kích thước làm nhiễu mờ đi chứ
    không xoá. Giới hạn đó nghiêng về phía BẤT LỢI cho Gemini, phải nói ra."""
    a, b = tmp_path / "gemini", tmp_path / "ta"
    _ghi(a, "p1", 1376, 768, "JPEG"); _ghi(b, "p1", 2560, 1440, "PNG")
    bk = C.chuan_hoa([a, b], tmp_path / "ra")
    doc = bk["_doc"].lower()
    assert "khong chua duoc" in doc and "bat loi" in doc
    assert "tinh mu" in doc


# ═══════════ từ chối sớm thay vì ra một lô sai ══════════════════════════════
def test_mot_ben_rong_thi_TU_CHOI(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    _ghi(a, "p1", 100, 100)
    b.mkdir(parents=True)
    with pytest.raises(C.LoiChuanHoa):
        C.chuan_hoa([a, b], tmp_path / "ra")


def test_chi_mot_thu_muc_thi_TU_CHOI(tmp_path):
    a = tmp_path / "a"
    _ghi(a, "p1", 100, 100)
    with pytest.raises(C.LoiChuanHoa):
        C.chuan_hoa([a], tmp_path / "ra")


def test_thu_muc_khong_ton_tai_thi_bao_ro(tmp_path):
    a = tmp_path / "a"
    _ghi(a, "p1", 100, 100)
    with pytest.raises(C.LoiChuanHoa):
        C.chuan_hoa([a, tmp_path / "khong-co"], tmp_path / "ra")


def test_tep_hong_bao_ro_ten_tep(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    _ghi(a, "p1", 100, 100); _ghi(b, "p1", 100, 100)
    (a / "hong.png").write_bytes(b"khong phai anh")
    with pytest.raises(C.LoiChuanHoa) as e:
        C.chuan_hoa([a, b], tmp_path / "ra")
    assert "hong.png" in str(e.value)
