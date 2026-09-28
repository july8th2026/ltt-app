"""test_4200 — bất biến: trần thân request PHẢI đủ byte cho cửa sổ công bố
RỘNG NHẤT, ở byte/token đo được, cho MỌI model — không phải một số bốc đại.

═══════════════════════════════════════════════════════════════════════════
 SỰ CỐ SINH RA TỆP NÀY (25/09/2026) — VÀ HAI LẦN ĐO SAI TRƯỚC KHI CÓ SỐ ĐÚNG
═══════════════════════════════════════════════════════════════════════════

`POST /api/v1/messages` ăn `413 payload_too_large` ở trần 1.048.576 B (1 MiB,
`DEFAULT_MAX_BODY_BYTES` mặc định, production không ghi đè
`LTT_PUBLIC_API_MAX_BODY_BYTES`). Khách nén hội thoại **4 lần liên tiếp vẫn
413** — không có đường ra.

Hai lần đo ĐẦU của chính lần sửa này đều là ca "đọc thứ đại diện thay vì đo
thứ thật", và cả hai đã bị RÚT LẠI:

  1. Soi ngược thân "1.150.067 B" tưởng là sản xuất thật — nó là **phép dò
     tổng hợp của người báo lỗi** (`'x' * 1_150_000`, một triệu ký tự ASCII
     không dấu câu, không phải hội thoại), và "5,059 byte/token" suy ra từ đó
     bịa mẫu số (gán 227.328 — ngân sách một model — cho một chuỗi không
     liên quan).
  2. Đọc MỘT ảnh chụp thanh đo % tại một khoảnh khắc, suy ra ≈10,64 byte/token
     — đúng HƯỚNG, nhưng đoán sai model (ảnh cho `ltt-3.5`, khách thật đã đổi
     sang `ltt-3.8` trước khi chụp) vì ảnh chụp không phải bản ghi đầy đủ.

SỐ DÙNG ĐỂ CHỐT: bản ghi phiên thật `session-0019f199` (165 bước; tệp ghi là
NHIỀU KHUNG zstd nối nhau — giải nén phải dùng
`zstandard.ZstdDecompressor().stream_reader(f, read_across_frames=True)`, đọc
một khung sẽ THIẾU dữ liệu). `usage` cuối cùng trước 413: `totalTokens =
80.823` (cacheRead 80.395, input 350 — token THẬT máy B báo, không phải ước
lượng), thân request **vượt** 1.048.576 B. `80.823 / 0,65 ≈ 124.343 ≈
124.245 = cong_bo_cua("qwen38-api")` xác nhận model đúng là `ltt-3.8` VÀ xác
nhận mẫu số thanh `%` (`plugins/llm-ltt/src/adapter.ts` gán `contextWindow =
entry.context_window` từ catalog `/api/v1/models`, tức `cong_bo_cua(model)`).

⇒ tỉ lệ **SÀN** (canh dưới kép — cả tử số lẫn mẫu số đều là cận dưới của giá
trị thật): `1.048.576 / 80.823 ≈ 12,97` byte/token. Phiên đó có 190 sự kiện
`tool/result` và khối suy nghĩ luôn bật (`ltt-3.8` mặc định `medium`) — cao
gấp ~3–4 lần mọi mẫu tiếng Việt/mã nguồn tự dựng của lần sửa này (tệ nhất đo
được 4,35 byte/token ước). Phần chênh CHƯA giải thích hết bằng dữ liệu đang
có; xem chú thích đầy đủ ở `apps/ltt_llm/ngan_sach.py::BYTE_MOI_TOKEN_JSON`.

`apps/ltt_llm/ngan_sach.py::BODY_BYTES_TOI_THIEU` VÀ phép kiểm bảo vệ nó
(`tests/test_334_ngan_sach_ltt_llm.py::TestDoiChieuNenTang
::test_tran_body_cua_nen_tang_du_cho_tran_vao_cua_app`) đã tồn tại TRƯỚC sự cố
này — và cả hai đều XANH, ở CẢ hai lần đo sai lẫn lần đo đúng, vì bản thân
công thức chưa từng sai; GIẢ ĐỊNH `BYTE_MOI_TOKEN_JSON` mà nó nhân vào mới là
chỗ sai, và không có gì đối chiếu giả định ấy với ca thật cho tới tệp này.

⭐ NÊN TỆP NÀY GHIM HAI THỨ CÙNG LÚC:
   1. Tỉ lệ SÀN đo được trên bản ghi thật (`12,97`) — không được ai hạ hằng
      số byte/token xuống dưới nó mà không biết đang tái hiện đúng sự cố
      25/09.
   2. Một phép kiểm CHỐT THEO TẬP HỢP: duyệt MỌI model trong
      `ngan_sach.CUA_SO_THEO_MODEL` (không gõ cứng tên `qwen38-api`/
      `qwen35-api`) — thêm một model thứ ba với cửa sổ rộng hơn mà quên nâng
      trần thân theo là ĐỎ, không phải một model bị bỏ sót lặng lẽ.

⛔ KHÔNG TỰ VIẾT BỘ ĐẾM TOKEN. Số 80.823 đọc thẳng từ `usage` thật của bản ghi
   phiên (provider-reported, không phải ước lượng của A hay của kho này).
"""
from __future__ import annotations

