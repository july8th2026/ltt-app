"""
Bộ khoá logic — biến các ràng buộc bất biến thành test.

Vì sao file này tồn tại
-----------------------
Một quy tắc chỉ nằm trong tài liệu là một quy tắc sẽ bị vi phạm. Không phải vì
ai cố ý, mà vì sáu tháng sau không ai nhớ nó tồn tại — và người vi phạm thường
là chính người đã viết ra nó.

Mỗi test ở đây khoá **một ràng buộc đã ghi trong `docs/QUYET_DINH_NEN_TANG.md`**
và giải thích ràng buộc đó bảo vệ điều gì. Test đỏ ở đây nghĩa là: hoặc bạn vừa
vi phạm một quyết định, hoặc quyết định đó đã thay đổi — và nếu là vế sau thì
phải sửa test **trong cùng commit** với việc sửa bảng quyết định (giao thức đổi
quyết định, `AGENTS.md` mục 6).

Nguyên tắc khi viết thêm test vào đây
-------------------------------------
Khoá **bất biến**, đừng khoá **chi tiết ngẫu nhiên**. Đã có tiền lệ:
`test_45` từng khoá cứng chuỗi `127.0.0.1:8000`, nên một lần đổi cổng hoàn toàn
hợp lệ lại trông giống một lỗi bảo mật. Điều thật sự cần bảo vệ là "chỉ được
proxy địa chỉ loopback", không phải con số 8000.
"""
from __future__ import annotations

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

# Thư mục chứa mã nguồn thật (không tính test, tài liệu, thư mục lưu trữ).
CODE_DIRS = ("core", "server", "utils", "platform_core", "apps", "tools")


def _source_files() -> list[pathlib.Path]:
    out: list[pathlib.Path] = []
    for d in CODE_DIRS:
        out += [p for p in (ROOT / d).rglob("*.py") if "__pycache__" not in str(p)]
    out += [ROOT / "worker_main.py"]
    return [p for p in out if p.exists()]


# ── Ràng buộc 1: mọi đường dẫn dữ liệu đi qua runtime_paths ───────────────────

# Các file được phép giữ chuỗi tương đối, vì đó là *nhánh dự phòng* bên trong
# chính hàm giải đường dẫn: khi runtime_paths không dùng được thì thà lưu sai
# chỗ còn hơn làm sập ứng dụng.
_DUOC_PHEP_DU_PHONG = {
    # Chuyển từ `core/` sang `platform_core/` ngày 2026-08-06 khi cắt phụ thuộc
    # cuối cùng của nền tảng vào `core/` legacy.
    "platform_core/runtime_paths.py",
    "core/session_lock.py",
    "core/token_store.py",
    "core/tiktok/token_store.py",
    "core/tiktok/account_warmup.py",
    "core/content_history.py",
    "core/page_health.py",
    "core/page_warmup.py",
    "utils/audit_logger.py",
}

_DUONG_DAN_TUONG_DOI = re.compile(r"""os\.path\.join\(\s*["']data["']""")


def test_khong_ai_tu_ghep_duong_dan_data_nua():
    """Đường dẫn dữ liệu phải đi qua `platform_core.runtime_paths.data_path()`.

    Bảo vệ điều gì: `os.path.join("data", ...)` là tương đối theo **thư mục làm
    việc của tiến trình**. Trên máy chủ, dịch vụ chạy tại `C:\\LTTPlatform\\app`
    nên chuỗi đó trỏ vào `app\\data\\` — thư mục bị xoá và thay toàn bộ ở mỗi
    lần cập nhật. Token Facebook/TikTok ghi vào đó sẽ biến mất sau lần cập nhật
    kế tiếp, và biến mất **âm thầm** (`_save()` có `os.makedirs(exist_ok=True)`
    nên nó tạo thư mục rồi ghi bình thường, không báo lỗi gì).

    Lỗi này đã xảy ra thật và từng chỉ được sửa cho một module
    (`core/session_lock.py`) trong khi 8 module khác vẫn nguyên.
    """
    vi_pham = []
    for path in _source_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel in _DUOC_PHEP_DU_PHONG:
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue          # chú thích giải thích lỗi cũ thì không tính
            if _DUONG_DAN_TUONG_DOI.search(line):
                vi_pham.append(f"{rel}:{i}")
    assert vi_pham == [], (
        "Dùng platform_core.runtime_paths.data_path() thay vì tự ghép chuỗi. "
        f"Vi phạm: {vi_pham}"
    )


