"""test_393 — bộ kiểm `kiem_truoc_khi_cam.py` phải dùng được TRÊN MỘT MÁY TRẮNG.

Tệp công cụ đó tồn tại để **chép sang máy khác** trước khi cắm Codex. Cái giá
của việc chép đi là: mọi giả định về môi trường đều sai. Nên ba tính chất dưới
đây không phải chuyện phong cách — chúng quyết định tệp có được chạy hay không.

⛔ VÀ MỘT TÍNH CHẤT THỨ TƯ, ĐẮT NHẤT: **mỗi phép đo phải có đối chứng.** Bài học
   của đợt 31/08–01/09 là tám lần một dụng cụ cho kết quả đẹp vì nó không đo gì
   cả. Một bộ kiểm "đường gọi thông" mà không thể báo *không thông* thì tệ hơn
   không có — nó biến một sự cố thành một dấu tích xanh.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

TEP = pathlib.Path(__file__).resolve().parents[1] / "tools" / "kiem_truoc_khi_cam.py"
VAN = TEP.read_text(encoding="utf-8")
CAY = ast.parse(VAN)


# ── 1. Chạy được trên một máy chưa cài gì ───────────────────────────────────

def test_CHI_dung_thu_vien_chuan():
    """Máy đích có thể chưa có `requests`, chưa có kho này, chưa có gì.

    ⛔ Một bộ kiểm đòi `pip install` là một bộ kiểm sẽ không được chạy — người
       ta sẽ bỏ qua nó và cắm thẳng, rồi gặp lỗi ở chỗ khó chẩn đoán hơn.
    """
    chuan = {"argparse", "json", "os", "sys", "time", "urllib", "typing",
             "__future__", "dataclasses", "pathlib", "ssl", "http", "re"}
    ngoai = set()
    for n in ast.walk(CAY):
        if isinstance(n, ast.Import):
            ngoai |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            ngoai.add(n.module.split(".")[0])
    la = ngoai - chuan
    assert not la, f"import ngoai thu vien chuan: {sorted(la)}"


def test_KHONG_phu_thuoc_vao_kho_nay():
    """Nó bị chép đi MỘT MÌNH. Import `platform_core`/`apps` là chép hụt."""
    for cam in ("platform_core", "apps.", "server."):
        assert f"import {cam}" not in VAN and f"from {cam}" not in VAN, (
            f"phu thuoc {cam} — tep nay se vo khi chep sang may khac")


def test_KHONG_goi_dia_chi_noi_bo():
    """Đo ở loopback là đo một thứ khác. `CLAUDE.md` quy tắc 5b đã trả giá:
    trang đẹp ở `127.0.0.1` mà **vỡ với người dùng thật** vì Cloudflare phục vụ
    bản cũ. Máy khách không có loopback của ta."""
    for cam in ("127.0.0.1", "localhost", "192.168."):
        assert cam not in VAN, f"co dia chi noi bo `{cam}` — may khach khong toi duoc"


# ── 2. Nó phải ĐỎ được ──────────────────────────────────────────────────────

def test_moi_phep_do_QUAN_TRONG_deu_co_doi_chung():
    """Ba đối chứng bắt buộc, mỗi cái chặn một kiểu 'xanh vì lý do sai'.

    - khoá SAI phải bị từ chối  → nếu không, "khoá dùng được" đúng tầm thường
    - một lượt gọi thật phải TRỪ TIỀN → nếu không, ta đang đo một đường không
      tính tiền, và mọi kết luận về đường gọi đều vô nghĩa
    - bẫy `Python-urllib` phải còn → nó là thứ khách tự viết sẽ vấp
    """
    for dau in ("doi chung", "CO tru tien", "Python-urllib"):
        assert dau in VAN, f"thieu doi chung: {dau}"

    # 🔴 VÀ ĐỐI CHỨNG KHOÁ SAI PHẢI LÀ MỘT LỜI GỌI THẬT, không phải một nhãn.
    #
    #    Bản đầu của phép kiểm này chỉ tìm chuỗi `"khoa SAI"` trong tệp. Đột
    #    biến cho thấy nó vô dụng: thay cả lời gọi bằng `ma_sai = 401` thì nhãn
    #    vẫn còn, phép kiểm vẫn xanh, và đối chứng đã biến mất.
    #
    # ⭐ Cùng hình dạng với thứ tệp này sinh ra để chống. Nên nay đọc AST và đòi
    #    có ít nhất một lời gọi `_goi` mang một khoá **đã bị sửa** — tức thật sự
    #    hỏi máy chủ bằng một khoá không hợp lệ.
    goi_khoa_sai = []
    for n in ast.walk(CAY):
        if not (isinstance(n, ast.Call) and getattr(n.func, "id", "") == "_goi"):
            continue
        for tham in n.args[1:2]:
            # `a.khoa` tran thi la khoa that; bat ky phep toan nao tren no
            # (noi chuoi, cat bot) deu la mot khoa CO Y lam sai.
            if isinstance(tham, ast.BinOp):
                goi_khoa_sai.append(n.lineno)
    assert goi_khoa_sai, (
        "khong co loi goi nao dung mot khoa DA BI SUA — doi chung 'khoa sai bi "
        "tu choi' chi con la mot nhan, khong con la mot phep do")


def test_DUNG_HAN_khi_doi_chung_tien_truot():
    """Nếu khoá đúng và khoá sai **cùng** được nhận, bộ kiểm phải DỪNG chứ không
    báo đạt — chính nó đang hỏng, và một dụng cụ hỏng nói 'đạt' là ca tệ nhất."""
    assert "DOI CHUNG TRUOT" in VAN
    assert "DUNG doc ket qua duoi day" in VAN


def test_ba_ma_thoat_phan_biet_duoc():
    """0 thông · 1 có mục hỏng · 2 không đo được. Một bộ kiểm luôn trả 0 thì
    không tự động hoá được, và sẽ bị đọc bằng mắt rồi bỏ qua."""
    ma = {n.value.value for n in ast.walk(CAY)
          if isinstance(n, ast.Return) and isinstance(n.value, ast.Constant)
          and isinstance(n.value.value, int)}
    assert {0, 1, 2} <= ma, f"chi thay ma thoat {sorted(ma)}"


# ── 3. Cấu hình nó in ra phải là cấu hình ĐÚNG ──────────────────────────────

def test_cau_hinh_in_ra_khop_hop_dong_that():
    """🔴 Bộ kiểm in ra một `config.toml` để người ta dán vào máy khác. Nếu bốn
    giá trị đó sai thì nó vừa nói "đường gọi thông" vừa phát một cấu hình hỏng —
    và người nhận sẽ tin dòng đầu.

    ⭐ `wire_api = "responses"` là dòng đáng canh nhất: Codex nối `/responses`
       vào `base_url`, nên base phải tận cùng `/api/v1`. Sai bốn ký tự ở đây cho
       một `404` không manh mối nào — đúng cái bẫy `CLI_BAY` đã ghi.
    """
    assert 'base_url = "{API}"' in VAN or "/api/v1" in VAN
    assert 'wire_api = "responses"' in VAN
    assert 'env_key = "LTT_API_KEY"' in VAN
    assert 'model = "ltt_llm"' in VAN


def test_ten_model_khop_ALIAS_that_cua_app():
    """Tên model in ra phải là bí danh công khai app đang khai, không phải một
    chuỗi gõ tay đã trôi."""
    from apps.ltt_llm.features import ALIAS_SANG_ID

    assert 'model = "ltt_llm"' in VAN
    assert "ltt_llm" in ALIAS_SANG_ID


def test_NOI_RO_canh_bao_metadata_cua_Codex():
    """Codex in `Model metadata for ltt_llm not found` ở **mọi** lượt chạy.

    ⛔ Không nói trước thì người cắm sẽ tưởng mình làm sai và đi sửa cấu hình
       đang đúng. Đo 01/09: Codex **không gọi** `/api/v1/models` lần nào, nên
       cảnh báo đó không phải lỗi của khuôn dữ liệu phía ta.
    """
    assert "Model metadata" in VAN
    assert "KHONG goi /api/v1/models" in VAN


@pytest.mark.parametrize("muc", ["Mang va Cloudflare", "Khoa API", "Model",
                                 "/responses", "Tien"])
def test_phu_du_nam_chang_cua_duong_goi(muc):
    """Thiếu một chặng thì bộ kiểm nói 'thông' về một đường nó chưa đi hết."""
    assert muc in VAN
