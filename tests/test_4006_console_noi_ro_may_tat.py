"""Console hỏng vì máy không chạy ⛔ không được nói giống console hỏng thật.

🔴 Đo 25/09: chủ dự án bấm "Kết nối lại" trên console. Proxmox ghi
   `vncproxy Failed to run` (ba lần cho VM 208, hai lần cho 204) và trang trả
   *"Không mở được console lúc này. Thử lại sau ít phút."*

   Câu đó **đúng về sự việc** và **sai về nguyên nhân**: máy đang tắt từ 17 giờ
   trước, "thử lại sau ít phút" sẽ không bao giờ đúng. Nó đẩy người đọc đi tìm
   lỗi ở console — đúng khuôn *hai trạng thái gộp thành một thông điệp*.

⚠️ Và phép đo phân biệt chỉ chạy **khi đã có lỗi**: đường bình thường ⛔ không
   được tốn thêm một lời gọi Proxmox cho một câu chỉ dùng lúc hỏng.
"""


def test_may_dang_tat_thi_cau_noi_ro_va_chi_viec_can_lam():
    from apps.vps import routes

    cau = routes._cau_console_hong(dien="tat")
    thap = str(cau).lower()
    assert "tắt" in thap
    assert "bật" in thap, "phai noi viec khach can lam, khong chi noi viec hong"
    assert "thử lại sau" not in thap, "cau nay sai huong khi may dang tat"


def test_may_dang_chay_ma_console_hong_thi_van_la_loi_console():
    from apps.vps import routes

    assert "thử lại sau" in str(routes._cau_console_hong(dien="chay")).lower()


def test_KHONG_doc_duoc_dien_thi_KHONG_doan():
    """⛔ `khong_ro` là một lần hỏi thất bại. Nói "máy đang tắt" lúc đó là bịa."""
    from apps.vps import routes

    cau = str(routes._cau_console_hong(dien="khong_ro")).lower()
    assert "tắt" not in cau
    assert "thử lại sau" in cau


def test_duong_BINH_THUONG_khong_do_dien():
    """⛔ Bánh cóc: phép đo chẩn đoán ⛔ không được nằm trên đường chạy tốt."""
    import ast
    import pathlib

    nguon = pathlib.Path("apps/vps/routes.py").read_text(encoding="utf-8")
    cay = ast.parse(nguon)
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "trang_console")
    # Moi loi goi `_cau_console_hong` phai nam TRONG mot khoi `except`.
    trong_except = {id(n) for h in ast.walk(ham) if isinstance(h, ast.ExceptHandler)
                    for n in ast.walk(h)}
    goi = [n for n in ast.walk(ham) if isinstance(n, ast.Call)
           and isinstance(n.func, ast.Name) and n.func.id == "_cau_console_hong"]
    assert goi, "trang console chua dung cau phan biet"
    assert all(id(n) in trong_except for n in goi)
