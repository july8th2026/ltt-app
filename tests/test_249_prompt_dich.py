"""
test_249 — dịch prompt trước khi gửi model ảnh (`platform_core/image_gen/prompt_dich.py`).

Mỗi test dưới đây neo vào một số đo thật của **D-027**, không vào một ý kiến.
Bối cảnh: HiDream-O1 trên máy B cho ra ảnh **không liên quan đến prompt** khi
prompt viết bằng tiếng Việt; cùng seed, bản tiếng Anh thì đúng.
"""
from __future__ import annotations

import unicodedata

import pytest

from platform_core.image_gen import prompt_dich as P


# ───────────────────── nhận biết có cần dịch không ──────────────────────────
def test_prompt_tieng_viet_thi_can_dich():
    assert P.can_dich("Con mèo tam thể nằm ngủ trên bậu cửa sổ")


def test_prompt_tieng_anh_thi_KHONG_goi_LLM():
    """Không gọi LLM khi không cần: đỡ một lượt gọi, đỡ credit, đỡ một chỗ hỏng."""
    goc = "A calico cat sleeping on a windowsill, afternoon light"
    kq = P.dich_prompt_anh(goc, goi_llm=None)      # goi_llm=None van phai chay duoc
    assert kq.prompt_model == goc and not kq.da_dich


def test_chi_co_CHU_CAN_VE_la_tieng_viet_thi_khong_can_dich():
    """⛔ Ca dễ sai: phần mô tả đã là tiếng Anh, chỉ chuỗi cần vẽ là tiếng Việt.
    Dịch lúc này là vô ích và còn rủi ro làm hỏng chuỗi cần vẽ."""
    assert not P.can_dich('A shop sign reading "CƠM TẤM SƯỜN BÌ" on yellow')


def test_nhan_dien_dau_tieng_viet_ca_khi_go_dang_to_hop():
    """Cùng chữ "ế" gõ dạng tổ hợp (e + dấu) phải nhận ra được, không thì phép so
    ký tự thô sẽ trượt và prompt đi thẳng sang model."""
    dung_san = unicodedata.normalize("NFC", "ế")
    to_hop = unicodedata.normalize("NFD", "ế")     # e + dau mu + dau sac
    assert dung_san != to_hop and len(to_hop) > len(dung_san), (
        "test nay RONG neu hai dang trung nhau")
    assert P.co_dau_tieng_viet(dung_san)
    assert P.co_dau_tieng_viet(to_hop), "phai chuan hoa NFC truoc khi so"


# ───────── chuỗi cần vẽ: điểm khác cốt lõi so với bản dịch của video ────────
def test_chuoi_trong_ngoac_KHONG_bi_dich(monkeypatch):
    """⛔ Đây là lý do tệp này tồn tại riêng. `"CƠM TẤM SƯỜN BÌ"` là **chữ sẽ vẽ
    vào ảnh**, không phải câu cần dịch. Dịch nó đi là giao sai hàng."""
    goc = 'Biển hiệu quán ăn với dòng chữ lớn "CƠM TẤM SƯỜN BÌ" màu đỏ trên nền vàng'
    thay = {}

    def gia_llm(text, he_thong):
        thay["gui"] = text
        thay["he_thong"] = he_thong
        # LLM tra ve ban dich CO GIU the giu cho.
        return 'A restaurant signboard with large red text "@@LTT_TEXT_0@@" on yellow'

    kq = P.dich_prompt_anh(goc, goi_llm=gia_llm)
    # Cai gui cho LLM khong duoc chua chuoi can ve.
    assert "CƠM TẤM SƯỜN BÌ" not in thay["gui"]
    assert "@@LTT_TEXT_0@@" in thay["gui"]
    # Ket qua thi PHAI chua lai nguyen van.
    assert '"CƠM TẤM SƯỜN BÌ"' in kq.prompt_model
    assert kq.chuoi_giu_nguyen == ("CƠM TẤM SƯỜN BÌ",)


def test_LLM_nuot_mat_the_thi_KHONG_im_lang_bo_qua():
    """Nếu bản dịch làm mất thẻ giữ chỗ thì chữ cần vẽ biến mất. Giao một ảnh
    thiếu chữ mà không ai biết là kiểu hỏng tệ nhất — phải nối lại."""
    goc = 'Poster ghi "GIẢM 50%" ở giữa'
    kq = P.dich_prompt_anh(goc, goi_llm=lambda t, h: "A poster in the centre")
    assert "GIẢM 50%" in kq.prompt_model


