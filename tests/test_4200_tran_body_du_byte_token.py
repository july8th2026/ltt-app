"""test_4200 — bất biến: trần thân request PHẢI đủ byte cho cửa sổ công bố
RỘNG NHẤT, ở byte/token đo được, cho MỌI model — không phải một số bốc đại.

═══════════════════════════════════════════════════════════════════════════
 SỰ CỐ SINH RA TỆP NÀY (25/09/2026)
═══════════════════════════════════════════════════════════════════════════

`POST /api/v1/messages` với thân **1.150.067 byte** ăn `413 payload_too_large`
ở trần khi đó **1.048.576 byte** (1 MiB, `DEFAULT_MAX_BODY_BYTES` mặc định,
production không ghi đè `LTT_PUBLIC_API_MAX_BODY_BYTES`). Khách nén hội thoại
**4 lần liên tiếp vẫn 413** — không có đường ra.

`apps/ltt_llm/ngan_sach.py::BODY_BYTES_TOI_THIEU` VÀ phép kiểm bảo vệ nó
(`tests/test_334_ngan_sach_ltt_llm.py::TestDoiChieuNenTang
::test_tran_body_cua_nen_tang_du_cho_tran_vao_cua_app`) đã tồn tại TRƯỚC sự cố
này — và cả hai đều XANH. Lý do: `BYTE_MOI_TOKEN_JSON` (giả định byte/token,
đo 30/08 trên thân Codex) là **4,5**, cho `BODY_BYTES_TOI_THIEU` ≈ 999 KB —
nhỏ hơn trần mặc định 1 MiB đúng **2,4%**. Ca sản xuất thật ăn
`1.150.067 / 227.328 = 5,059` byte/token — VƯỢT giả định cũ. Phép kiểm cũ
không sai (nó vẫn đúng công thức); GIẢ ĐỊNH đầu vào của nó sai, và không có gì
đối chiếu giả định ấy với ca thật.

⭐ NÊN TỆP NÀY GHIM HAI THỨ CÙNG LÚC:
   1. Số ĐO ĐƯỢC (`5,059`) — sự cố thật, không được ai hạ hằng số byte/token
      xuống dưới nó mà không biết đang tái hiện đúng sự cố 25/09.
   2. Một phép kiểm CHỐT THEO TẬP HỢP: duyệt MỌI model trong
      `ngan_sach.CUA_SO_THEO_MODEL` (không gõ cứng tên `qwen38-api`/
      `qwen35-api`) — thêm một model thứ ba với cửa sổ rộng hơn mà quên nâng
      trần thân theo là ĐỎ, không phải một model bị bỏ sót lặng lẽ.

⛔ KHÔNG TỰ VIẾT BỘ ĐẾM TOKEN. Mọi số ở đây đọc từ `ngan_sach` (đã dùng
   `platform_core/llm/uoc_token.py` để đo, xem chú thích `BYTE_MOI_TOKEN_JSON`).
"""
from __future__ import annotations

import pytest

from apps.ltt_llm import ngan_sach
from platform_core.public_api.config import load_public_api_config


#: Tỉ lệ byte/token ĐO ĐƯỢC trên chính sự cố production 25/09/2026:
#: `1_150_067 / 227_328` (227.328 = ngân sách ƯỚC của model cửa sổ rộng nhất
#: đang bán, `max(CUA_SO_THEO_MODEL) - TOKEN_RA_TRAN - DEM_UOC`). Đây là SỐ ĐO
#: của một ca thật, không phải một hằng số chọn — giữ nguyên phân số gốc để
#: người sau thấy đúng cách ra số, không phải một float đã làm tròn.
_QUAN_SAT_SU_CO_BYTES = 1_150_067
_QUAN_SAT_SU_CO_UOC_TOKEN = 227_328
TY_LE_DO_DUOC_SU_CO_25_09 = _QUAN_SAT_SU_CO_BYTES / _QUAN_SAT_SU_CO_UOC_TOKEN  # ~5.059


