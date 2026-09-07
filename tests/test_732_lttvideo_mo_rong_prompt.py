"""`A5` — mở rộng mô tả bằng bộ enhancer của WanGP.

Mọi phép kiểm ở đây hỏi một trong hai câu:

  1. Ta có gửi **đúng thứ WanGP đọc** không? (ngữ nghĩa `"T"` / `"TI"`)
  2. Ta có hứa với người dùng thứ máy chưa làm được không?
"""
from __future__ import annotations

import ast
import inspect

from apps.lttvideo import ho_so, jobs, kha_nang


# ── 1. Ngu nghia khoa, doc tu wgp.py ────────────────────────────────────────

def test_chu_gui_T_va_anh_gui_TI():
    """`wgp.py:6561` doc `"I"` de biet co dua ANH vao bo mo rong; `wgp.py:3118`
    tu nang `"I"` thanh `"TI"`. Nen gui thang `"TI"` la gui dung thu se chay."""
    assert ho_so.khoa_mo_rong("chu", bat=True) == "T"
    assert ho_so.khoa_mo_rong("anh", bat=True) == "TI"


def test_tat_thi_tra_ve_dung_gia_tri_XUAT_XUONG():
    """⛔ Tắt phải trả `""` — y hệt hồ sơ WanGP. Nếu nó trả thứ khác thì lượt
    KHÔNG bật mở rộng vẫn đổi hành vi, và không ai biết vì sao video khác đi."""
    for hinh_dang in ("chu", "anh", "video", "khong-co-that"):
        assert ho_so.khoa_mo_rong(hinh_dang, bat=False) == ""
    assert ho_so.MO_RONG_TAT == ""


def test_hinh_dang_la_khong_biet_thi_KHONG_bat_bua():
    """Hình dạng chưa mở (vd `"video"`) mà bật ⇒ vẫn tắt, không đoán một giá trị."""
    assert ho_so.khoa_mo_rong("video", bat=True) == ""


def test_moi_gia_tri_bat_deu_chua_T():
    """Bất biến của WanGP: `"I"` một mình không tồn tại — nó luôn được nâng thành
    `"TI"`. Nên mọi giá trị ta sinh ra khi bật đều phải có `"T"`."""
    for gia_tri in ho_so.MO_RONG_THEO_DAU_VAO.values():
        assert "T" in gia_tri, gia_tri


def test_khoa_nam_trong_danh_sach_nguoi_dung_doi_duoc():
    """`ap_dung` ném lỗi với khoá ngoài danh sách, nên thiếu dòng này thì mọi
    job đều vỡ — nhưng chỉ vỡ khi chạy thật, không phải lúc import."""
    assert "prompt_enhancer" in ho_so.KHOA_NGUOI_DUNG_DOI_DUOC


def test_ho_so_xuat_xuong_van_giu_gia_tri_rong():
    """Ta gửi khoá mỗi lượt, **không** sửa tệp hồ sơ. Tệp hồ sơ là bản chụp của
    WanGP; sửa nó là làm bản chụp ấy nói dối về nguồn của nó."""
    for h in ho_so.liet_ke():
        assert h.doc_tham_so()["prompt_enhancer"] == ""


# ── 2. jobs.py co that su gui khong ─────────────────────────────────────────

def test_jobs_dat_khoa_qua_ho_so_chu_khong_go_tay():
    """⛔ Gõ thẳng `"T"` trong `jobs.py` là tách ngữ nghĩa WanGP ra làm hai bản.
    Đọc AST chứ không quét văn bản — quét văn bản báo động lên chính đoạn giải
    thích nó (`docs/BAY_TRONG_CONG_CHAT_LUONG.md`)."""
    cay = ast.parse(inspect.getsource(jobs))
    goi = {f"{n.func.value.id}.{n.func.attr}"
           for n in ast.walk(cay)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
           and isinstance(n.func.value, ast.Name)}
    assert "ho_so.khoa_mo_rong" in goi


def test_jobs_KHONG_chua_gia_tri_T_hay_TI_go_tay():
    """Đối chứng chiều ngược: bản đúng phải KHÔNG có hằng chuỗi `"TI"` nào."""
    cay = ast.parse(inspect.getsource(jobs))
    hang = {n.value for n in ast.walk(cay)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert "TI" not in hang


# ── 3. Khong hua thu may chua lam duoc ──────────────────────────────────────

def test_nang_luc_CHUA_mo_cho_toi_khi_co_mot_luot_chay_that():
    """🔴 Đây là phép kiểm quan trọng nhất tệp này, và nó **cố ý** chốt trạng
    thái ĐÓNG.

    Trọng số `Qwen3.5-9B` chưa từng tải và chưa từng chạy trên ngăn xếp
    py3.11/cu130. Bật ô tick khi C-CLOUD còn `enhancer_enabled = 5` + `gguf`
    nghĩa là WanGP bỏ qua khoá ấy trong im lặng (`wgp.py:6853` cần
    `enhancer_enabled > 0` **và** `enhancer_mode == 0`) — người dùng tick, chờ
    hai mươi phút, và nhận đúng video như khi không tick.

    ⇒ Mở năng lực này là một hành động CÓ CHỦ Ý: chạy
      `tools/wangp/cau_hinh_enhancer.py --ghi`, sinh thật một video có bật, rồi
      mới sửa dòng dưới đây cùng `kha_nang.NANG_LUC_MO`.
    """
    assert "mo_rong_prompt" not in kha_nang.NANG_LUC_MO
    assert not kha_nang.duoc_phep("mo_rong_prompt", vai="admin")


def test_co_ten_than_thien_san_cho_ngay_mo():
    """Lý do từ chối phải đọc được, không rò tên nội bộ."""
    assert kha_nang.ten_than_thien("mo_rong_prompt") != "tính năng này"


def test_route_KHONG_tin_o_tick_cua_bieu_mau():
    """Trình duyệt gửi được trường bất kỳ. Nhánh nhận `mo_rong_prompt` phải hỏi
    lại `kha_nang`, nếu không thì năng lực đang đóng vẫn vào tới worker."""
    from apps.lttvideo import routes

    cay = ast.parse(inspect.getsource(routes.tao_video))
    for n in ast.walk(cay):
        if (isinstance(n, ast.If)
                and any(isinstance(c, ast.Name) and c.id == "mo_rong_prompt"
                        for c in ast.walk(n.test))):
            goi = {c.func.attr for c in ast.walk(n.test)
                   if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)}
            assert "duoc_phep" in goi, "nhanh nhan o tick ma khong hoi kha_nang"
            return
    raise AssertionError("khong tim thay nhanh xu ly `mo_rong_prompt`")