def test_nhieu_chuoi_can_ve_giu_dung_thu_tu():
    goc = 'Poster ghi "GIẢM 50% HÔM NAY" ở giữa, phía dưới là "Áp dụng đến 30/09"'
    kq = P.dich_prompt_anh(
        goc, goi_llm=lambda t, h: 'A poster with "@@LTT_TEXT_0@@" above "@@LTT_TEXT_1@@"')
    assert kq.chuoi_giu_nguyen == ("GIẢM 50% HÔM NAY", "Áp dụng đến 30/09")
    assert kq.prompt_model.index("GIẢM 50%") < kq.prompt_model.index("Áp dụng")


# ───────────────────────── cảnh báo dấu tiếng Việt ──────────────────────────
def test_canh_bao_khi_chu_can_ve_co_dau():
    """Đo thật: `CƠM TẤM` ra `CỜM TÀM`, `HÔM NAY` ra `HỐM NAY`. Nhưng cùng biển
    hiệu viết KHÔNG DẤU (`COM TAM SUON BI`) thì ra đúng từng chữ. Người dùng phải
    được biết trước, chứ không phải phát hiện sau khi trả tiền."""
    kq = P.dich_prompt_anh('A sign reading "CƠM TẤM SƯỜN BÌ"', goi_llm=None)
    assert kq.canh_bao and "dấu" in kq.canh_bao[0]


def test_chu_khong_dau_thi_KHONG_canh_bao():
    """Cảnh báo bắn oan sẽ bị người ta học cách bỏ qua."""
    kq = P.dich_prompt_anh('A sign reading "COM TAM SUON BI"', goi_llm=None)
    assert kq.canh_bao == ()


# ─────────────────── hỏng thì hỏng job, đừng gửi bản gốc ────────────────────
def test_LLM_hong_thi_NEM_chu_khong_gui_ban_tieng_viet():
    """⛔ Gửi bản tiếng Việt không phải phương án dự phòng — nó là giao một tấm
    ảnh sai mà khách vẫn trả tiền."""
    def hong(_):
        raise RuntimeError("het quota")

    with pytest.raises(P.DichThatBai):
        P.dich_prompt_anh("Con mèo ngủ trên bậu cửa sổ", goi_llm=hong)


def test_LLM_tra_ve_rong_thi_NEM():
    with pytest.raises(P.DichThatBai):
        P.dich_prompt_anh("Con mèo ngủ trên bậu cửa sổ", goi_llm=lambda t, h: "   ")


def test_LLM_khong_dich_gi_ca_thi_NEM():
    """LLM đôi khi trả lại nguyên văn. Gửi đi là rơi đúng vào lỗi mà tệp này sinh
    ra để tránh — nên phải bắt."""
    with pytest.raises(P.DichThatBai):
        P.dich_prompt_anh("Con mèo tam thể ngủ trên bậu cửa sổ",
                          goi_llm=lambda t, h: "Con mèo tam thể ngủ trên bậu cửa sổ")


def test_can_dich_nhung_khong_co_duong_goi_LLM_thi_NEM():
    with pytest.raises(P.DichThatBai):
        P.dich_prompt_anh("Con mèo ngủ trên bậu cửa sổ", goi_llm=None)


def test_prompt_rong_thi_NEM():
    with pytest.raises(P.DichThatBai):
        P.dich_prompt_anh("   ", goi_llm=None)


# ───────────────────────────── lời nhắc hệ thống ────────────────────────────
def test_loi_nhac_dan_LLM_giu_the_va_giu_chu_de_ban_dia():
    """Hai điều lời nhắc bắt buộc phải nói, vì thiếu cái nào cũng hỏng theo một
    kiểu riêng: mất thẻ giữ chỗ (mất chữ cần vẽ), và "phở" bị dịch thành "noodle
    soup" (mất đúng chủ đề khách cần)."""
    assert "@@LTT_TEXT_n@@" in P.LOI_NHAC_NEN
    assert "pho" in P.LOI_NHAC_NEN and "com tam" in P.LOI_NHAC_NEN


