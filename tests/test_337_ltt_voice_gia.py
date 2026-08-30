"""Giá của LTT VOICE — khuôn tầng 3 của `docs/KHUON_BAN_MODEL_NHA.md`.

Sáu chốt, và mỗi chốt ở đây có một sự cố thật đứng sau nó ở H37/H38.
"""
from __future__ import annotations

import math

import pytest

from apps.ltt_voice import gia, text_pipeline
from apps.ltt_voice.manifest import MANIFEST

#: Số đo thật trên RTX 5060 Ti ngày 2026-08-30 (`docs/LTT_VOICE/do_v1.json`).
#: `(mo ta, van ban, giay audio do duoc)`.
DO_THAT = [
    ("cau ngan", "Xin chào, đây là giọng đọc thử của LTT Studios.", 3.36),
    ("en ngan", "This is a short English sentence to check pronunciation.", 3.60),
    ("tron vi/en",
     "Chúng tôi dùng API để gọi model text to speech trên server.", 3.12),
    ("nhieu so va ngay",
     "Doanh thu tháng 8 đạt 1.500.000 đồng, tăng 12% so với ngày 12/08/2026, "
     "lúc 14h30.", 8.16),
    ("danh sach", "1. Mở ứng dụng.\n2. Chọn giọng đọc.\n3. Bấm tạo tiếng.", 3.04),
]

#: Bậc độ dài đã đo, `(so ky tu, giay audio)`.
DO_DAI_DA_DO = [(500, 24.42), (1000, 47.66), (1500, 71.62),
                (2000, 97.10), (3000, 144.54)]


def test_bang_gia_co_phien_ban():
    """3.1 — không có phiên bản thì không đối soát được một hoá đơn cũ."""
    assert gia.PHIEN_BAN_GIA
    b = gia.bang_gia()
    assert b["phien_ban"] == gia.PHIEN_BAN_GIA
    assert b["muc"], "bang gia rong thi trang cong khai khong co gi de hien"


def test_bang_gia_lay_tu_chinh_ham_ra_hoa_don():
    """3.6 — gõ lại số vào template là tạo bảng giá thứ hai."""
    muc = next(m for m in gia.bang_gia()["muc"] if "vi_du" in m)
    for vd in muc["vi_du"]:
        giay = float(vd["mo_ta"].split("~")[1].split()[0].replace(",", "."))
        if "phút" in vd["mo_ta"]:
            giay *= 60
        assert vd["credit"] == gia.tinh(giay)


@pytest.mark.parametrize("giay", [0.001, 0.5, 1, 3.36, 60, 144.54, 3600])
def test_lam_tron_len_va_toi_thieu_mot_credit(giay):
    """3.2 — số học số nguyên, làm tròn LÊN, tối thiểu 1 credit."""
    c = gia.tinh(giay)
    assert isinstance(c, int)
    assert c >= 1
    assert c >= (giay * gia.MCREDIT_MOI_GIAY) / gia.MCREDIT_MOI_CREDIT - 1e-9


def test_gia_khong_giam_khi_dai_hon():
    """Đơn điệu. Một bài dài hơn không bao giờ được rẻ hơn."""
    truoc = 0
    for giay in [1, 5, 10, 30, 60, 120, 300]:
        c = gia.tinh(giay)
        assert c >= truoc
        truoc = c


@pytest.mark.parametrize("ten,text,giay", DO_THAT, ids=[d[0] for d in DO_THAT])
def test_giu_cho_luon_lon_hon_gia_that_tren_so_do_that(ten, text, giay):
    """🔴 3.3 — `uoc_tran()` giữ chỗ **>= giá thật, LUÔN LUÔN**.

    Giữ thiếu thì khách tiêu quá số dư. Đây là một lỗi sổ sách, không phải một
    lỗi hiển thị, nên nó được chốt bằng **số đo thật** chứ không bằng một ví dụ
    tự nghĩ ra.
    """
    giu = MANIFEST.credit_cost({"text": text})
    that = gia.tinh(giay)
    assert giu >= that, f"{ten}: giu {giu} < that {that}"


@pytest.mark.parametrize("so_ky_tu,giay", DO_DAI_DA_DO)
def test_giu_cho_du_o_moi_bac_do_dai(so_ky_tu, giay):
    giu = MANIFEST.credit_cost({"text": "x" * so_ky_tu})
    assert giu >= gia.tinh(giay)