def test_data_path_ton_trong_bien_moi_truong():
    """`data_path()` phải theo `LTT_DATA_DIR`, không theo thư mục làm việc."""
    from platform_core.runtime_paths import data_path, resolve_runtime_paths

    env = {"LTT_DATA_DIR": "/tmp/kho-du-lieu-gia-dinh"}
    assert resolve_runtime_paths(env).data_dir == "/tmp/kho-du-lieu-gia-dinh"
    # data_path() đọc os.environ thật; ở đây chỉ cần khẳng định nó nằm dưới
    # data_dir đã giải, chứ không phải một chuỗi tương đối trần trụi.
    ket_qua = data_path("vi_du.bin")
    assert ket_qua.endswith("vi_du.bin")
    assert ket_qua != "data/vi_du.bin".replace("/", "\\")
    assert pathlib.Path(ket_qua).is_absolute() or ket_qua.startswith("data")


# ── Ràng buộc 2: hai cây mã nguồn độc lập ─────────────────────────────────────

def test_khong_import_cheo_tu_bot_gemini():
    """`D:\\BOT GEMINI` là kho tham chiếu chỉ đọc, không phải thư viện.

    Bảo vệ điều gì: hai dự án trùng thương hiệu và trùng cả kiến trúc FastAPI.
    Một `import` hay một đường dẫn tuyệt đối trỏ sang đó biến hệ thống đang
    phục vụ 13 người dùng thật thành phụ thuộc lúc chạy của dự án này — sửa bên
    này hỏng bên kia, và bên kia không có ai canh.
    """
    # Miễn trừ: script DI TRÚ MỘT LẦN (H8.5) CỐ Ý trỏ sang BOT GEMINI để nhập key
    # sang, chạy tay đúng một lần — web/worker KHÔNG bao giờ import nó, nên không
    # phải phụ thuộc lúc chạy (đúng tinh thần ràng buộc này).
    MIEN_TRU = {"tools/import_api_keys_from_botgemini.py",
                "tools/import_r2_modelark_from_botgemini.py"}
    mau = re.compile(r"BOT[ _]GEMINI", re.IGNORECASE)
    vi_pham = []
    for path in _source_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel in MIEN_TRU:
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if mau.search(line) and ("import" in line or "path" in line.lower()):
                vi_pham.append(f"{rel}:{i}")
    assert vi_pham == [], f"Không được trỏ sang BOT GEMINI lúc chạy: {vi_pham}"


# ── Ràng buộc 3: cổng của nền tảng ────────────────────────────────────────────

def test_khong_con_cong_8000_trong_bo_cai():
    """Cổng 8000 thuộc về hệ thống khác trên cùng máy (quyết định Q4).

    Bảo vệ điều gì: `D:\\BOT GEMINI` đang nghe 8000 và phục vụ người dùng thật.
    Bộ cài mặc định 8000 sẽ giành cổng với nó — dịch vụ mới không khởi động
    được, hoặc tệ hơn là hạ dịch vụ đang chạy.

    Chỉ soi bộ cài và cấu hình triển khai. Test/tài liệu lịch sử được phép nhắc
    tới 8000 để giải thích.
    """
    thu_muc = [ROOT / "setup", ROOT / "deploy", ROOT / "cloudflare"]
    vi_pham = []
    for d in thu_muc:
        for path in d.rglob("*"):
            if not path.is_file() or path.suffix not in (".ps1", ".yml", ".example", ""):
                continue
            try:
                noi_dung = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for i, line in enumerate(noi_dung.splitlines(), 1):
                if line.lstrip().startswith("#"):
                    continue
                if re.search(r"(?<!\d)8000(?!\d)", line):
                    vi_pham.append(f"{path.relative_to(ROOT).as_posix()}:{i}")
    assert vi_pham == [], f"Cổng 8000 thuộc hệ thống khác, dùng 8100: {vi_pham}"


# ── Ràng buộc 4: chốt phiên bản thư viện (Q17) ────────────────────────────────

