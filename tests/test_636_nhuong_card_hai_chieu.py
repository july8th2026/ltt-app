"""
Nhường card giữa LLM và model ảnh — bốn nhánh, và mỗi nhánh một cách hỏng thật.

🔴 Máy B có **một** card 24.576 MB. Qwen thường trú 19.237 MB, HiDream đỉnh
   18.450 MB. Hai model không bao giờ cùng lúc được, nên swap không phải tối ưu
   hoá — nó là **chế độ vận hành duy nhất**.

🔴 HAI NHÁNH ĐẦU ĐÃ ĐƯỢC GỠ (dual-model 5.4a, 12/09/2026).

     1. ~~đang TÍNH thì KHÔNG đuổi~~   ─┐
     2. ~~chỉ GIỮ bộ nhớ thì đuổi được~~  ─┘ `xin_card` không còn tồn tại
     3. lấy lại được thì đừng báo bận — báo bận là khoá chết cả đường ảnh;
     4. không lấy lại được thì báo bận — và đó là câu trả lời đúng.

   Trọng tài cũ nằm **trong chính cổng render** và nhả model bằng `GET /unload` —
   một lệnh **không mang tên model**, nay đo được là nó nhả **mọi** model đang chạy
   (DECISION_LOG L-17), tức từ khi máy B có hai model thì nó giết luôn LTT-3.5 trên
   card không ai tranh. Thay bằng trọng tài residency (D01 B): xả trước, nhả theo
   **tên model**, không bao giờ giết lượt đang chạy.

   ⭐ Bất biến của hai nhánh bỏ đi **không mất**, nó đổi chỗ:
       `platform_core/llm/residency.py` — `buoc_thuan` chỉ rời `LLM` khi đã drain,
       và chỉ phát `nap_llm` khi `vram_3090_mib <= vram_sach_mib`;
       `tests/test_1216_residency_thuan.py` — ca `vram_con_ban` / `vram_sach`.

⛔ Cả bốn đo được **không cần GPU**: mọi nguồn tín hiệu đều tiêm được. Một phép
   kiểm đòi GPU là một phép kiểm sẽ bị tắt.
"""
from __future__ import annotations

import pytest

from render_gateway import busy as B


# ── Nhánh 3+4: `/health` chỉ báo bận khi KHÔNG lấy lại được ─────────────────

class _ComfyGia:
    def queue_prompt_ids(self):
        return ([], [])

    def alive(self):
        return True


def _watcher(*, ngoai_mb, so_python, co_ho):
    w = B.BusyWatcher(comfy=_ComfyGia(),
                      ram_trong_toi_thieu_gb=0.0,
                      doc_vram_mb=lambda: ngoai_mb + 1_500,
                      dem_python_gpu=lambda: so_python,
                      co_ho_bao_duoc=lambda: co_ho)
    w._tong_mb = 24_576
    # `_tai_nguyen` đọc RAM/VRAM ngoài; ép thẳng để test không chạm máy thật.
    w._tai_nguyen = lambda: (ngoai_mb + 1_500, 100.0, ngoai_mb)   # type: ignore[assignment]
    return w


def test_health_KHONG_bao_ban_khi_card_lay_lai_duoc():
    """🔴 Nhánh này gỡ một KHOÁ CHẾT THEO THỨ TỰ, đo 04/09/2026.

    Máy A hỏi `/health` trước khi gửi lệnh vẽ và hoãn job nếu `busy`. Nhánh VRAM
    bật `busy` mỗi khi bất kỳ ai giữ card — kể cả Qwen, kẻ ta bảo nhả được. Nên
    lệnh vẽ không bao giờ tới, và `xin_card` **không bao giờ chạy**.

    Bằng chứng: `gateway.log` không có một `POST` nào, `/unload` gọi đúng 6 lần
    trong toàn bộ lịch sử, và job ảnh nằm `queued` vô hạn trong khi ComfyUI sống
    và hàng đợi trống.
    """
    st = _watcher(ngoai_mb=20_431, so_python=1, co_ho=True).observe(set())
    assert st.busy is False, st.reason


def test_health_BAO_BAN_khi_ho_giu_card_khong_bao_duoc():
    """Không có hộ bảo-được ⇒ giữ nguyên hành vi cũ, và nó cứu một ca thật.

    Đo 22/08: `llama-server` ôm 15,9 GB, GPU 0 % tải, phép đếm python trả về 1 ⇒
    cổng báo rảnh trong khi card chỉ còn 4,6 GB.
    """
    st = _watcher(ngoai_mb=20_431, so_python=1, co_ho=False).observe(set())
    assert st.busy is True
    assert "dang giu" in st.reason


