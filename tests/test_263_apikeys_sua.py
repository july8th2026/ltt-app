"""
test_263 — sửa API key mà **không mất lịch sử**, và chặn tick nhầm category.

Không mạng, không GPU.

⛔ SỰ CỐ THẬT 2026-08-23, và nó tốn hai vòng mới tìm ra.

   Chủ dự án thêm khoá `ltt_image` xong báo *"Provider đâu có ltt_image"*. Hoá ra
   có **hai mục menu cùng tên "APIKEYS"**, và mục kia (`can_create = False`) không
   có nút tạo lẫn dropdown provider.

   Thêm được rồi thì khoá vào với category `model_control` thay vì `image`. Hợp lệ
   về mặt danh sách nên form nhận — nhưng provider `ltt_image` chỉ khai `('image',)`,
   nên `api_pool` **không bao giờ cấp phát nó**, và lỗi báo ra là
   `ThieuKeyError: khong co API key kha dung` — một câu nói về một thứ **khác** với
   nguyên nhân thật.

   Và không có đường sửa `categories` nào từ giao diện, nên cách duy nhất để chữa
   là **xoá khoá đi tạo lại** — mất `total_requests`, `health_score`, và id mà nhật
   ký đang tham chiếu.
"""
from __future__ import annotations

import pytest

from platform_core import api_keys as A


class DbGia:
    def __init__(self):
        self.da_flush = 0

    def add(self, _row):
        pass

    def flush(self):
        self.da_flush += 1


def KeyGia(provider="ltt_image", categories=None):
    """Một `ApiKey` THẬT, chưa gắn session.

    Không dùng lớp giả: `flag_modified` cần `_sa_instance_state` của SQLAlchemy,
    và một đối tượng giả sẽ làm test xanh trong khi mã thật ném lỗi — đúng loại
    test tệ nhất."""
    from platform_core.models import ApiKey

    return ApiKey(
        id="khoa-cu-khong-duoc-doi", provider=provider,
        categories=list(categories or []), credential_enc="secret-cu",
        key_preview="Knro", total_requests=1234, total_success=1200,
        health_score=87)


# ═══════════ chặn tick nhầm category NGAY TỪ ĐẦU ════════════════════════════
def test_provider_khong_phuc_vu_category_thi_TU_CHOI():
    """⛔ Ràng buộc chính. `ltt_image` chỉ khai `('image',)`; nhận `model_control`
    là để một lỗi gõ nhầm đi thẳng vào CSDL rồi hỏng ở một chỗ cách xa nguyên nhân."""
    with pytest.raises(A.ApiKeyError) as e:
        A._chuan_hoa_categories(["model_control"], "ltt_image")
    assert "ltt_image" in str(e.value) and "image" in str(e.value)


def test_thong_bao_NOI_RO_provider_phuc_vu_gi():
    """Báo "sai category" thì người vận hành vẫn phải đi tra. Báo kèm danh sách
    đúng thì họ sửa được ngay.

    ⭐ Bản cũ dùng `gemini` làm ví dụ, vì lúc ấy nó khai `model_control/chat/
       image`. Sau 10/09/2026 nó khai **rỗng**, nên nó không còn từ chối gì —
       và một phép kiểm về *chất lượng thông điệp* không nên phụ thuộc vào việc
       nhà cung cấp nào còn sống. Đổi sang `ltt_image` (khai `image`) thì mệnh
       đề cũ được giữ **nguyên vẹn**, chỉ đứng trên một ví dụ còn tồn tại.
    """
    with pytest.raises(A.ApiKeyError) as e:
        A._chuan_hoa_categories(["video"], "ltt_image")
    loi = str(e.value)
    assert "video" in loi, "khong noi ro category nao sai"
    assert "image" in loi, "khong liet ke thu provider THUC SU phuc vu"


def test_category_dung_thi_cho_qua():
    assert A._chuan_hoa_categories(["image"], "ltt_image") == ["image"]
    assert A._chuan_hoa_categories(["chat", "image"], "gemini") == ["chat", "image"]


def test_provider_LA_thi_KHONG_chan():
    """Chỗ này kiểm một **lời khai**. Không có lời khai thì không có gì để kiểm —
    chặn bừa sẽ làm hỏng provider mới trước khi ai kịp khai nó."""
    assert A._chuan_hoa_categories(["image"], "provider-chua-ton-tai") == ["image"]


def test_khong_truyen_provider_thi_giu_hanh_vi_cu():
    """Bên gọi cũ không truyền `provider` — không được làm hỏng chúng."""
    assert A._chuan_hoa_categories(["image", "video"]) == ["image", "video"]


def test_category_khong_ton_tai_van_bi_TU_CHOI_nhu_truoc():
    with pytest.raises(A.ApiKeyError):
        A._chuan_hoa_categories(["khong-phai-category"], "gemini")


# ═══════════ gợi ý cho form ═════════════════════════════════════════════════
def test_goi_y_category_theo_provider():
    """Form dùng cái này để tick sẵn — người vận hành không phải đoán."""
    assert A.categories_goi_y("ltt_image") == ["image"]
    assert A.categories_goi_y("byteplus") == ["video"]
    assert A.categories_goi_y("khong-co") == []


