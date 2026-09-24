"""Khuôn chạy ĐÚNG MỘT giai đoạn ASV (Task 4 của thang cổng từng bước).

## Vì sao cần

Muốn đo `transcribe` — một bước ~20 giây — hiện phải đi qua `media_prepare` +
`audio_prepare` trước, tức **3 phút để đo một bước 20 giây**. Thang đo từng bước
siết từng mắt xích, nên nó chạy phép đo đó hàng chục lần; 3 phút mỗi lần là lý do
người ta thôi đo.

## ⚠️ Gieo theo TẬP ĐỌC THẬT, không theo cột `sau`

`BAN_DO_BUOC.md` §2: bản khai `sau=` **hẹp hơn** thứ mã thật sự đọc ở 8/12 giai
đoạn (bao đóng bắc cầu thì phủ, nên hôm nay không hỏng — N-08). Gieo theo cột `sau`
sẽ cho một lỗi *"thiếu đầu vào"* **nghe như khiếm khuyết sản phẩm**, và người đọc
sẽ đi sửa nhầm chỗ.

## ⛔ Không viết đường xin card thứ hai, không gõ lại bảng 12 nhánh

* card ⇒ `fx.card_cho_job` (đã có, gọi chính `_vram_can` + `_giu_gpu` của worker);
* trình thông dịch ⇒ `fx.ghim_python_co_card` (đã có);
* chọn giai đoạn ⇒ `thi_hanh.chay_giai_doan` — **bề mặt công khai** mà hai executor
  thật đang dùng. Gõ lại bảng 12 nhánh ở đây là dựng đúng cái N-08 cảnh báo: **hai
  chỗ khai cùng một điều, không ai bắt khớp**.
"""
from __future__ import annotations

import pytest

from tests import test_423_asv_giao_dien as _mt

moi_truong = _mt.moi_truong


def test_khuon_ton_tai_va_khai_du_be_mat():
    """Bề mặt tối thiểu của khuôn — chốt TRƯỚC khi viết nó."""
    from tests.fixtures import asv_mot_buoc

    assert callable(asv_mot_buoc.chay_mot_buoc)


def test_chay_mot_buoc_KHONG_chay_cac_buoc_truoc(moi_truong, tmp_path, monkeypatch):  # noqa: F811
    """Cả mục đích của khuôn: đo một bước 20 giây không phải trả 3 phút.

    🔑 Chốt bằng cách **đếm ai bị gọi**: thay `chay` của cả 12 module giai đoạn bằng
       một hàm ghi tên. Nếu khuôn lỡ chạy cả chuỗi thì danh sách sẽ dài hơn một.
    """
    from apps.auto_scan_video import pipeline
    from tests.fixtures import asv_mot_buoc

    goi: list[str] = []
    for ten, mod in asv_mot_buoc.MODULE_GIAI_DOAN.items():
        def ghi(db, kho, *, run, ctx=None, _t=ten):
            goi.append(_t)
            return {"phan": [], "tom_tat": {"stage": _t}}
        monkeypatch.setattr(mod, "chay", ghi, raising=True)

    asv_mot_buoc.chay_mot_buoc(
        moi_truong, ten_giai_doan=pipeline.TRANSCRIBE,
        duong_video=None, cai_dat={"nguon_loi": "asr"},
        gieo={pipeline.MEDIA_PREPARE: "asset:tieng.wav"}, xin_card=False)

    assert goi == [pipeline.TRANSCRIBE], f"da chay ca cac buoc khac: {goi}"


def test_thieu_GIEO_thi_noi_RO_thieu_gi_chu_khong_nem_KeyError(moi_truong, tmp_path):  # noqa: F811
    """⛔ ĐỐI CHỨNG. Gọi một bước KHÔNG phải bước đầu mà không gieo gì.

    🔴 Một `KeyError` trống ở đây là cái bẫy tệ nhất của cả thang: người đo sẽ đọc
       nó như *"sản phẩm hỏng"* trong khi nó là *"khuôn thiếu đầu vào"*. Và đúng
       chuyện đó đã xảy ra ở lượt A (N-06): `auto_match_thieu_can_cu` mất ba vòng
       mới tách được ra khỏi *"AUTO_MATCH là đường chết"*.
    """
    from apps.auto_scan_video import pipeline
    from tests.fixtures import asv_mot_buoc

    with pytest.raises(asv_mot_buoc.ThieuDauVaoGieo) as e:
        asv_mot_buoc.chay_mot_buoc(
            moi_truong, ten_giai_doan=pipeline.TRANSCRIBE,
            duong_video=None, cai_dat={}, gieo=None, xin_card=False)
    cau = str(e.value)
    assert pipeline.TRANSCRIBE in cau
    assert pipeline.MEDIA_PREPARE in cau, (
        f"cau loi khong noi THIEU GI: {cau!r}")
    assert "gieo" in cau.lower()


def test_TAP_DOC_THAT_chu_khong_phai_cot_sau():
    """⚠️ `compose` đọc 4 giai đoạn mà nó KHÔNG khai trong `sau=`.

    Khuôn phải đòi đúng tập **đọc thật**; đòi theo `sau` sẽ để lọt và lỗi hiện ra ở
    giữa bước, dưới dạng một thông báo của sản phẩm.
    """
    from apps.auto_scan_video import pipeline
    from tests.fixtures import asv_mot_buoc

    can = asv_mot_buoc.can_gieo(pipeline.COMPOSE)
    assert {pipeline.MEDIA_PREPARE, pipeline.AUDIO_PREPARE,
            pipeline.CONTENT_PROCESS, pipeline.VOICE_SYNTHESIS,
            pipeline.TIMING_ALIGN} <= can, sorted(can)
    assert set(pipeline.THEO_TEN[pipeline.COMPOSE].sau) < can, (
        "khuon dang doi theo cot `sau` — hep hon thuc te")


def test_buoc_DAU_khong_doi_gieo_gi():
    """`media_prepare` đọc `run.source_key`, không đọc giai đoạn nào."""
    from apps.auto_scan_video import pipeline
    from tests.fixtures import asv_mot_buoc

    assert asv_mot_buoc.can_gieo(pipeline.MEDIA_PREPARE) == set()