def test_ket_qua_xuat_ra_duoc_dict_de_ghi_vao_job():
    kq = P.dich_prompt_anh("A cat on a windowsill", goi_llm=None)
    d = kq.as_dict()
    assert set(d) == {"prompt_model", "da_dich", "chuoi_giu_nguyen", "canh_bao"}


# ═══ dò ngôn ngữ: model chỉ hiểu EN và ZH, mọi thứ khác PHẢI dịch ═══════════

@pytest.mark.parametrize("prompt, mong_doi", [
    ("A calico cat sleeping on a windowsill", "en"),
    ("Con mèo tam thể nằm ngủ trên bậu cửa sổ", "khac"),
    ("古墙上的静夜思，水墨风格", "zh"),
    ("猫が窓辺で寝ている", "khac"),          # tieng Nhat co kana
    ("แมวนอนอยู่ที่หน้าต่าง", "khac"),        # tieng Thai
    ("Кот спит на подоконнике", "khac"),      # tieng Nga
    ("고양이가 창턱에서 자고 있다", "khac"),   # tieng Han
])
def test_nhan_dien_ngon_ngu(prompt, mong_doi):
    """⛔ Bản đầu CHỈ dò dấu tiếng Việt. Một prompt tiếng Nhật, Thái, Hàn hay Nga
    sẽ **đi thẳng vào model và hỏng y hệt cách tiếng Việt đã hỏng** — mà không ai
    biết, vì không có lỗi nào báo. Model chỉ có benchmark EN (0,979) và ZH (0,978);
    **không có thứ ba**."""
    assert P.nhan_dien_ngon_ngu(prompt) == mong_doi


def test_tieng_trung_KHONG_bi_dich():
    """Dịch tiếng Trung sang tiếng Anh là **làm hỏng** một thứ đang chạy tốt —
    model có benchmark ZH 0,978."""
    assert not P.can_dich("古墙上的静夜思")


def test_chu_can_ve_tieng_viet_KHONG_lam_prompt_anh_bi_dich_oan():
    """Phần mô tả đã là tiếng Anh, chỉ chuỗi cần vẽ là tiếng Việt ⇒ không dịch."""
    assert P.nhan_dien_ngon_ngu('A shop sign reading "CƠM TẤM SƯỜN BÌ"') == "en"


# ═══ giữ sắc tộc bản địa — sinh ra từ một số đo, không từ ý thích ═══════════

def test_loi_nhac_dan_LLM_giu_nguoi_viet_khi_prompt_goc_khong_noi():
    """Đo thật: bản tiếng Anh của *"đội bóng chuyền nữ"* cho ra **cầu thủ da
    trắng**, *"đầu bếp"* cho ra đầu bếp Âu — prompt gốc không nói sắc tộc và tiếng
    Anh không mang theo ngữ cảnh ấy."""
    assert "Vietnamese" in P.loi_nhac(giu_nguoi_viet=True)
    assert "Vietnamese" not in P.loi_nhac(giu_nguoi_viet=False).replace(
        "Vietnamese subjects", "")


def test_co_giu_nguoi_viet_TAT_DUOC():
    """Có khách cố ý muốn người nước ngoài. Một gợi ý ép cứng là một giới hạn."""
    thay = {}
    P.dich_prompt_anh("Chân dung một người phụ nữ",
                      goi_llm=lambda t, h: thay.setdefault("h", h) and "A portrait of a woman"
                      or "A portrait of a woman",
                      giu_nguoi_viet=False)
    assert "describe them as Vietnamese" not in thay["h"]


# ═══ thông điệp hỏng phải có LỐI ĐI TIẾP ═══════════════════════════════════

def test_loi_dich_NOI_RA_cach_di_tiep():
    """⛔ Một lời từ chối không kèm lối ra biến thành ngõ cụt: khách bấm lại, hỏng
    lại, rồi bỏ đi. Model chỉ hiểu Anh/Trung ⇒ khách tự viết tiếng Anh là đi được
    ngay. Phải nói ra."""
    def hong(t, h):
        raise RuntimeError("het quota")
    with pytest.raises(P.DichThatBai) as e:
        P.dich_prompt_anh("Con mèo ngủ trên bậu cửa sổ", goi_llm=hong)
    t = str(e.value)
    assert "tiếng Anh" in t and "tiếng Trung" in t
    assert "het quota" in t, "phai giu ca ly do ky thuat de con truy duoc"