def test_MOI_provider_CON_SONG_deu_khai_category():
    """Nếu một provider quên khai thì phép chặn ở trên **im lặng không chặn gì**
    cho riêng nó — và đó đúng là kiểu lỗ hổng khó thấy nhất.

    ⭐ 10/09/2026 mệnh đề này phải hẹp lại **một cách có chủ đích**: AI CLEAN
       REBUILD V2 làm rỗng `categories` của bốn nhà cung cấp đã nghỉ, vì một
       nhà cung cấp đã ngừng thì **không phục vụ category nào cả**. Nói "mọi
       provider đều phải khai category" sau đó là đòi một lời khai vô nghĩa.

    ⛔ Nhưng thu hẹp một mệnh đề là chỗ dễ làm yếu một phép kiểm nhất, nên vế
       thứ hai dưới đây **rộng ra** đúng bằng phần vừa hẹp lại: nhà cung cấp đã
       nghỉ phải khai **không** category nào. Trước đây không ai canh điều đó.

    ⚠️ Và ghi lại một hệ quả đã cân, không giấu: vì `_chuan_hoa_categories` có
       luật *"provider không khai gì thì không chặn"*, bốn nhà cung cấp nghỉ nay
       **không còn bị chặn theo category**. Chốt thật cho chúng nằm ở chỗ khác
       và mạnh hơn — `providers.chan_neu_da_ngung()` từ chối MỌI lượt gọi, và
       `test_1008` chốt rằng `/capacity` cũng không đếm khoá của chúng.
    """
    from platform_core import providers as P

    song = [p for p in P.list_all() if p.is_active]
    nghi = [p for p in P.list_all() if not p.is_active]
    assert song and nghi, "tien de sai: registry phai co ca hai loai"

    thieu = [p.id for p in song if not (p.categories or ())]
    assert thieu == [], f"provider CON SONG chua khai categories: {thieu}"

    thua = [p.id for p in nghi if (p.categories or ())]
    assert thua == [], f"provider DA NGHI ma van khai categories: {thua}"


# ═══════════ sửa mà GIỮ NGUYÊN lịch sử ══════════════════════════════════════
def test_doi_category_GIU_NGUYEN_id_va_lich_su():
    """⭐ Lý do cả tệp này tồn tại. Xoá đi tạo lại là mất `total_requests`,
    `health_score`, và một id mà nhật ký vận hành đang tham chiếu."""
    k = KeyGia(categories=["model_control"])
    A.cap_nhat_categories(DbGia(), k, ["image"])
    assert k.categories == ["image"]
    assert k.id == "khoa-cu-khong-duoc-doi"
    assert (k.total_requests, k.total_success, k.health_score) == (1234, 1200, 87)


def test_doi_category_KHONG_dung_toi_credential():
    """Sửa một ô tick không được phép vô tình xoá mất khoá."""
    k = KeyGia(categories=["model_control"])
    A.cap_nhat_categories(DbGia(), k, ["image"])
    assert k.credential_enc == "secret-cu" and k.key_preview == "Knro"


def test_doi_category_van_bi_KIEM_theo_provider():
    """Đường sửa không được lỏng hơn đường tạo — nếu không thì nó thành lối vòng."""
    k = KeyGia(categories=["image"])
    with pytest.raises(A.ApiKeyError):
        A.cap_nhat_categories(DbGia(), k, ["video"])


def test_cot_JSON_duoc_danh_dau_da_doi():
    """⛔ Cột JSON của SQLAlchemy: gán một list mới mà không `flag_modified` thì
    thay đổi **bị bỏ qua lặng lẽ** — commit chạy, không lỗi, dữ liệu không đổi."""
    import inspect
    assert "flag_modified" in inspect.getsource(A.cap_nhat_categories)


# ═══════════ hai mục menu không được trùng tên ══════════════════════════════
def test_hai_muc_menu_APIKEYS_khong_con_trung_ten():
    """⛔ Hai mục cùng tên là lý do chủ dự án vào nhầm trang không tạo được khoá.
    Trang sqladmin có `can_create = False`, nên nó không có nút tạo lẫn dropdown."""
    from server.admin import ApiKeyAdmin, ApiKeysConsole

    assert ApiKeysConsole.name != getattr(ApiKeyAdmin, "name_plural", "")
    assert ApiKeyAdmin.can_create is False, (
        "neu trang nay tao duoc key thi ten trung khong con nguy hiem - "
        "nhung luc do phai kiem no ma hoa credential")


def test_console_co_nut_SUA_tro_dung_trang():
    import inspect

    from server import admin
    ma = inspect.getsource(admin.ApiKeysConsole)
    assert "/admin/api-key-sua?id=" in ma, "console khong co duong vao trang sua"


def test_trang_sua_co_dang_ky_vao_admin():
    import inspect

    from server import admin
    assert "add_view(SuaApiKeyView)" in inspect.getsource(admin)


# ═══════════ reset phải reset THẬT ══════════════════════════════════════════
def test_reset_dat_lai_ca_HEALTH_SCORE():
    """`chon_key` xếp hạng theo `health_score`. Reset mà không đụng tới nó thì
    khoá đã hồi phục vẫn bị đẩy xuống cuối mãi — và người vận hành thấy trạng thái
    về `active` nên tưởng đã xong."""
    import inspect

    from server import admin
    ma = inspect.getsource(admin.ApiKeyActionView)
    i = ma.index('op == "reset"')
    assert "health_score" in ma[i:i + 700], "reset khong dat lai health_score"


def test_refresh_hong_thi_BAO_chu_khong_nuot():
    """`except ProviderLiveError: pass` khiến người vận hành bấm nút, trang tải
    lại, và không có gì cho biết nó đã hỏng."""
    import inspect

    from server import admin
    ma = inspect.getsource(admin.ApiKeyActionView)
    i = ma.index('op == "refresh"')
    doan = ma[i:i + 1200]
    assert "ProviderLiveError as e" in doan, "van nuot loi khong giu lai ly do"
    assert "loi=" in doan, "khong bao gi cho nguoi van hanh"