import pytest

from apps.ltt_llm import ngan_sach
from platform_core.public_api.config import load_public_api_config


#: Tỉ lệ byte/token **SÀN** đo được trên bản ghi phiên thật `session-0019f199`
#: (165 bước, giải nén xong mới đọc được — xem docstring tệp): `usage` cuối
#: trước 413 có `totalTokens = 80.823` (token THẬT), thân request **vượt**
#: 1.048.576 B (bất đẳng thức, không phải giá trị chính xác — trần khi đó là
#: 1 MiB). Giữ nguyên phân số gốc, không làm tròn trước, để người sau thấy
#: đúng cách ra số.
_QUAN_SAT_PHIEN_THAT_BYTES_VUOT = 1_048_576
_QUAN_SAT_PHIEN_THAT_TOKEN_THAT = 80_823
TY_LE_SAN_SESSION_0019F199 = (
    _QUAN_SAT_PHIEN_THAT_BYTES_VUOT / _QUAN_SAT_PHIEN_THAT_TOKEN_THAT)  # ~12.97

#: ⛔ HAI SỐ ĐÃ BỊ RÚT LẠI — giữ ở đây làm bánh cóc ngược: nếu số nào dưới đây
#: xuất hiện trở lại trong vai trò "sàn"/"canh trên" ở bất kỳ chú thích hay
#: phép kiểm nào, đó là dấu hiệu ai đó đang lặp lại đúng lỗi đã sửa 25/09.
#:   * 5,059 — suy từ phép dò tổng hợp ASCII (`'x' * 1_150_000`), không phải
#:     hội thoại thật; mẫu số "227.328 token" cho chuỗi đó là bịa.
#:   * 10,64 — suy từ MỘT ảnh chụp thanh đo (không phải bản ghi), và đoán sai
#:     model đang chạy (`ltt-3.5` thay vì `ltt-3.8` thật).
_SO_DA_RUT_LAI = (5.059, 10.64)


def test_ty_le_san_khop_phep_tinh_da_ghi():
    """Đối chứng phép tính ở trên — sai một số ở đây là ghim sai cả sự cố."""
    assert round(TY_LE_SAN_SESSION_0019F199, 2) == 12.97


def test_byte_moi_token_khong_thap_hon_san_da_do():
    """⛔ BÁNH CÓC: hạ `BYTE_MOI_TOKEN_JSON` xuống dưới tỉ lệ SÀN đã đo trên
    chính bản ghi sự cố 25/09 là LẶP LẠI sự cố 25/09 — dù có làm tròn đẹp cỡ
    nào, và dù đơn vị (token THẬT, không phải token ước) phải khớp."""
    assert ngan_sach.BYTE_MOI_TOKEN_JSON >= TY_LE_SAN_SESSION_0019F199, (
        f"BYTE_MOI_TOKEN_JSON={ngan_sach.BYTE_MOI_TOKEN_JSON} thap hon ty le "
        f"san da do tren session-0019f199 ({TY_LE_SAN_SESSION_0019F199:.3f}) "
        f"— se tu choi lai dung than da tung bi choi ngay 25/09")


def test_khong_dung_lai_hai_so_da_rut_lai():
    """Bánh cóc ngược: `BYTE_MOI_TOKEN_JSON` không được TRÙNG hay THẤP HƠN
    một trong hai số đã bị rút lại vì gán sai nguồn (xem `_SO_DA_RUT_LAI`)."""
    for so_sai in _SO_DA_RUT_LAI:
        assert ngan_sach.BYTE_MOI_TOKEN_JSON > so_sai, (
            f"BYTE_MOI_TOKEN_JSON={ngan_sach.BYTE_MOI_TOKEN_JSON} <= {so_sai} "
            f"— dung mot so DA BI RUT LAI vi gan sai nguon (xem docstring)")


