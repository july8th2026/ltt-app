"""dual-model 6.3 — sáu bộ dò báo động của `tools/soi_cong_llm.py`.

Dải **1200–1249** của chương trình Multi-Job / LTT LLM dual-model.

═══════════════════════════════════════════════════════════════════════════
 LUẬT CỦA TỆP NÀY: MỖI BÁO ĐỘNG HAI CA, KHÔNG BAO GIỜ MỘT
═══════════════════════════════════════════════════════════════════════════

Mỗi bộ dò có **một ca kêu** và **một ca IM TRÊN ĐẦU VÀO LÀNH**. Lý do không
phải "cho đủ bộ": một bộ dò kêu **mọi lúc** và một bộ dò **không bao giờ** kêu
đều qua được một phép kiểm một chiều, và cả hai đều vô dụng. Cái sau hỏng âm
thầm; cái trước ồn tới mức người ta tắt kênh cảnh báo, rồi lượt kêu thật rơi
vào hư không.

🔴 VÀ MỘT BÁO ĐỘNG TRONG SỐ NÀY TỪNG ĐƯỢC VIẾT SAI TRONG CHÍNH KẾ HOẠCH.
   Plan ghi *"`Shared Usage > 0`"*. §G1 của `docs/ltt_llm_dual/10_BENCHMARK_P3.md`
   đã bác nó bằng một đối chứng: **cấu hình đang phục vụ khách** cũng cho
   526–568 MiB qua đúng bộ đếm ấy. Ngưỡng `> 0` sẽ kêu mỗi lượt thăm dò, mãi
   mãi. `test_bao_dong_shared_im_o_cau_hinh_lanh_da_do` là phép kiểm ghim điều
   đó: nó nạp đúng con số của cấu hình đang chạy và đòi bộ dò **im**.
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parents[1]


def _nap():
    """Nạp `tools/soi_cong_llm.py` như một module (thư mục `tools/` không phải gói)."""
    duong = GOC / "tools" / "soi_cong_llm.py"
    spec = importlib.util.spec_from_file_location("soi_cong_llm_6_3", duong)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def soi():
    return _nap()


def _ma(canh):
    return sorted(c["ma"] for c in canh)


def _health(*, san38=0, san35=700, trong38=3000, trong35=3000):
    """`/health` tối giản nhưng ĐÚNG HÌNH DẠNG cổng đang trả (Task 4.1/4.2).

    ⚠️ `san38=0` là mặc định **đúng**: `qwen38-api` cố ý không có sàn VRAM ở tầng
       cổng — 3090 do trọng tài residency quản, và hai cơ chế canh một card là
       hai chỗ khai một điều (`llm_gateway/config.py`, `_san_vram`).
    """
    return {
        "gioi_han": {"qwen38-api": {"san_vram_mb": san38},
                     "qwen35-api": {"san_vram_mb": san35}},
        "gpu": {"theo_vai": {
            "ltt38": {"uuid": "GPU-38", "vram_trong_mb": trong38},
            "ltt35": {"uuid": "GPU-35", "vram_trong_mb": trong35}}},
    }


# ══════════════════════════════════════════════════════════════════════════
#  1. VRAM trống dưới sàn — THEO UUID
# ══════════════════════════════════════════════════════════════════════════

def test_vram_duoi_san_thi_keu(soi):
    h = _health(trong35=100)
    canh = soi.bao_dong_vram(h)
    assert _ma(canh) == ["vram_trong_duoi_san"]
    assert canh[0]["model"] == "qwen35-api"
    assert canh[0]["uuid"] == "GPU-35"          # 🔴 số của ĐÚNG card
    assert canh[0]["muc"] == soi.MUC_LOI


def test_vram_tren_san_thi_im(soi):
    """Đối chứng: cùng bộ dò, đầu vào lành ⇒ danh sách rỗng."""
    assert soi.bao_dong_vram(_health(trong35=3000)) == []


def test_card_kia_thap_khong_lam_model_nay_keu(soi):
    """🔴 Số của card sai còn tệ hơn không có số nào.

    3090 trống 100 MiB là chuyện của 3090. `qwen35-api` sống trên 5060 Ti và nó
    vẫn rộng — một bộ dò đọc "VRAM trống" như một con số toàn cục sẽ kêu ở đây,
    và đó đúng là khuyết tật đã phải sửa ở ba tệp ngày 12/09.
    """
    assert soi.bao_dong_vram(_health(trong38=100, trong35=3000)) == []


def test_khong_doc_duoc_card_thi_noi_ra_chu_khong_coi_la_lanh(soi):
    h = _health()
    h["gpu"]["theo_vai"]["ltt35"] = {"ly_do": "khong doc duoc danh tinh"}
    canh = soi.bao_dong_vram(h)
    assert _ma(canh) == ["vram_khong_do_duoc"]
    assert canh[0]["muc"] == soi.MUC_CANH_BAO


def test_model_khong_co_san_thi_khong_keu_va_khong_gia_vo_da_kiem(soi):
    """`qwen38-api` không có sàn ở tầng cổng ⇒ bộ dò bỏ qua nó hoàn toàn."""
    h = _health(san38=0, trong38=1)
    assert [c for c in soi.bao_dong_vram(h) if c["model"] == "qwen38-api"] == []


# ══════════════════════════════════════════════════════════════════════════
#  2. Tràn WDDM (`Shared Usage`) — ngưỡng ĐO, không phải `> 0`
# ══════════════════════════════════════════════════════════════════════════

def test_bao_dong_shared_im_o_cau_hinh_lanh_da_do(soi):
    """🔴 GHIM PHÉP ĐỐI CHỨNG CỦA §G1: cấu hình ĐANG PHỤC VỤ KHÁCH phải IM.

    Nếu ai đó đổi ngưỡng về `> 0` như plan viết, ca này đỏ ngay — và nó đỏ với
    đúng con số mà máy B đo được ở cấu hình chốt, không phải một con số bịa.
    """
    for model, san in soi.SAN_SHARED_MIB.items():
        assert soi.bao_dong_shared(model, san) == [], model
        # Và cả dải sàn đo được ở §G1 (thấp hơn sàn ghim) cũng phải im.
        assert soi.bao_dong_shared(model, san - 42) == [], model


def test_bao_dong_shared_keu_khi_vuot_san_cong_bien(soi):
    model = "qwen38-api"
    san = soi.SAN_SHARED_MIB[model]
    canh = soi.bao_dong_shared(model, san + soi.BIEN_SHARED_MIB + 1)
    assert _ma(canh) == ["tran_wddm"]
    assert canh[0]["tran_mib"] == soi.BIEN_SHARED_MIB + 1


def test_bien_shared_nam_giua_hai_moc_da_do(soi):
    """Biên phải > độ trải của dải sàn LÀNH và < lần tràn NHỎ NHẤT đã quan sát.

    Hai mốc lấy ở §G1/§G1b: dải sàn lành 526–568 (trải 42 MiB); lần tràn nhỏ
    nhất quan sát được là +138 MiB trên sàn. Một biên nằm ngoài khoảng ấy hoặc
    kêu vì nhiễu của chính bộ đếm, hoặc bỏ lọt lần tràn nhỏ nhất từng thấy.

    ⚠️ Hai mốc này là **số đo của §G1**, và chúng nằm ở đây vì đây là nơi duy
       nhất trong mã kiểm chúng; chúng không phải một cấu hình ai đó chỉnh được.
    """
    assert 42 < soi.BIEN_SHARED_MIB < 138


def test_model_chua_do_san_thi_khong_ket_luan(soi):
    canh = soi.bao_dong_shared("model-la", 9_999)
    assert _ma(canh) == ["shared_chua_do_san"]
    assert canh[0]["muc"] == soi.MUC_CANH_BAO


def test_shared_khong_do_duoc_thi_noi_ra(soi):
    assert _ma(soi.bao_dong_shared("qwen38-api", None)) == ["shared_khong_do_duoc"]


def test_gom_shared_theo_model_quy_ve_dung_card(soi):
    """🔴 Bộ đếm WDDM khoá theo TIẾN TRÌNH; phép quy về card đi qua `gpu_uuid`.

    Đối chứng nằm trong chính dữ liệu: cả hai tiến trình đều tên `llama-server`
    và chỉ khác nhau ở cột UUID. Một bản cộng tất sẽ trả 2.000 cho cả hai model.
    """
    h = _health()
    proc = [(11, "llama-server.exe", 21_000, "GPU-38"),
            (22, "llama-server.exe", 13_000, "GPU-35")]
    shared = {11: 568, 22: 354}
    ra = soi.gom_shared_theo_model(h, proc, shared)
    assert ra == {"qwen38-api": 568, "qwen35-api": 354}
    # …và đúng những con số ấy là cấu hình lành, nên chuỗi đầy đủ phải im.
    assert soi.soi_bao_dong(health=h, shared_mib=ra) == []


# ══════════════════════════════════════════════════════════════════════════
#  3. `requests_deferred`
# ══════════════════════════════════════════════════════════════════════════

_METRICS_LANH = """# HELP llamacpp:requests_deferred Number of deferred requests
# TYPE llamacpp:requests_deferred gauge
llamacpp:requests_processing 1
llamacpp:requests_deferred 0
"""

_METRICS_HOAN = _METRICS_LANH.replace("requests_deferred 0",
                                      "requests_deferred 3")


def test_requests_deferred_duong_thi_keu(soi):
    canh = soi.bao_dong_deferred("qwen38-api", _METRICS_HOAN)
    assert _ma(canh) == ["requests_deferred"]
    assert canh[0]["gia_tri"] == 3.0


def test_requests_deferred_bang_khong_thi_im(soi):
    assert soi.bao_dong_deferred("qwen38-api", _METRICS_LANH) == []


def test_dong_HELP_khong_bi_doc_thanh_so_do(soi):
    """Dòng `# HELP …` chứa đúng tên đo. Đọc nhầm nó là một báo động vĩnh viễn."""
    assert soi.bao_dong_deferred("qwen38-api",
                                 "# HELP llamacpp:requests_deferred 9\n") == []


def test_doi_tien_to_ten_do_van_bat_duoc(soi):
    """Khớp theo **hậu tố**: llama.cpp đã đổi tiền tố giữa các bản."""
    assert _ma(soi.bao_dong_deferred("m", "engine_requests_deferred 2\n")) == [
        "requests_deferred"]


# ══════════════════════════════════════════════════════════════════════════
#  4. Log "Context size has been exceeded"
# ══════════════════════════════════════════════════════════════════════════

def test_log_vuot_ngu_canh_thi_keu(soi):
    dong = ["slot update_slots: id 0 | task 7 | new prompt",
            "srv  send_error: task 7 | Context size has been exceeded."]
    canh = soi.bao_dong_log(dong)
    assert _ma(canh) == ["vuot_ngu_canh"] and canh[0]["so_dong"] == 1


def test_log_binh_thuong_thi_im(soi):
    assert soi.bao_dong_log(["slot released", "prompt done", ""]) == []


# ══════════════════════════════════════════════════════════════════════════
#  5. Trọng tài cư trú ở `LOI_NAP`
# ══════════════════════════════════════════════════════════════════════════

def test_loi_nap_thi_keu_ngay_lan_dau(soi):
    from platform_core.llm import residency

    canh = soi.bao_dong_residency(residency.LOI_NAP, lan_nap_loi=1)
    assert _ma(canh) == ["residency_loi_nap"] and canh[0]["muc"] == soi.MUC_LOI


def test_moi_trang_thai_binh_thuong_deu_im(soi):
    """Đối chứng vét cạn: **mọi** trạng thái khác `LOI_NAP` phải im.

    Duyệt `residency.TRANG_THAI` chứ không liệt kê tay — thêm một trạng thái mới
    là ca này tự phủ luôn nó.
    """
    from platform_core.llm import residency

    for ten in residency.TRANG_THAI:
        if ten == residency.LOI_NAP:
            continue
        assert soi.bao_dong_residency(ten, lan_nap_loi=0) == [], ten


# ══════════════════════════════════════════════════════════════════════════
#  6. Tiến trình lạ trên UUID 3090
# ══════════════════════════════════════════════════════════════════════════

def test_tien_trinh_la_thi_keu(soi):
    canh = soi.bao_dong_tien_trinh([(9, r"C:\\Games\\miner.exe", 4096)])
    assert _ma(canh) == ["tien_trinh_la_tren_3090"]
    assert canh[0]["tien_trinh"][0]["pid"] == 9


def test_cau_hinh_lanh_cua_3090_thi_im(soi):
    """Đúng hai thứ Task 0.3 đo được trên 3090: engine LLM + ComfyUI (python)."""
    assert soi.bao_dong_tien_trinh([
        (100, r"H:\\LTT_LLM\\llama-server.exe", 21_493),
        (200, r"E:\\AI\\ComfyUI\\python.exe", 224),
    ]) == []


def test_danh_sach_rong_thi_im(soi):
    assert soi.bao_dong_tien_trinh([]) == []


# ══════════════════════════════════════════════════════════════════════════
#  Bộ gộp: im khi mọi đầu vào lành, và KHÔNG bịa ra "lành" khi thiếu dữ liệu
# ══════════════════════════════════════════════════════════════════════════

def test_soi_bao_dong_im_tren_mot_he_lanh(soi):
    from platform_core.llm import residency

    assert soi.soi_bao_dong(
        health=_health(),
        shared_mib=dict(soi.SAN_SHARED_MIB),
        upstream_metrics={"qwen38-api": _METRICS_LANH},
        dong_log=["slot released"],
        residency_trang_thai=residency.LLM,
        tien_trinh_3090=[(1, "llama-server.exe", 21_000)]) == []


def test_soi_bao_dong_gom_du_sau_bo_do(soi):
    from platform_core.llm import residency

    canh = soi.soi_bao_dong(
        health=_health(trong35=10),
        shared_mib={"qwen38-api": soi.SAN_SHARED_MIB["qwen38-api"]
                    + soi.BIEN_SHARED_MIB + 1},
        upstream_metrics={"qwen38-api": _METRICS_HOAN},
        dong_log=["Context size has been exceeded"],
        residency_trang_thai=residency.LOI_NAP,
        tien_trinh_3090=[(9, "miner.exe", 1)])
    assert _ma(canh) == sorted([
        "vram_trong_duoi_san", "tran_wddm", "requests_deferred",
        "vuot_ngu_canh", "residency_loi_nap", "tien_trinh_la_tren_3090"])


def test_khong_co_du_lieu_thi_khong_sinh_ra_bao_dong_lanh(soi):
    """⛔ Danh sách rỗng chỉ nói "không bộ dò nào kêu", KHÔNG nói "lành".

    Ghim bằng chính hình dạng hàm: gọi không đầu vào nào trả về rỗng — nên bên
    gọi buộc phải in ra mình đã đo được gì (và `chay_bao_dong` làm đúng thế).
    """
    assert soi.soi_bao_dong() == []


# ══════════════════════════════════════════════════════════════════════════
#  Phần THU THẬP: bóc stdout của máy B (chưa chạy thật với máy B ở phiên này)
# ══════════════════════════════════════════════════════════════════════════

def test_cat_khuc_va_doc_proc(soi):
    ra = "\n".join([
        soi.NGAN_HEALTH, '{"gioi_han": {}}',
        soi.NGAN_PROC,
        "100, llama-server.exe, 21493, GPU-38",
        "200, python.exe, [N/A], GPU-38",
        soi.NGAN_SHARED, "100=568", "200=0",
    ])
    khuc = soi._cat_khuc(ra)
    proc = soi._doc_proc(khuc[soi.NGAN_PROC])
    # `[N/A]` ⇒ 0 MiB nhưng **giữ dòng**: sự tồn tại của tiến trình là tin chắc
    # chắn, chỉ dung lượng là không biết.
    assert proc == [(100, "llama-server.exe", 21493, "GPU-38"),
                    (200, "python.exe", 0, "GPU-38")]
    assert soi._doc_shared(khuc[soi.NGAN_SHARED]) == {100: 568, 200: 0}


def test_phan_xu_cu_khong_bi_dung_toi(soi):
    """Bánh cóc: lớp phán xử `/health` ↔ `Get-Service` đang chạy theo lịch."""
    assert soi.phan_xu("200", "Running") == (soi.LANH, "lanh")
    assert soi.phan_xu("200", "Stopped") == (soi.LECH, "xanh-gia")
