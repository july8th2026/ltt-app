"""
Nhường card giữa LLM và model ảnh — bốn nhánh, và mỗi nhánh một cách hỏng thật.

🔴 Máy B có **một** card 24.576 MB. Qwen thường trú 19.237 MB, HiDream đỉnh
   18.450 MB. Hai model không bao giờ cùng lúc được, nên swap không phải tối ưu
   hoá — nó là **chế độ vận hành duy nhất**.

⭐ Bốn nhánh, viết theo đúng thứ tự thiệt hại giảm dần:

     1. đang TÍNH thì KHÔNG đuổi — đuổi là cắt ngang câu trả lời của khách;
     2. chỉ GIỮ bộ nhớ thì đuổi được — không ai thiệt;
     3. lấy lại được thì đừng báo bận — báo bận là khoá chết cả đường ảnh;
     4. không lấy lại được thì báo bận — và đó là câu trả lời đúng.

⛔ Cả bốn đo được **không cần GPU**: mọi nguồn tín hiệu đều tiêm được. Một phép
   kiểm đòi GPU là một phép kiểm sẽ bị tắt.
"""
from __future__ import annotations

import pytest

from render_gateway import busy as B
from render_gateway import nhuong_card as N


HO_LLM = N.HoDung(ten="llm", duong_nha="http://127.0.0.1:8280/unload")
HO_VIDEO = N.HoDung(ten="video")            # chỉ chờ được


def _xin(*, vram, dang_tinh=None, ho=(HO_LLM,), han=3.0, **kw):
    """Gọi `xin_card` với đồng hồ giả — không ngủ thật một giây nào."""
    dong_ho = {"t": 0.0}
    doc = iter(vram) if isinstance(vram, list) else None

    def _vram():
        return next(doc) if doc is not None else vram

    da_goi = []
    return N.xin_card(
        ho_khac=ho, doc_vram=_vram,
        goi_nha=lambda d: (da_goi.append(d), True)[1],
        dang_tinh=dang_tinh, han_giay=han, nhip_giay=0.1,
        now=lambda: dong_ho["t"],
        ngu=lambda s: dong_ho.__setitem__("t", dong_ho["t"] + s),
        **kw), da_goi


# ── Nhánh 1: đang TÍNH thì không đuổi ──────────────────────────────────────

def test_ho_dang_tinh_thi_KHONG_goi_unload():
    """⛔ Đây là nhánh đắt nhất, và nó bảo vệ một thứ khách nhìn thấy.

    `llama-swap` **giết một lượt đang chạy** để nhả model — đo 03/09/2026 và ghi
    trong `llama-swap.yaml`. Lượt bị giết chỉ nhận `ConnectionReset`, không lỗi
    nào nói vì sao. Với khách ChatLTT đó là câu trả lời đang chảy **biến mất giữa
    chừng**, và nó trông y hệt một lần OOM.
    """
    px, da_goi = _xin(vram=20_000, dang_tinh=lambda: True)
    assert px.duoc is False
    assert da_goi == [], "da goi /unload trong luc ho kia DANG TINH"
    assert "DANG TINH" in px.ly_do


def test_ho_dang_tinh_roi_XONG_thi_di_tiep_ma_khong_duoi():
    """Nó tự xong và tự nhả ⇒ đi luôn, không cần đuổi ai."""
    lan = {"n": 0}

    def dang_tinh():
        lan["n"] += 1
        return lan["n"] <= 2          # bận hai nhịp rồi rảnh

    px, da_goi = _xin(vram=[20_000, 20_000, 1_200], dang_tinh=dang_tinh)
    assert px.duoc is True
    assert da_goi == [], "khong duoc duoi ai khi card tu trong ra"


def test_khong_do_duoc_dang_tinh_thi_CHO_chu_khong_duoi():
    """⛔ "Không biết" ở đây phải xử như "khoan đã", ngược với nhánh VRAM.

    Hai chỗ, hai hướng, và ngược nhau có chủ ý: đọc VRAM hỏng ⇒ **từ chối** (ta
    sắp tiêu GPU và tiêu tiền khách, chạy mù là tạo ra sự cố im lặng); đo "đang
    tính" hỏng ⇒ **chờ** (ta sắp phá việc người khác).
    """
    def no():
        raise RuntimeError("nvidia-smi im")

    px, da_goi = _xin(vram=20_000, dang_tinh=no)
    assert px.duoc is False and da_goi == []


# ── Nhánh 2: chỉ GIỮ bộ nhớ thì đuổi được ──────────────────────────────────

def test_ho_chi_giu_bo_nho_thi_duoi_va_di_tiep():
    px, da_goi = _xin(vram=[20_000, 20_000, 1_500], dang_tinh=lambda: False)
    assert px.duoc is True
    assert da_goi == [HO_LLM.duong_nha], "phai bao dung ho bao-duoc nha"
    assert px.da_bao_nha == ("llm",)


def test_ho_chi_cho_duoc_thi_KHONG_BAO_GIO_bi_bao_nha():
    """Dự án video không có endpoint nhả — đuổi nó là phá việc của người khác."""
    px, da_goi = _xin(vram=20_000, dang_tinh=lambda: False, ho=(HO_VIDEO,))
    assert da_goi == []
    assert px.duoc is False, "card van day thi khong duoc cho qua"


def test_card_da_trong_thi_khong_duoi_ai_va_khong_hoi_gi():
    """Nhánh thường gặp nhất: một lô ảnh liên tiếp không được đuổi ai."""
    goi_dang_tinh = {"n": 0}

    def dem():
        goi_dang_tinh["n"] += 1
        return False

    px, da_goi = _xin(vram=1_200, dang_tinh=dem)
    assert px.duoc is True and da_goi == []
    assert goi_dang_tinh["n"] == 0, "card trong roi ma van di hoi ai do dang tinh"


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