class TestTranThanDuChoMoiModelCongBo:
    """Bất biến CHỐT THEO TẬP HỢP: trần thân >= cửa sổ **công bố** (token
    THẬT, `cong_bo_cua`) × byte/token đo được, cho **từng** model — không chỉ
    cho model rộng nhất hôm nay, và không dùng ngân sách ƯỚC nội bộ
    (`tran_vao_cua`/`CUA_SO_THEO_MODEL`) vốn ở đơn vị KHÁC.

    ⭐ Vì sao lặp qua từng model thay vì chỉ kiểm `BODY_BYTES_TOI_THIEU`
       (vốn đã lấy `max()`): `max()` tự bảo vệ khỏi việc bỏ SÓT một model rộng
       hơn, nhưng nếu chính công thức tính `BODY_BYTES_TOI_THIEU` bị viết lại
       và vô tình đổi từ `max()` sang model mặc định (đúng khuyết tật F-02 đã
       xảy ra ở `CUA_SO_MODEL` lịch sử), phép kiểm CHỈ đọc hằng số đã tính sẵn
       sẽ không thấy gì sai. Lặp qua `CUA_SO_THEO_MODEL` trực tiếp ở ĐÂY hỏi
       lại đúng câu hỏi gốc cho từng model, độc lập với cách `ngan_sach` tự
       tổng hợp nội bộ.
    """

    def test_moi_model_deu_du_cho(self):
        cfg = load_public_api_config()
        thieu = []
        for model_id in ngan_sach.CUA_SO_THEO_MODEL:
            cong_bo = ngan_sach.cong_bo_cua(model_id)
            # 28/09: CONG so hang ANH. Truoc hom nay phep nay chi tinh CHU, va
            # do la ly do `ANH_BYTE_TOI_DA = 12 MiB` cong bo duoc trong 6 tuan
            # ma khong request nao dat toi: hai phep canh nhau doc cung mot san
            # bang HAI cong thuc khac nhau thi cai thieu hon khong ai bat.
            can_toi_thieu = (cong_bo * ngan_sach.BYTE_MOI_TOKEN_JSON
                             + ngan_sach.BODY_BYTES_ANH_TOI_THIEU)
            if cfg.max_body_bytes < can_toi_thieu:
                thieu.append(
                    f"{model_id}: can >= {can_toi_thieu:.0f} B nhung tran chi "
                    f"cho {cfg.max_body_bytes} B (cong_bo_cua={cong_bo})")
        assert not thieu, (
            "tran than khong du cho it nhat mot model dang cong bo:\n"
            + "\n".join(thieu))

    def test_them_mot_model_gia_lap_RONG_HON_thi_do(self):
        """Mô phỏng đúng câu hỏi bánh cóc đòi hỏi: một model THỨ BA, cửa sổ
        công bố rộng hơn mọi model đang bán, mà trần thân KHÔNG được nâng
        theo, phải làm phép kiểm ở trên đỏ nếu chạy lại với bảng đã mở rộng.

        ⛔ Test này không gọi hàm `test_moi_model_deu_du_cho` (pytest không
           cho gọi test khác như hàm thường mà giữ nguyên ngữ nghĩa fixture),
           nó viết lại đúng phép so sánh với một cửa sổ công bố giả lập tại
           chỗ — để không phụ thuộc cách `ngan_sach` tổ chức bảng thật.

        🔴 28/09/2026 — PHÉP TIÊM NGHỊCH NÀY ĐÃ TỪNG RỖNG, VÀ ĐÓ LÀ LÝ DO NÓ
           KHÔNG CÒN GÕ MỘT HỆ SỐ NÀO NỮA.

           Bản trước lấy `cửa sổ giả lập = rộng nhất × 2`, một hệ số **gõ tay
           không buộc vào gì**. Khi trần thân nâng 4 MiB → 32 MiB, sàn của một
           model gấp đôi (4,85 MB) **vừa** trần mới ⇒ phép này đỏ, và thông điệp
           của chính nó phải bảo người đọc "tăng hệ số giả lập lên".

           Một phép tiêm nghịch cần người bảo trì đi nâng hằng số bằng tay mỗi
           lần trần đổi thì **sẽ có một lần không ai nâng** — và lần đó nó im
           lặng mất sức phân biệt, chứ không đỏ. Nên nay cửa sổ giả lập được
           **suy từ chính trần**: nhỏ nhất vừa đủ để KHÔNG vừa.

        ⭐ Và hai phép khẳng định dưới đây kiểm HAI điều khác nhau:
           1. cửa sổ giả lập thật sự RỘNG HƠN mọi model đang bán (nếu không, nó
              không mô phỏng "model thứ ba rộng hơn" mà mô phỏng một model hẹp
              hơn — phép thử vô nghĩa, và ca đó xảy ra nếu trần bị nâng vô lối);
           2. sàn của nó VƯỢT trần — tức phép ở trên sẽ đỏ.
        """
        cfg = load_public_api_config()
        cong_bo_rong_nhat_that = max(
            ngan_sach.cong_bo_cua(m) for m in ngan_sach.CUA_SO_THEO_MODEL)
        # Cửa sổ nhỏ NHẤT mà sàn của nó không còn vừa trần hiện tại. `+ 1` đẩy
        # nó qua đúng một token, nên đây là ca biên — không phải một ca thừa.
        cong_bo_gia_lap = int(
            (cfg.max_body_bytes - ngan_sach.BODY_BYTES_ANH_TOI_THIEU)
            / ngan_sach.BYTE_MOI_TOKEN_JSON) + 1
        assert cong_bo_gia_lap > cong_bo_rong_nhat_that, (
            f"cua so gia lap {cong_bo_gia_lap} KHONG rong hon model rong nhat "
            f"dang ban {cong_bo_rong_nhat_that} — phep tiem nghich nay dang mo "
            f"phong mot model HEP hon, tuc no khong con thu dieu no noi la thu. "
            f"Tran than {cfg.max_body_bytes} da duoc nang qua muc can thiet.")
        can_toi_thieu_gia_lap = (
            cong_bo_gia_lap * ngan_sach.BYTE_MOI_TOKEN_JSON
            + ngan_sach.BODY_BYTES_ANH_TOI_THIEU)
        assert cfg.max_body_bytes < can_toi_thieu_gia_lap, (
            "phep thu nay tu no phai la mot ca ĐỎ khi ap dung")


