"""Service C-CLOUD — mọi đường đều phải đòi khoá, và job_id không được đoán ra.

⛔ Hai lỗ này **nhân nhau**: `job_id` đoán được cộng với đường tải không đòi khoá
   nghĩa là tải được video của người khác mà **không cần khoá nào**. Vá một cái
   thôi vẫn còn đường vào.
"""
from __future__ import annotations

import ast
import importlib.util
import pathlib

_TEP = (pathlib.Path(__file__).parent.parent / "tools" / "wangp"
        / "dich_vu_ccloud.py")


def _cay() -> ast.Module:
    return ast.parse(_TEP.read_text(encoding="utf-8"))


def _handler() -> dict[str, ast.FunctionDef]:
    ra = {}
    for n in ast.walk(_cay()):
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for d in n.decorator_list:
            if (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                    and d.func.attr in ("get", "post")):
                ra[n.name] = n
    return ra


def test_MOI_duong_deu_doi_khoa_tru_health():
    """`/health` được để ngỏ có chủ đích — nó chỉ nói máy sống và chạy bản nào."""
    thieu = []
    for ten, n in _handler().items():
        if ten == "health":
            continue
        if "_kiem_khoa" not in ast.unparse(n):
            thieu.append(ten)
    assert not thieu, f"đường không đòi khoá: {thieu}"


def test_ba_duong_DOC_cung_phai_doi_khoa():
    """Đường đọc để rò dữ liệu; đường ghi để phá. Cả hai đều cần khoá."""
    h = _handler()
    for ten in ("progress", "result", "tai_ve"):
        assert ten in h, f"thiếu handler {ten}"
        assert "_kiem_khoa" in ast.unparse(h[ten]), f"{ten} không đòi khoá"


def test_job_id_sinh_bang_CSPRNG_chu_khong_bang_dong_ho():
    """`f\"j{int(time.time()*1000)}{len(_JOB)}\"` đoán ra được trong vài lượt thử."""
    ma = _TEP.read_text(encoding="utf-8")
    assert "secrets.token_urlsafe" in ma, "job_id phải sinh bằng CSPRNG"
    assert "time.time() * 1000" not in ma, "còn dấu vết id theo đồng hồ"


def test_so_khop_khoa_khong_ro_ri_qua_thoi_gian():
    ma = _TEP.read_text(encoding="utf-8")
    assert "compare_digest" in ma


def test_job_id_du_dai_de_khong_do_duoc():
    """Nạp thật module và sinh id — đối chứng, không chỉ đọc mã."""
    spec = importlib.util.spec_from_file_location("_dvcc", _TEP)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    ids = {m.sinh_job_id() for _ in range(200)}
    assert len(ids) == 200, "id bị trùng"
    for i in ids:
        assert len(i) >= 20, f"id quá ngắn: {i!r}"


# ── nạp model: phải xong TRƯỚC khi có người gửi việc ──────────────────────────


def test_ham_nong_chay_luc_KHOI_DONG_chu_khong_luc_submit():
    """Nạp model lười làm hỏng theo ba đường cùng lúc.

    1. người dùng ĐẦU TIÊN trả toàn bộ độ trễ nạp model;
    2. proxy RunPod (Cloudflare) có trần thời gian riêng ⇒ nâng timeout phía
       client **không** cứu được, yêu cầu chết ở giữa đường;
    3. `/health` đã biết sự thật (`san_sang`) mà không ai dùng.

    Đo 06/09: `POST /submit` timeout ở 60 giây, và log phía dịch vụ **không có
    dòng nào** cho `/submit` — uvicorn chỉ ghi khi phản hồi đã gửi, nên phía
    máy chủ trông như chưa từng nhận gì.
    """
    ma = _TEP.read_text(encoding="utf-8")
    assert 'on_event("startup")' in ma or "lifespan" in ma, (
        "không có móc khởi động — model sẽ lại nạp lười ở /submit"
    )
    assert "_ham_nong_nen" in ma


def test_submit_TU_CHOI_NGAY_khi_chua_am_chu_khong_treo():
    """503 + `Retry-After` nói rõ 'chưa sẵn sàng'.

    ⛔ Một yêu cầu treo tới khi proxy cắt là thất bại **không phân biệt được**
       với máy chết: LTT không biết nên thử lại hay báo hỏng.
    """
    import ast

    n = _handler()["submit"]
    than = ast.unparse(n)
    assert "503" in than, "/submit không trả 503 khi phiên chưa sẵn sàng"
    assert "Retry-After" in than
    # phai kiem TRUOC khi goi _lay_phien, khong phai sau
    assert than.index("503") < than.index("_lay_phien"), (
        "kiểm sẵn-sàng phải nằm TRƯỚC lời gọi nạp model"
    )


# ── `xong`: co bao ket thuc, them 07/09 cung `F1` ─────────────────────────

def test_cau_noi_dat_co_xong_khi_luong_su_kien_dong():
    """🔑 Căn cứ ở thượng nguồn, không phải phỏng đoán: `shared/api.py:379`
    cho thấy `iter()` chỉ `break` khi `self._closed.is_set()`; hết giờ thì nó
    `continue`. Nên **thoát khỏi vòng `for` nghĩa là job đã xong**.

    ⭐ Vì sao cần: trước đó `/progress` không có cách nào nói "xong", nên phía
       LTT phải gọi `/result` — vốn **chặn-chờ ~20 phút** — chỉ để biết. Và nó
       chết vì timeout socket 30 giây (`F1`). Một cờ boolean ở đây đổi một cuộc
       gọi hai mươi phút thành một cuộc gọi vài mili-giây.
    """
    import ast
    import pathlib

    goc = pathlib.Path(__file__).resolve().parents[1]
    ma = (goc / "tools" / "wangp" / "dich_vu_ccloud.py").read_text(encoding="utf-8")
    cay = ast.parse(ma)

    # Co dat trong `finally` cua ham theo doi — tuc CHAC CHAN chay khi vong ket
    # thuc, ke ca khi co ngoai le.
    co_finally = False
    for n in ast.walk(cay):
        if isinstance(n, ast.Try) and n.finalbody:
            doan = ast.unparse(ast.Module(body=n.finalbody, type_ignores=[]))
            if "'xong'" in doan or '"xong"' in doan:
                co_finally = True
    assert co_finally, "co `xong` khong nam trong `finally` — mot ngoai le se nuot no"


def test_progress_co_NGUON_THU_HAI_cho_xong():
    """Một sự thật quan trọng nên có hai nguồn độc lập: luồng theo dõi đặt cờ,
    và `/progress` hỏi thẳng `events.closed`. Thiếu nguồn thứ hai thì một luồng
    theo dõi chết sớm sẽ làm job treo vô hạn ở phía LTT."""
    import pathlib

    goc = pathlib.Path(__file__).resolve().parents[1]
    ma = (goc / "tools" / "wangp" / "dich_vu_ccloud.py").read_text(encoding="utf-8")
    than = ma.split('@app.get("/progress/{job_id}")', 1)[1].split("@app.", 1)[0]
    assert "closed" in than, "/progress khong hoi thang trang thai luong su kien"