def test_ty_le_do_duoc_khop_phep_tinh_da_ghi():
    """Đối chứng phép tính ở trên — sai một số ở đây là ghim sai cả sự cố."""
    assert _QUAN_SAT_SU_CO_UOC_TOKEN == (
        max(ngan_sach.CUA_SO_THEO_MODEL.values())
        - ngan_sach.TOKEN_RA_TRAN - ngan_sach.DEM_UOC), (
        "227.328 khong con khop cong thuc song — mot hang so goc da doi, "
        "tinh lai TY_LE_DO_DUOC_SU_CO_25_09 tu du lieu su co that")
    assert round(TY_LE_DO_DUOC_SU_CO_25_09, 3) == 5.059


def test_byte_moi_token_khong_thap_hon_ca_da_do():
    """⛔ BÁNH CÓC: hạ `BYTE_MOI_TOKEN_JSON` xuống dưới tỉ lệ đã đo trên chính
    sự cố 25/09 là LẶP LẠI sự cố 25/09 — dù có làm tròn đẹp cỡ nào."""
    assert ngan_sach.BYTE_MOI_TOKEN_JSON >= TY_LE_DO_DUOC_SU_CO_25_09, (
        f"BYTE_MOI_TOKEN_JSON={ngan_sach.BYTE_MOI_TOKEN_JSON} thap hon ty le "
        f"da do tren san xuat ({TY_LE_DO_DUOC_SU_CO_25_09:.3f}) — se tu choi "
        f"lai dung than da tung bi choi ngay 25/09")


class TestTranThanDuChoMoiModelCongBo:
    """Bất biến CHỐT THEO TẬP HỢP: trần thân >= cửa sổ ƯỚC × byte/token đo
    được, cho **từng** model — không chỉ cho model rộng nhất hôm nay.

    ⭐ Vì sao lặp qua từng model thay vì chỉ kiểm `BODY_BYTES_TOI_THIEU`
       (vốn đã lấy `max()`): `max()` tự bảo vệ khỏi việc bỏ SÓT một model rộng
       hơn, nhưng nếu chính công thức tính `BODY_BYTES_TOI_THIEU` bị viết lại
       và vô tình đổi từ `max()` sang model mặc định (đúng khuyết tật F-02 đã
       xảy ra ở `CUA_SO_MODEL` lịch sử), phép kiểm CHỈ đọc hằng số đã tính sẵn
       sẽ không thấy gì sai. Lặp qua `CUA_SO_THEO_MODEL.items()` trực tiếp ở
       ĐÂY hỏi lại đúng câu hỏi gốc cho từng model, độc lập với cách
       `ngan_sach` tự tổng hợp nội bộ.
    """

    def test_moi_model_deu_du_cho(self):
        cfg = load_public_api_config()
        thieu = []
        for model_id in ngan_sach.CUA_SO_THEO_MODEL:
            vao_toi_da_uoc = ngan_sach.tran_vao_cua(model_id)
            can_toi_thieu = vao_toi_da_uoc * ngan_sach.BYTE_MOI_TOKEN_JSON
            if cfg.max_body_bytes < can_toi_thieu:
                thieu.append(
                    f"{model_id}: can >= {can_toi_thieu:.0f} B nhung tran chi "
                    f"cho {cfg.max_body_bytes} B (vao_toi_da_uoc={vao_toi_da_uoc})")
        assert not thieu, (
            "tran than khong du cho it nhat mot model dang cong bo:\n"
            + "\n".join(thieu))

    def test_them_mot_model_gia_lap_RONG_HON_thi_do(self):
        """Mô phỏng đúng câu hỏi bánh cóc đòi hỏi: một model THỨ BA, cửa sổ
        rộng hơn mọi model đang bán, mà trần thân KHÔNG được nâng theo, phải
        làm phép kiểm ở trên đỏ nếu chạy lại với bảng model đã mở rộng.

        ⛔ Test này không gọi hàm `test_moi_model_deu_du_cho` (pytest không
           cho gọi test khác như hàm thường mà giữ nguyên ngữ nghĩa fixture),
           nó viết lại đúng phép so sánh với một bảng model giả lập tại chỗ —
           để không phụ thuộc cách `ngan_sach` tổ chức bảng thật.
        """
        cfg = load_public_api_config()
        bang_gia_lap = dict(ngan_sach.CUA_SO_THEO_MODEL)
        # Model gia lap: cua so gap doi model rong nhat that, dem_uoc/token_ra
        # giu nguyen cua model mac dinh cho don gian.
        rong_nhat_that = max(bang_gia_lap.values())
        bang_gia_lap["model-gia-lap-rong-hon"] = rong_nhat_that * 2

        vao_toi_da_uoc_gia_lap = (bang_gia_lap["model-gia-lap-rong-hon"]
                                  - ngan_sach.TOKEN_RA_TRAN - ngan_sach.DEM_UOC)
        can_toi_thieu_gia_lap = vao_toi_da_uoc_gia_lap * ngan_sach.BYTE_MOI_TOKEN_JSON
        assert cfg.max_body_bytes < can_toi_thieu_gia_lap, (
            "phep thu nay tu no phai la mot ca ĐỎ khi ap dung — neu tran hien "
            "tai TINH CO du cho ca model gap doi thi phep gia lap chua du "
            "'rong hon', tang he so gia lap len")