def test_body_bytes_toi_thieu_van_nam_duoi_tran_mac_dinh():
    """Đối chứng dương: với hằng số đã nâng, `BODY_BYTES_TOI_THIEU` (tính từ
    model rộng nhất THẬT, không phải model giả lập ở trên) phải NẰM DƯỚI trần
    mặc định hiện hành, với biên đủ rộng — nếu không thì chính default đã
    chọn lại quá sát (đúng hình dạng đã gây sự cố hai lần: biên 2,4% rồi biên
    ~6% trên một CANH DƯỚI)."""
    cfg = load_public_api_config()
    assert cfg.max_body_bytes >= ngan_sach.BODY_BYTES_TOI_THIEU
    bien_phan_tram = (
        (cfg.max_body_bytes - ngan_sach.BODY_BYTES_TOI_THIEU)
        / ngan_sach.BODY_BYTES_TOI_THIEU * 100)
    assert bien_phan_tram >= 25, (
        f"bien chi con {bien_phan_tram:.1f}% giua tran mac dinh va san toi "
        f"thieu — hai lan truoc sua o bien 2,4% roi ~6% tren mot CANH DUOI da "
        f"deu khong du; dung ha bien xuong duoi 25% ma khong do lai tu dau")


@pytest.mark.parametrize("model_id", sorted(ngan_sach.CUA_SO_THEO_MODEL))
def test_mot_than_gan_kin_cua_so_cong_bo_thi_lot(model_id):
    """Cùng câu hỏi của sự cố thật (thân gần kín cửa sổ CÔNG BỐ một model, ở
    tỉ lệ byte/token đã chốt), lặp qua từng model bằng
    `pytest.mark.parametrize` — id ca hỏng in ra đúng tên model, không phải
    một khẳng định gộp không nói được model nào thiếu."""
    cfg = load_public_api_config()
    cong_bo = ngan_sach.cong_bo_cua(model_id)
    than_gan_kin = int(cong_bo * ngan_sach.BYTE_MOI_TOKEN_JSON)
    assert than_gan_kin <= cfg.max_body_bytes, (
        f"{model_id}: mot than dung gan kin cua so cong bo ({cong_bo} token "
        f"that, o {ngan_sach.BYTE_MOI_TOKEN_JSON} B/token) can {than_gan_kin} "
        f"B nhung tran chi cho {cfg.max_body_bytes} B")