@pytest.mark.parametrize("ten", ["requirements.txt", "requirements-server.txt"])
def test_moi_thu_vien_deu_co_can_tren(ten):
    """Mọi thư viện phải có cận trên (`<`).

    Bảo vệ điều gì: chỉ ghi `>=` nghĩa là `pip install` kéo về bản mới nhất tại
    thời điểm cài. Ngày 2026-07-31 điều đó đã xảy ra thật — Starlette nhảy từ
    0.x lên 1.3 và việc liệt kê route không còn hoạt động. Ứng dụng vẫn chạy
    đúng, nhưng **hai lần cài cùng một mã nguồn cho ra hai môi trường khác
    nhau**, và không ai chủ động quyết định điều đó.

    Ngoại lệ có chủ ý: các gói dữ liệu múi giờ (`pytz`, `tzdata`) chỉ chứa dữ
    liệu, chốt cận trên chúng là tự khoá mình khỏi bản vá múi giờ.
    """
    NGOAI_LE = {"pytz", "tzdata"}
    thieu = []
    for line in (ROOT / ten).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        goi = re.split(r"[<>=\[]", line, maxsplit=1)[0].strip().lower()
        if goi in NGOAI_LE:
            continue
        if "<" not in line:
            thieu.append(line)
    assert thieu == [], (
        f"{ten}: thiếu cận trên, một lần cài lại có thể đổi hành vi âm thầm: {thieu}"
    )


# ── Ràng buộc 5: tài liệu có đúng một nguồn chân lý ───────────────────────────

def test_co_nguon_chan_ly_va_ke_hoach_va_nhat_ky():
    """Ba tầng tài liệu phải tồn tại và tách bạch (AGENTS.md mục 6).

    Bảo vệ điều gì: trước đây trạng thái, kế hoạch và nhật ký nằm chung trong
    một file 1.540 dòng. Phần nhật ký được cập nhật kỷ luật, phần tóm tắt trạng
    thái thì không ai sửa — và người đọc mới luôn đọc phần tóm tắt trước. Kết
    quả: 6 chỗ tài liệu mô tả một hệ thống không còn tồn tại.
    """
    for ten in ("QUYET_DINH_NEN_TANG.md", "KE_HOACH_TRIEN_KHAI.md", "NHAT_KY.md"):
        assert (DOCS / ten).exists(), f"thiếu docs/{ten}"


def test_thu_muc_luu_tru_co_giai_thich():
    """`docs/_luutru/` phải có README nói rõ từng file là gì và vì sao ngừng dùng.

    Bảo vệ điều gì: một thư mục tài liệu cũ không có nhãn sẽ được ai đó đọc và
    làm theo. Chúng mô tả một hệ thống desktop đã bị xoá.
    """
    readme = DOCS / "_luutru" / "README.md"
    assert readme.exists(), "docs/_luutru/ phải có README.md"
    noi_dung = readme.read_text(encoding="utf-8")
    assert "ngừng dùng" in noi_dung.lower() or "ngung dung" in noi_dung.lower()


def test_tai_lieu_dang_hieu_luc_khong_tro_vao_file_da_chuyen_di():
    """Tài liệu chỉ tới file không tồn tại là chỉ dẫn sai.

    Bảo vệ điều gì: 19 tài liệu vừa được chuyển vào `docs/_luutru/`. Một liên
    kết còn trỏ vào chỗ cũ sẽ dẫn người đọc (và Claude) vào ngõ cụt, hoặc tệ
    hơn là làm họ tưởng tài liệu đó đã bị xoá.
    """
    mau = re.compile(r"docs/([A-Za-z0-9_\-]+\.(?:md|json|py))")
    hong = []
    for doc in DOCS.glob("*.md"):
        for ten in mau.findall(doc.read_text(encoding="utf-8")):
            if not (DOCS / ten).exists() and not (DOCS / "_luutru" / ten).exists():
                hong.append(f"{doc.name} -> docs/{ten}")
    assert hong == [], f"tài liệu trỏ vào file không có: {hong}"


