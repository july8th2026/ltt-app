"""B9-1 — cỡ chữ phụ đề phải theo khung RA, ⛔ không chỉ theo chiều cao.

🔴 **Ca thật (T1a, 28/09).** Một lần chạy đổi khung `16:9 -> 9:16` giao một tệp
   mà **97/98 dòng phụ đề vượt bề rộng khung**, dòng rộng nhất gấp **6,1 lần**.
   libass tự ngắt lại ⇒ **8 dòng che ~75 % hình** (frame `t=70`).

   Sinh lại `.ass` bằng chính `viet_tep_ass` cho hai khung **cùng chiều cao**:

       NGUON  16:9 (1024x576)   Style: Default,Arial,48,...   PlayResX: 1024
       BANGIAO 9:16 ( 324x576)  Style: Default,Arial,48,...   PlayResX:  324

   **Cỡ chữ 48 ở CẢ HAI.** Khung hẹp đi 3,16 lần, cỡ chữ ⛔ không đổi.

⭐ **Cùng họ với B8, và là nửa còn thiếu của nó.** B8 đổi trục **DỌC**
   (`margin_v` theo khung ra). Trục **NGANG** thì ⛔ không ai đổi.

🔑 **Vì sao `42` là bằng chứng chứ ⛔ không phải một con số tuỳ tiện.**

       (1024 - 20 - 20) / (48 x 0,5) = 41,0   ~   KY_TU_MOI_DONG = 42

   Hằng số ngắt dòng **chính là** công thức bề rộng, tính sẵn ở khung tham
   chiếu. Nên nếu co **cả bố cục** theo tỉ lệ bề rộng thì số ký tự mỗi dòng
   **giữ nguyên** — và ⛔ không cần ngắt lại câu.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from apps.auto_scan_video import phu_de as pd

HO_SO = {"che_do": "tu_dong", "kieu": "default", "phan_doan": "sentence",
         "xuat_srt": False}
SU_KIEN = [{"start": 1.0, "end": 4.0, "index": 0, "scene_id": "s1",
            "text": "Su dung hoa luc manh de kim ham thu dich.",
            "display_text": "Su dung hoa luc manh de kim ham thu dich.",
            "line_count": 1}]


def _style(tmp: Path, rong: int, cao: int) -> list[str]:
    """Trả các trường của dòng `Style:` trong `.ass` sinh ra cho khung này."""
    thu = tmp / ("k%dx%d" % (rong, cao))
    thu.mkdir()
    duong = pd.viet_tep_ass(HO_SO, SU_KIEN, thu, rong=rong, cao=cao)
    noi = Path(duong).read_text(encoding="utf-8-sig")
    dong = next(d for d in noi.splitlines() if d.startswith("Style:"))
    return dong[len("Style:"):].split(",")


def _co_chu(truong: list[str]) -> int:
    return int(truong[2])


def _le_ngang(truong: list[str]) -> int:
    #: `Style:` = Name,Fontname,Fontsize,...,Alignment,MarginL,MarginR,MarginV,Enc
    return int(truong[-4])


# ── Bất biến chính ───────────────────────────────────────────────────────────

def test_hai_khung_NGUOC_ti_le_cho_HAI_co_chu_khac_nhau(tmp_path):
    """🔑 Bài chốt chính. Một bài chỉ chốt MỘT khung sẽ xanh cả khi công thức
    ⛔ không hề đọc bề rộng — đúng cách B8 đã chốt `margin_v`.
    """
    rong_16_9 = _co_chu(_style(tmp_path, 1024, 576))
    rong_9_16 = _co_chu(_style(tmp_path, 324, 576))
    assert rong_9_16 < rong_16_9, (
        "co chu 9:16 = %d, 16:9 = %d — cong thuc dang ⛔ khong doc be rong"
        % (rong_9_16, rong_16_9))


#: Câu dài nhất thật của T1a (90 ký tự sau khi chuẩn hoá khoảng trắng).
CAU_DAI = ("Sử dụng hỏa lực mạnh để kìm hãm thủ địch, đồng thời che chắn cho "
           "các thành viên trong đội.")


def _ass(tmp: Path, rong: int, cao: int, cac_cau=(CAU_DAI,)):
    """Trả `(trường Style, các dòng Dialogue)` cho khung và tập câu này."""
    thu = tmp / ("k%dx%d_%d" % (rong, cao, len(cac_cau)))
    thu.mkdir(exist_ok=True)
    sk = [{"start": 1.0 + i, "end": 2.0 + i, "index": i,
           "scene_id": "s%d" % i, "text": c, "display_text": c,
           "line_count": 1} for i, c in enumerate(cac_cau)]
    noi = Path(pd.viet_tep_ass(HO_SO, sk, thu, rong=rong, cao=cao)
               ).read_text(encoding="utf-8-sig")
    kieu = next(d for d in noi.splitlines() if d.startswith("Style:"))
    thoai = [d for d in noi.splitlines() if d.startswith("Dialogue:")]
    return kieu[len("Style:"):].split(","), thoai


@pytest.mark.parametrize("rong,cao", [(1024, 576), (324, 576), (1080, 1920),
                                      (720, 1280), (1920, 1080)])
def test_HAI_DONG_la_tran_cung_va_moi_dong_VUA_be_rong(tmp_path, rong, cao):
    """🔴 Chủ dự án chốt 28/09: **tối đa 2 dòng**, cỡ chữ cơ động theo khung.

    ⚠️ Hai vế phải đo **cùng nhau**. Chỉ đếm dòng thì một cỡ chữ to vẫn "2
       dòng" trong `.ass` rồi **libass ngắt lại** thành tám — đúng ca T1a. Chỉ
       đo bề rộng thì một bản vá hạ trần xuống 4 dòng cũng xanh.
    """
    truong, thoai = _ass(tmp_path, rong, cao)
    co, le = _co_chu(truong), _le_ngang(truong)
    con_lai = rong - 2 * le
    for d in thoai:
        # ⚠️ Tách theo ĐÚNG 9 dấu phẩy đầu của `Dialogue:`, ⛔ không tách theo
        #    `",,"` — chuỗi ấy khớp cả `Default,,` (trường Name rỗng) nên phần
        #    "văn bản" sẽ dính thêm `0,0,0,,` và **mọi** dòng dài thêm 8 ký tự.
        #    ⭐ Chính tôi đã mắc nó, và nó báo lỗi trên một sản phẩm ĐÚNG.
        dong = d.split(",", 9)[9].split("\\N")
        assert len(dong) <= pd.SO_DONG_TOI_DA, (
            "%dx%d: %d dong, tran la %d" % (rong, cao, len(dong),
                                            pd.SO_DONG_TOI_DA))
        for x in dong:
            assert pd._be_rong_dong(x, co) <= con_lai, (
                "%dx%d co_chu %d: dong %d ky tu chiem ~%.0f px, khung con %d px"
                % (rong, cao, co, len(x), pd._be_rong_dong(x, co), con_lai))


def test_hai_khung_NGUOC_ti_le_cho_HAI_co_chu_khac_nhau_2(tmp_path):
    """Nhắc lại bất biến chính trên tập câu thật, ⛔ không chỉ câu ngắn."""
    assert (_co_chu(_ass(tmp_path, 324, 576)[0])
            < _co_chu(_ass(tmp_path, 1024, 576)[0]))


# ── Vế ⛔ KHÔNG được đổi ─────────────────────────────────────────────────────

def test_khung_RONG_hon_16_9_KHONG_duoc_phong_TO_chu(tmp_path):
    """⛔ Phép co chỉ đi MỘT chiều.

    Một khung rộng hơn tham chiếu ⛔ không có lỗi gì để sửa, nên phóng to chữ ở
    đó là **đổi hành vi ⛔ không vì lý do nào** — đúng hình dạng *"mã phòng thủ
    cho ca ⛔ không thể xảy ra"*.
    """
    assert _co_chu(_ass(tmp_path, 2048, 576, ("Ngan.",))[0]) <= 48


def test_cau_NGAN_o_khung_tham_chieu_GIU_NGUYEN_co_chu_preset(tmp_path):
    """⛔ Phép co chỉ chạm những khung/câu THẬT SỰ tràn.

    ⭐ Thiếu bài này thì một bản vá co chữ vô điều kiện sẽ âm thầm thu nhỏ phụ
       đề của **mọi** khách 16:9 đang chạy.
    """
    truong, _ = _ass(tmp_path, 1024, 576, ("Mot cau ngan.",))
    assert _co_chu(truong) == 48
    # ⭐ Lề thì CÓ đổi, và đó là một chốt riêng của chủ dự án (28/09): sàn
    #    *title safe* 90 % của SMPTE = 5 % mỗi cạnh. `1024 × 0,05 = 51`, rộng
    #    hơn `margin_h = 20` của preset nên sàn thắng. Xem `LE_AN_TOAN_PHAN`.
    assert _le_ngang(truong) == round(1024 * pd.LE_AN_TOAN_PHAN)


def test_chu_HAN_tinh_be_rong_GAP_DOI(tmp_path):
    """⚠️ Chế độ phụ đề `nguon` giữ tiếng Trung — một chữ Hán chiếm **cả ô**.

    Bỏ qua điều đó thì bề rộng được tính bằng **một nửa** sự thật và chữ tràn
    ra ngoài khung — đúng loại lỗi mà chính B9 sinh ra để xoá.
    """
    assert pd._be_rong_dong("狙击", 48) == pytest.approx(
        pd._be_rong_dong("abcd", 48))

    # ⚠️ **⛔ Không chốt "chữ Hán ⇒ cỡ chữ nhỏ hơn".** Tôi viết vế ấy trước và
    #    nó ĐỎ trên một sản phẩm đúng: `wrap_lines` ngắt được chữ Hán theo
    #    **từng ký tự** (⛔ không cần dấu cách), nên nó tự bù bằng cách chia hai
    #    dòng — cùng cỡ chữ, ⛔ không tràn. Thứ đáng chốt là **⛔ không tràn**.
    truong, thoai = _ass(tmp_path, 324, 576, ("狙击" * 20,))
    co, le = _co_chu(truong), _le_ngang(truong)
    for d in thoai:
        for x in d.split(",", 9)[9].split("\\N"):
            assert pd._be_rong_dong(x, co) <= 324 - 2 * le, (
                "dong chu Han %d ky tu o co chu %d tran khung" % (len(x), co))


# ── Vị trí so với DẢI CHỮ GỐC (chủ dự án chốt 28/09) ─────────────────────────

def _margin_v(truong: list[str]) -> int:
    return int(truong[-2])


def test_vung_lam_mo_RONG_o_1_3_duoi_keo_phu_de_XUONG_de_len_vet_mo(tmp_path):
    """🔴 Ca T1a: khách khoanh `lam_mo` đúng dải phụ đề Hoa và ⛔ không có gì xảy ra.

    Đáy chữ mới phải trùng **đáy dải** ⇒ `margin_v = (1 − y1) × cao`.
    Dải `y1 = 0,96` trên khung `576` ⇒ `23`.
    """
    ho = dict(HO_SO, che_do="tu_dong")
    vung = [{"loai": "lam_mo", "x0": 0.10, "x1": 0.90,
             "y0": 0.82, "y1": 0.96}]
    ho["dai_phu_de_goc"] = pd.dai_phu_de_goc(vung)
    assert ho["dai_phu_de_goc"] is not None, (
        "vung lam mo rong o 1/3 duoi phai duoc nhan la dai phu de goc")
    assert pd.vi_tri_tu_dong(ho, cao=576)["margin_v"] == round((1 - 0.96) * 576)


def test_KHONG_co_dai_thi_lui_ve_san_title_safe_5_phan_tram(tmp_path):
    """⭐ Mặc định cho video ⛔ không có chữ gốc — SMPTE/Netflix *title safe* 90 %.

    ⚠️ Trước B9 nhánh này giữ `margin_v = 30` **tuyệt đối** của preset: đúng
       `5,2 %` trên khung `576` nhưng chỉ **`1,6 %`** trên khung `1920`.
    """
    ho = dict(HO_SO, che_do="tu_dong")
    assert pd.vi_tri_tu_dong(ho, cao=576) == {}, (
        "khung 576: preset (30) da rong hon san (29) nen phai GIU preset")
    assert (pd.vi_tri_tu_dong(ho, cao=1920)["margin_v"]
            == round(1920 * pd.LE_AN_TOAN_PHAN))


# ── B9-2: neo lớp phủ chữ ───────────────────────────────────────────────────

def test_lop_phu_x_la_TAM_chu_chu_khong_phai_mep_trai():
    """🔴 Ca T1a: *"LTT STUDIOS"* đặt `x = 0,5` hiện ra **"LTT STUD"**.

    `drawtext` neo `x` ở **mép trái** hộp chữ, nên khách kéo tới giữa thì
    nhận mép trái ở giữa và đuôi chữ tràn ra ngoài khung.

    ⭐ `text_w` là biến của chính `drawtext` — ffmpeg đo font rồi mới thay vào,
       nên đây là chỗ **duy nhất** bề rộng chữ được biết.
    """
    from apps.auto_scan_video import che_do_render as cdr

    ve = cdr._loc_chu(
        [{"chu": "LTT STUDIOS", "x": 0.5, "y": 0.06, "co_chu": 0.06,
          "do_mo": 1.0, "vien": True, "mau": "trang"}],
        ["/tmp/chu.txt"], "vao", "ra", cao_khung=576)
    loc = "".join(ve)
    assert "-text_w/2" in loc, (
        "x van dang neo MEP TRAI — khach dat 0,5 se nhan chu lech sang phai")
    assert "x=(W*0.500000)-text_w/2" in loc


def test_lop_phu_van_KHONG_kep_ve_bien():
    """⛔ Luật L3 giữ nguyên — phép neo lại ⛔ không được lặng lẽ đảo nó.

    ⭐ Thiếu bài này thì một bản sửa *"cho chữ khỏi tràn"* rất dễ thêm một
       `max(0, ...)`, và khi đó chữ khách cố tình đặt lệch sẽ bị kéo về biên —
       đúng cái sai lầm mà chú thích tại chỗ đã ghi tên.
    """
    from apps.auto_scan_video import che_do_render as cdr

    loc = "".join(cdr._loc_chu(
        [{"chu": "x", "x": 0.0, "y": 0.5, "co_chu": 0.06, "do_mo": 1.0,
          "vien": False, "mau": "trang"}],
        ["/tmp/chu.txt"], "vao", "ra", cao_khung=576))
    assert "max(" not in loc and "min(" not in loc
    assert "x=(W*0.000000)-text_w/2" in loc