def test_health_BAO_BAN_khi_co_tien_trinh_khac_dang_tinh():
    """Lấy lại được **không** đủ: còn phải lấy lại mà không cắt ngang việc ai."""
    st = _watcher(ngoai_mb=20_431, so_python=2, co_ho=True).observe(set())
    assert st.busy is True


def test_khong_doc_duoc_so_python_thi_giu_hanh_vi_cu():
    """"Không biết" ⇒ không nhường ⇒ báo bận. An toàn về phía cũ."""
    st = _watcher(ngoai_mb=20_431, so_python=None, co_ho=True).observe(set())
    assert st.busy is True


# ── Hằng số dùng chung: một nguồn, không phải hai ──────────────────────────

def test_hai_cong_doc_CUNG_MOT_nguong_tai_gpu():
    """⛔ Một hằng số ở hai nơi là một hằng số sẽ lệch.

    Cổng ảnh dùng ngưỡng này để **không đuổi** một hộ đang tính; cổng LLM dùng nó
    để **không nạp đè** lên một lượt vẽ. Hai câu hỏi ngược chiều, cùng một ngưỡng.
    """
    from llm_gateway import trong_tai

    assert trong_tai.TAI_GPU_DANG_TINH is B.TAI_GPU_DANG_TINH


@pytest.mark.parametrize("ten", ["TRAN_PYTHON_GPU", "TAI_GPU_DANG_TINH"])
def test_hang_so_co_ten_chu_khong_go_thang(ten):
    """Hai tín hiệu của luật đều phải có TÊN — chúng được đọc ở nhiều chỗ."""
    assert isinstance(getattr(B, ten), int)


# ── Chiều LLM: model ta đã nạp KHÔNG cho phép nạp đè lên một lượt vẽ ────────

def _trong_tai(*, so_python, tai, model_cua_ta, comfy_ve):
    from llm_gateway.trong_tai import TrongTai

    return TrongTai(ram_trong_toi_thieu_gb=0.0,
                    dem_python_gpu=lambda: so_python,
                    tai_gpu=lambda: tai,
                    ram_trong_gb=lambda: 100.0,
                    model_cua_ta_dang_chay=lambda: model_cua_ta,
                    ho_kia_dang_ve=lambda: comfy_ve)


def test_tai_cao_cua_CHINH_TA_thi_khong_tu_choi():
    """Giữ nguyên bản sửa 31/08: 70 % lượt từng bị từ chối oan vì tải của ta."""
    px = _trong_tai(so_python=1, tai=95, model_cua_ta=True, comfy_ve=False).phan_xu()
    assert px.ban is False, px.ly_do


def test_model_ta_da_nap_MA_ComfyUI_DANG_VE_thi_van_ban():
    """🔴 Lỗ hổng đo được 04/09, và chính chú thích nhánh kia đã báo trước.

    `qwen38-api state=ready` + ComfyUI `queue_running=1` ⇒ card **24.178/24.576
    MiB, tải 86 %**: hai model vừa cùng thường trú vừa cùng làm việc. Và tiền đề
    của đánh đổi đã hỏng — VRAM của ta lúc ấy chỉ **13,3 GB** thay vì 22,4 GB,
    tức đã tràn sang RAM chủ.

    ⭐ Thứ sửa được không phải một ngưỡng tải khác mà một **nguồn tin khác**:
       mức tải là suy đoán, hàng đợi là sự thật.
    """
    px = _trong_tai(so_python=1, tai=86, model_cua_ta=True, comfy_ve=True).phan_xu()
    assert px.ban is True
    assert "ComfyUI dang ve that" in px.ly_do


def test_hoi_hang_doi_hong_thi_GIU_HANH_VI_CU():
    """⛔ Một nguồn tin mới hỏng không được làm cổng CHẶT HƠN trước.

    Đó là cách một cải tiến biến thành một sự cố: thêm một phép hỏi, phép hỏi
    trục trặc, và cả cổng đóng lại vì một thứ trước đây nó không cần biết.
    """
    from llm_gateway.trong_tai import TrongTai

    def no():
        raise RuntimeError("ComfyUI im")

    px = TrongTai(ram_trong_toi_thieu_gb=0.0, dem_python_gpu=lambda: 1,
                  tai_gpu=lambda: 95, ram_trong_gb=lambda: 100.0,
                  model_cua_ta_dang_chay=lambda: True,
                  ho_kia_dang_ve=no).phan_xu()
    assert px.ban is False, "hoi hang doi hong ma lai chan — chat hon truoc"


def test_model_ta_CHUA_nap_thi_ComfyUI_ve_van_ban_nhu_cu():
    px = _trong_tai(so_python=1, tai=95, model_cua_ta=False, comfy_ve=True).phan_xu()
    assert px.ban is True
    assert "nap model bay gio se de len nhau" in px.ly_do