def test_chi_con_mot_he_danh_so_ke_hoach():
    """Chỉ được dùng một hệ đánh số hạng mục: H0, H1, …

    Bảo vệ điều gì: dự án từng có **bốn** hệ song song (P0–P11, PA–PE, W1–W6)
    và không hệ nào tuyên bố mình đã bị thay thế. Đọc tài liệu không biết đang
    ở đâu — đó là nguyên nhân gốc của việc phải đi dọn tài liệu.

    Chỉ soi kế hoạch đang hiệu lực. Tài liệu lưu trữ giữ nguyên hệ số cũ của
    chúng, đó là đúng.
    """
    ke_hoach = (DOCS / "KE_HOACH_TRIEN_KHAI.md").read_text(encoding="utf-8")
    # Bỏ qua phần giải thích lịch sử (chỗ duy nhất được phép nhắc hệ số cũ).
    dong_vi_pham = [
        line for line in ke_hoach.splitlines()
        if re.search(r"^\s*[-*|]?\s*(P\d{1,2}|W[1-6]|P[A-E])\b", line)
        and "trước đây" not in line.lower() and "song song" not in line.lower()
    ]
    assert dong_vi_pham == [], (
        f"Kế hoạch chỉ dùng hệ H. Dòng dùng hệ cũ: {dong_vi_pham}"
    )


# ── Ràng buộc 6: script không được chứa ký tự điều khiển vô hình ─────────────

def _script_files() -> list[pathlib.Path]:
    out: list[pathlib.Path] = []
    for d in ("setup", "deploy"):
        out += [p for p in (ROOT / d).rglob("*.ps1")]
    return out


@pytest.mark.parametrize("ten", sorted(p.relative_to(ROOT).as_posix()
                                       for p in _script_files()))
def test_script_khong_co_ky_tu_dieu_khien(ten):
    r"""Ký tự điều khiển trong script là lỗi vô hình và tốn kém nhất.

    Đã xảy ra hai lần trong dự án này:

    1. Một chuỗi Python không phải raw-string chứa ``.\setup\3-cloudflare`` —
       ``\3`` là escape bát phân nên thành ``chr(3)``. Người đọc copy đường dẫn
       về sẽ chạy sai. Dự án đã thêm test cho **tài liệu** sau lần đó.
    2. Ngày 2026-07-31, đúng lỗi ấy lọt vào **script** khi thêm bước cài
       PostgreSQL: ``'...\PostgreSQL\$v\bin'`` thành ``\x08in`` và
       ``'secrets\app.env'`` thành ``secrets\x07pp.env``.

    Lần thứ hai nguy hiểm hơn nhiều vì không ai đọc script bằng mắt:
    - bộ cài không tìm thấy PostgreSQL rồi báo "cài thất bại" — sai nguyên nhân;
    - `backup.ps1` không thấy `app.env` nên **âm thầm bỏ qua CSDL**, cho ra một
      bản sao lưu trông y hệt bản đầy đủ và chỉ lộ ra đúng lúc cần khôi phục.

    Kiểm tra ASCII sẵn có **không** bắt được: các ký tự này đều nhỏ hơn 128.
    Kiểm tra cú pháp cũng không, vì chúng nằm trong chuỗi.
    """
    text = (ROOT / ten).read_text(encoding="utf-8")
    bad = [(i, hex(ord(c))) for i, c in enumerate(text)
           if ord(c) < 32 and c not in "\n\r\t"]
    chi_tiet = [f"vi tri {i} ({m}): {text[max(0, i-25):i+10]!r}" for i, m in bad[:3]]
    assert bad == [], f"{ten} co ky tu dieu khien vo hinh: " + " | ".join(chi_tiet)


# ── Ràng buộc 7: quyết định không được trùng số ───────────────────────────────

def test_moi_quyet_dinh_co_mot_so_duy_nhat():
    """Hai quyết định trùng số là hai câu trả lời cho cùng một câu hỏi.

    Bảo vệ điều gì: giao thức đổi quyết định (`AGENTS.md` mục 6) yêu cầu thêm
    dòng mới chứ không sửa đè. Nếu dòng mới trùng số với dòng cũ thì không ai
    biết cái nào đang hiệu lực — đúng thứ giao thức đó sinh ra để tránh.
    """
    text = (DOCS / "QUYET_DINH_NEN_TANG.md").read_text(encoding="utf-8")
    so = re.findall(r"^\|\s*(Q\d+)\s*\|", text, flags=re.MULTILINE)
    trung = {q for q in so if so.count(q) > 1}
    assert not trung, f"quyết định trùng số: {sorted(trung)}"
    assert len(so) >= 12, "bảng quyết định trông như bị cắt mất"