def test_giu_cho_uoc_tren_van_ban_da_chuan_hoa():
    """Phần NỞ của chuẩn hoá phải nằm trong ước, không nằm ngoài.

    "1.500.000 đồng" là 14 ký tự nhưng đọc ra gần 30 ký tự chữ. Ước trên bản thô
    thì mọi văn bản thường phải trả giá cho khả năng đó.
    """
    tho = "Giá 1.500.000 đồng, giảm 25% từ ngày 12/08/2026."
    assert len(text_pipeline.chuan_hoa(tho)) > len(tho)
    assert MANIFEST.credit_cost({"text": tho}) >= gia.uoc_tran(so_ky_tu=len(tho))


def test_khong_do_duoc_thi_thu_khong():
    """3.5 — không đo được ⇒ hoàn đủ, thu 0."""
    from apps.ltt_voice.features import KetQua, YeuCau
    kq = KetQua(yeu_cau=YeuCau(text="x"), audio_key="k", giay=0.0,
                text_da_chuan_hoa="x")
    assert kq.credit_that == 0
    assert kq.as_result()["credit_cost"] == 0


def test_ket_qua_luon_bao_credit_cost():
    """🔴 4.4 — handler PHẢI báo `credit_cost`.

    Không báo thì `job_runner._quyet_toan_credit` thu **trọn phần đã giữ**, im
    lặng. Đó đúng là lỗi H37 đã mắc: khách xin 4 ảnh, máy trả 2, vẫn bị thu 4.
    """
    from apps.ltt_voice.features import KetQua, YeuCau
    kq = KetQua(yeu_cau=YeuCau(text="x" * 100), audio_key="k", giay=10.0,
                text_da_chuan_hoa="x" * 100)
    r = kq.as_result()
    assert "credit_cost" in r
    assert r["credit_cost"] == gia.tinh(10.0)
    assert r["phien_ban_gia"] == gia.PHIEN_BAN_GIA


def test_quyet_toan_theo_san_pham_that_khong_theo_phan_da_giu():
    """🔴 3.4 — xin dài mà nhận ngắn thì trả theo ngắn."""
    from apps.ltt_voice.features import KetQua, YeuCau
    yc = YeuCau(text="x" * 1500)
    giu = MANIFEST.credit_cost({"text": yc.text})
    # Cổng chỉ sinh được 5 giây thay vì ~94 giây đáng lẽ.
    kq = KetQua(yeu_cau=yc, audio_key="k", giay=5.0, text_da_chuan_hoa=yc.text)
    assert kq.credit_that == gia.tinh(5.0)
    assert kq.credit_that < giu


def test_cong_don_lo_lam_tron_dung_mot_lan():
    """Cộng mcredit rồi làm tròn một lần, không làm tròn từng đoạn.

    Làm tròn 20 lần cho một bài 20 đoạn là bắt khách trả tới 20 credit cho việc
    làm tròn chứ không cho tiếng nói.
    """
    doan = [2.4] * 20
    assert gia.tinh_lo(doan) < sum(gia.tinh(g) for g in doan)
    assert gia.tinh_lo(doan) >= gia.tinh(sum(doan)) - 1


def test_gia_ghi_danh_la_mot_lan():
    assert gia.CREDIT_GHI_DANH >= 1
    assert MANIFEST.credit_cost(
        {"_job_type": "ltt_voice.enroll"}) == gia.CREDIT_GHI_DANH


def test_uoc_giay_phu_moi_so_do_that():
    """Hàm ước giây phải >= MỌI thời lượng đã đo thật.

    Đây là phép kiểm bắt được lỗi khi mô hình giá còn là một phép chia phẳng:
    câu 47 ký tự đo được 14,0 ký tự/giây trong khi bài 3.000 ký tự đạt 20,8, nên
    không một mẫu số nào vừa cả hai. Nếu một số đo mới rơi xuống dưới đường ước
    thì test này đỏ **trước khi** một khách bị giữ thiếu.
    """
    for ten, text, giay in DO_THAT:
        da = text_pipeline.chuan_hoa(text)
        assert gia.giay_uoc(len(da)) >= giay, (
            f"{ten}: uoc {gia.giay_uoc(len(da)):.2f}s < do that {giay}s")
    for so_ky_tu, giay in DO_DAI_DA_DO:
        assert gia.giay_uoc(so_ky_tu) >= giay, (
            f"{so_ky_tu} ky tu: uoc {gia.giay_uoc(so_ky_tu):.1f}s < do that {giay}s")