def test_body_bytes_toi_thieu_van_nam_duoi_tran_mac_dinh():
    """Đối chứng dương: với hằng số đã nâng, `BODY_BYTES_TOI_THIEU` (tính từ
    model rộng nhất THẬT, không phải model giả lập ở trên) phải NẰM DƯỚI trần
    mặc định hiện hành — nếu không thì chính default đã chọn lại quá sát."""
    cfg = load_public_api_config()
    assert cfg.max_body_bytes >= ngan_sach.BODY_BYTES_TOI_THIEU
    bien_phan_tram = (
        (cfg.max_body_bytes - ngan_sach.BODY_BYTES_TOI_THIEU)
        / ngan_sach.BODY_BYTES_TOI_THIEU * 100)
    assert bien_phan_tram >= 10, (
        f"bien chi con {bien_phan_tram:.1f}% giua tran mac dinh va san toi "
        f"thieu — day chinh la hinh dang da gay su co 25/09 (bien 2,4%)")


def test_khong_con_tai_hien_dung_ca_25_09():
    """Regression ghim đúng con số của sự cố: thân ĐÃ TỪNG bị chặn oan
    (1.150.067 B, nằm trong ngân sách ƯỚC của model rộng nhất) nay phải lọt."""
    cfg = load_public_api_config()
    assert cfg.max_body_bytes >= _QUAN_SAT_SU_CO_BYTES, (
        f"tran mac dinh {cfg.max_body_bytes} B van tu choi dung than "
        f"{_QUAN_SAT_SU_CO_BYTES} B da gay 413 oan ngay 25/09")


@pytest.mark.parametrize("model_id", sorted(ngan_sach.CUA_SO_THEO_MODEL))
def test_khong_gopy_cung_ca_tren_TUNG_model_rieng(model_id):
    """Cùng câu hỏi của sự cố thật (thân gần kín ngân sách ƯỚC một model), lặp
    qua từng model bằng `pytest.mark.parametrize` — id ca hỏng in ra đúng tên
    model, không phải một khẳng định gộp không nói được model nào thiếu."""
    cfg = load_public_api_config()
    vao_toi_da_uoc = ngan_sach.tran_vao_cua(model_id)
    than_gan_kin = int(vao_toi_da_uoc * ngan_sach.BYTE_MOI_TOKEN_JSON)
    assert than_gan_kin <= cfg.max_body_bytes, (
        f"{model_id}: mot than dung gan kin ngan sach uoc ({vao_toi_da_uoc} "
        f"token uoc, o {ngan_sach.BYTE_MOI_TOKEN_JSON} B/token) can "
        f"{than_gan_kin} B nhung tran chi cho {cfg.max_body_bytes} B")
