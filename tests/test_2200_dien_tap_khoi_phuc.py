"""test_2200 — biên an toàn của đường diễn tập khôi phục.

Kiểm MỌI điều mà nếu vỡ một cái là có thể chạm production:

1. ``deploy/windows/dien_tap_khoi_phuc.ps1`` thuần ASCII, không BOM
   (luật AGENTS.md §5.2 — PowerShell 5.1 đọc ANSI, một dấu tiếng Việt làm
   hỏng câu lệnh ở dòng khác).
2. KHÔNG có tham số ``-Live`` ở bất kỳ đâu trong script — không đường nào
   vô tình gọi ``restore.ps1 -Live`` hay ghi đè CSDL thật.
3. Script chỉ VIẾT vào ``$env:TEMP`` (dải ``ltt_dienthu_``), không có đường
   dẫn nào trỏ vào ``C:\\LTTPlatform\\data`` hay thư mục ``restore_test_``.
   ``C:\\LTTPlatform`` chỉ được phép xuất hiện với tư cách NƠI ĐỌC
   ``secrets\\app.env`` (đọc, không ghi).
4. Khối ``finally`` phải DROP CSDL tạm (``DROP DATABASE IF EXISTS``) —
   CSDL diễn tập không được phép tồn tại sau khi script chạy, kể cả khi lỗi.
5. Script phải tạo CSDL theo đúng hình ``lttplatform_dienthu_<stamp>`` —
   không bao giờ trùng tên CSDL production ``lttplatform``.
6. ``dien_tap_kiem.py`` (checker) đọc ``LTT_DATABASE_URL`` bằng regex giống
   hệt ``restore.ps1`` — kiểm bằng giá trị TỔNG HỢP, không phải secret thật.

Không cần CSDL thật, không đọc trạng thái máy: toàn bộ là đọc hai tệp trong
kho + một vài chuỗi tổng hợp.
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
PS1 = ROOT / "deploy" / "windows" / "dien_tap_khoi_phuc.ps1"
PY_CHECKER = ROOT / "deploy" / "windows" / "dien_tap_kiem.py"

# Regex ĐỘC LẬP (không import từ script) để so sánh — hai nguồn phải khớp
# về DẠNG chuỗi kết nối mà chúng nhận. Đây là luật "đọc đúng theo cách
# restore.ps1 đang làm".
RE_GIONG_RESTORE = re.compile(
    r"(?m)^LTT_DATABASE_URL=postgresql\+?\w*://([^:]+):([^@]+)@"
    r"([^:/]+):(\d+)/(\S+)\s*$"
)


def test_ps1_ton_tai_va_thuan_ascii_khong_bom() -> None:
    assert PS1.is_file(), f"thieu {PS1}"
    raw = PS1.read_bytes()
    assert raw[:3] != b"\xef\xbb\xbf", "BOM ở đầu file .ps1 — PowerShell 5.1 sẽ đọc sai"
    for i, b in enumerate(raw):
        assert b < 128, f"byte không-ASCII 0x{b:02x} ở vị trí {i} — .ps1 phải thuần ASCII (AGENTS.md §5.2)"


def test_ps1_khong_co_duong_dan_live() -> None:
    text = PS1.read_text(encoding="ascii")
    # "-Live" không được xuất hiện như MỘT TOKEN tham số (nhắc trong chú thích
    # là chuyện khác). Token = -Live đứng sau dấu cách/ngoặc kép/dấu nháy.
    assert re.search(r"['\" ]-Live\b", text) is None, (
        "dien_tap_khoi_phuc.ps1 chứa token tham số -Live — không được có đường dẫn tới khôi phục thật"
    )
    # Không GỌI restore.ps1 (dòng lệnh, không phải chú thích). Nhắc "đọc cấu
    # hình theo phương pháp của restore.ps1" trong comment là được phép.
    for dong in text.splitlines():
        dong_s = dong.strip()
        if dong_s.startswith("#"):
            continue
        assert not re.search(r"(&|Invoke-Expression|Start-Process|'|\.)\s*restore\.ps1", dong_s, re.IGNORECASE), (
            f"dien_tap không được GỌI restore.ps1 — nó phải là đường độc lập: {dong_s!r}"
        )


def test_ps1_chi_viet_vao_env_temp() -> None:
    text = PS1.read_text(encoding="ascii")
    assert "$env:TEMP" in text, "script phải đặt mọi thứ tạm dưới $env:TEMP"
    assert "ltt_dienthu_" in text, "dải tên tạm phải là ltt_dienthu_<stamp>"
    # Các đường dẫn ghi KHÔNG được trỏ vào production.
    for can in [r"Join-Path $Root 'data'", "restore_test_", r"\\data\\", "Expand-Archive -Path $Archive -DestinationPath $dataDir"]:
        assert can not in text, f"script có đường ghi vào production: {can!r}"


def test_ps1_drop_csd_tam_trong_finally() -> None:
    text = PS1.read_text(encoding="ascii")
    assert "finally" in text
    # DROP phải nằm SAU từ khoá finally (trong khối finally), không phải trước.
    pos_finally = text.index("finally")
    pos_drop = text.index("DROP DATABASE IF EXISTS")
    assert pos_drop > pos_finally, "DROP DATABASE IF EXISTS phải nằm trong khối finally để chạy kể cả khi lỗi"


def test_ps1_tao_csd_dung_hinh_dienthu() -> None:
    text = PS1.read_text(encoding="ascii")
    m = re.search(r"\$dbName\s*=\s*\"([^\"]+)\"", text)
    assert m, "không tìm được định nghĩa $dbName"
    dang = m.group(1)
    assert dang.startswith("lttplatform_dienthu_"), f"hình CSDL tạm sai: {dang!r}"
    # Dải tên bắt buộc mang hậu tố "lttplatform_dienthu_" — CSDL tạo ra từ
    # biến này KHÔNG THỂ trùng tên production "lttplatform" (hậu tố khác).
    assert dang != "lttplatform"
    # Mọi câu CREATE DATABASE trong code (không phải comment) phải tham chiếu
    # $dbName — không câu nào viết cứng tên production.
    tao = []
    trong_khong = False
    for d in text.splitlines():
        ds = d.strip()
        if ds.startswith("<#"):
            trong_khong = True
        if trong_khong:
            if ds.endswith("#>"):
                trong_khong = False
            continue
        if ds.startswith("#"):
            continue
        if "CREATE DATABASE" in d:
            tao.append(ds)
    assert tao, "không tìm thấy câu CREATE DATABASE nào trong script"
    for dong in tao:
        assert "$dbName" in dong, f"Câu CREATE DATABASE không dùng $dbName: {dong!r}"


def test_ps1_chi_doc_app_env_khong_in_ra() -> None:
    text = PS1.read_text(encoding="ascii")
    # Chỉ được NƠI ĐỌC app.env (mặc định C:\LTTPlatform\secrets\app.env).
    assert "app.env" in text
    # Mật khẩu phải đi qua biến môi trường PGPASSWORD cho pg_restore/psql,
    # và không được Write-Host/Out-String giá trị của nó.
    assert "PGPASSWORD" in text
    for dong in text.splitlines():
        if "Write-Host" in dong:
            assert "$pgPass" not in dong, f"dòng in ra giá trị mật khẩu: {dong.strip()!r}"


def test_checker_doc_url_giong_restore_ps1() -> None:
    """Checker phải đọc LTT_DATABASE_URL bằng ĐÚNG MỘT regex với restore.ps1.

    Không import code của restore.ps1 (nó là PowerShell, không phải Python).
    Thay vào đó: so nguồn regex TỪNG CHỮ — hai file phải chứa cùng một
    literal regex (cùng chuỗi, cùng nhóm bắt). Đây mới là điều "giống
    restore.ps1" thật sự đo được: một dòng URL hợp lệ mà restore.ps1 sinh ra
    phải được checker nhận, và một dòng sai phải bị từ chối.
    """
    assert PY_CHECKER.is_file(), f"thieu {PY_CHECKER}"
    src = PY_CHECKER.read_text(encoding="utf-8")

    # Tách THÂN của re.compile(_RE_URL) bằng AST — không phải regex-vào-regex
    # (thân chứa ')' bên trong, vd \), nên tách bằng dấu ngoặc thô sẽ bắt
    # nhầm). AST đọc đúng ký tự chuỗi nối trên nhiều dòng.
    start = src.find("_RE_URL")
    assert start != -1, "không tìm thấy _RE_URL trong dien_tap_kiem.py"
    open_paren = src.find("re.compile(", start)
    assert open_paren != -1, "không tìm thấy re.compile( cho _RE_URL"
    body = src[open_paren:]
    # Lấy đến dấu đóng ) đứng đầu dòng kế tiếp.
    m_close = re.search(r"\n\s*\)\s*\n", body)
    assert m_close, "không tìm thấy dấu đóng ) của re.compile(_RE_URL)"
    call_src = body[: m_close.start()] + ")"

    import ast
    tree = ast.parse(call_src)
    assert isinstance(tree.body, list) and tree.body, "thân re.compile không parse được"
    stmt = tree.body[0]
    assert isinstance(stmt, ast.Expr), "thân re.compile không phải biểu thức"
    call = stmt.value
    assert isinstance(call, ast.Call) and len(call.args) == 1, "re.compile phải nhận 1 tham số"
    pattern_node = call.args[0]
    assert isinstance(pattern_node, ast.Constant) and isinstance(pattern_node.value, str), (
        "tham số của re.compile(_RE_URL) phải là chuỗi"
    )
    checker_pattern = pattern_node.value

    # So với pattern ĐỘC LẬP của restore.ps1 — hai chuỗi phải KHỚP HẲNG.
    restore_pattern = (
        r"(?m)^LTT_DATABASE_URL=postgresql\+?\w*://([^:]+):([^@]+)@"
        r"([^:/]+):(\d+)/(\S+)\s*$"
    )
    assert checker_pattern == restore_pattern, (
        f"regex đọc LTT_DATABASE_URL của checker KHÁC restore.ps1.\n"
        f"  checker : {checker_pattern!r}\n"
        f"  restore : {restore_pattern!r}"
    )

    # Hành vi: giá trị TỔNG HỢP (không phải secret) phải được nhận và nhóm
    # bắt khớp; chuỗi KHÔNG có DB name phải bị từ chối.
    checker_re = re.compile(checker_pattern)
    dong_tong_hop = "LTT_DATABASE_URL=postgresql+psycopg://user_giam_do:mat_khau_giam_do@127.0.0.1:5432/giam_do_db\n"
    m_restore = RE_GIONG_RESTORE.search(dong_tong_hop)
    m_checker = checker_re.search(dong_tong_hop)
    assert m_restore and m_checker, "cả hai regex phải nhận được chuỗi hợp lệ"
    assert m_restore.groups() == m_checker.groups(), (
        f"regex checker khác regex restore: {m_restore.groups()} != {m_checker.groups()}"
    )

    dong_hong = "LTT_DATABASE_URL=postgresql+psycopg://user:pw@127.0.0.1:5432\n"
    assert RE_GIONG_RESTORE.search(dong_hong) is None
    assert checker_re.search(dong_hong) is None


def test_ps1_co_buoc_alembic_upgrade_head() -> None:
    """Đường khôi phục phải có BƯỚC NÂNG CẤP LƯỢC ĐỒ sau khi nạp dump.

    Bài học diễn tập 23/09/2026: dump 02:30 ở version e4a19c07b5d2, head mã
    đang deploy là 5e1a9c46b2d7 — lệch 3 migration video_crawler vì deploy
    (13:40) mới là lúc chạy alembic. So sánh "version dump == head" là sai:
    nó đỏ cả bản sao khoẻ, và xanh không nói gì về đường khôi phục. Phép
    kiểm đúng phải CHẠY `alembic upgrade head` lên CSDL tam và xác minh
    version sau nâng cấp == head.

    Test này chốt BA điều khiến bước upgrade an toàn trên máy production:
    1. script phải gọi `alembic upgrade head` (không chỉ so version);
    2. URL CSDL của tiến trình upgrade phải được ghim vào CSDL TAM
       (LTT_DATABASE_URL xây từ $dbName) — upgrade không được phép chạm
       DB thật dù môi trường cha có sẵn URL live;
    3. script phải đọc lại version sau upgrade và so với head (xác minh
       kết quả, không chỉ tin mã thoát).
    """
    text = PS1.read_text(encoding="ascii")
    # 1. Có bước upgrade head.
    assert "upgrade head" in text, (
        "dien_tap_khoi_phuc.ps1 thiếu bước 'alembic upgrade head' sau khi nạp dump — "
        "khôi phục bản sao lấy trước deploy sẽ thiếu bảng mới"
    )
    # 2. URL của upgrade con trỏ vào CSDL tam, không trỏ DB thật.
    assert re.search(r'LTT_DATABASE_URL\s*=\s*"[^"]*\$\{dbName\}', text) or (
        "LTT_DATABASE_URL" in text and "$dbName" in text
        and re.search(r"postgresql\+psycopg://.*\$\{dbName\}", text)
    ), (
        "upgrade head phải chạy với LTT_DATABASE_URL ghim vào CSDL tam ($dbName) — "
        "không được để upgrade đọc URL live từ môi trường cha"
    )
    # 3. Xác minh bằng cách đọc lại version sau upgrade, không chỉ tin rc.
    assert "SELECT version_num FROM alembic_version" in text, (
        "script phải đọc lại alembic_version SAU upgrade để xác minh "
        "(tin mã thoát của alembic là đo hình dáng, không phải kết quả)"
    )
    # 4. Upgrade phải chạy trong venv có mã DEPLOYED (C:\LTTPlatform\app),
    # không phải cây dev (head của dev có thể khác production).
    assert "C:\\LTTPlatform\\app" in text, (
        "alembic head phải lấy từ cây mã đã deploy (C:\\LTTPlatform\\app) — "
        "máy khôi phục sẽ chạy đúng cây đó"
    )
