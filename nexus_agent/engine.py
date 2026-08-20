"""Lái engine RustDesk **NGUYÊN BẢN** (Q97, Rổ 1). Agent không sửa binary — chỉ
cấu hình + đặt/xoay mật khẩu + lấy ID qua dòng lệnh của chính RustDesk.

Mọi thao tác ở đây đã **đo trên máy thật** (VM106/VM105, 2026-08-20 —
`docs/nexus/N3_2_ENGINE.md` §3b), không suy đoán từ tài liệu:

* **V1** — trỏ RustDesk về server LTT bằng `RustDesk2.toml`, không sửa binary;
* **V2/V3** — đặt và **xoay** mật khẩu bằng `--password`;
* **V5** — lấy ID bằng `--get-id` (ID cất dạng mã hoá `enc_id`, nên **không bao
  giờ** parse file config để lấy ID — cách đó hỏng ở bản RustDesk kế tiếp).

## Ranh giới QUYỀN — đo được, không đoán (N3_2_ENGINE §V8)

| Thao tác | Quyền cần |
|---|---|
| `--get-id` | **user thường** — được |
| `--password`, ghi config service profile, dừng service | **ADMIN** |

`--password` chạy dưới user thường trả thẳng *"Installation and administrative
privileges required!"*. Hệ quả: **Agent không-admin (N3.3b) KHÔNG tự xoay mật
khẩu được.** Module này vì thế tách rõ hai nhóm hàm:

* `lay_id` — chạy được ở Agent thường;
* `ghi_cau_hinh`, `dat_mat_khau`, `xoay_mat_khau` — **thao tác có đặc quyền**,
  phải chạy bởi thành phần admin (xem quyết định kiến trúc ở `N3_2_ENGINE §V8`:
  hoặc Agent chạy admin, hoặc một trợ lý đặc quyền nhỏ mà Agent thường gọi tới).

Module này **không tự quyết** ai chạy nó với quyền gì — nó chỉ dựng lệnh và nội
dung config đúng, và mỗi hàm khai rõ quyền nó cần. Đặt đúng chỗ là việc của tầng
gọi, và quyết định đó phải công khai vì nó động tới ràng buộc UAC/T1 của Q95.
"""
from __future__ import annotations

import secrets
import string

#: Ba khoá cấu hình trỏ RustDesk về hạ tầng LTT. Bất kỳ dòng nào bắt đầu bằng
#: một trong số này (kể cả `api-server`) đều bị thay, để chạy lại nhiều lần
#: không sinh dòng trùng.
KHOA_SERVER = ("custom-rendezvous-server", "relay-server", "key", "api-server")

#: Bảng chữ cho mật khẩu phiên. Có chủ ý bỏ ký tự dễ nhầm (0/O/1/l/I) và ký tự
#: gây rối cho vỏ lệnh — dù ta truyền qua argv (không qua shell) nên an toàn,
#: giữ sạch để log/hiển thị không hiểu nhầm.
_ALPHABET = (string.ascii_uppercase + string.ascii_lowercase + string.digits
             ).translate(str.maketrans("", "", "0O1lI"))


class EngineError(Exception):
    """Một thao tác engine không thành. Không bao giờ chứa mật khẩu."""


# ── Hàm THUẦN: dựng nội dung/lệnh, không chạm hệ thống ───────────────────────

def sinh_mat_khau_phien(do_dai: int = 20) -> str:
    """Mật khẩu một-lần cho một phiên. CSPRNG, không đoán được.

    Dùng `secrets`, không `random`: mật khẩu này là credential truyền của một
    phiên điều khiển từ xa; một PRNG đoán được ở đây là một cửa hậu đoán được.
    """
    if do_dai < 12:
        raise EngineError("mat khau phien qua ngan")
    return "".join(secrets.choice(_ALPHABET) for _ in range(do_dai))


def noi_dung_config(dong_hien_co, server: str, key: str) -> str:
    """Trả về NỘI DUNG mới của `RustDesk2.toml` trỏ về server LTT.

    Idempotent: gọi lại với cùng tham số cho ra cùng kết quả, không nhân dòng —
    vì Agent sẽ chạy nó mỗi lần khởi động, và một file config phình thêm ba dòng
    mỗi lần là một lỗi âm thầm.

    Đặt ba khoá **ngay sau `[options]`**, không phải cuối file: TOML gán khoá cho
    section gần nhất phía trên, nên thả xuống cuối có thể rơi nhầm vào một section
    khác nếu file có nhiều section. Bẫy này chỉ hiện khi config phức tạp lên.
    """
    server = str(server or "").strip()
    key = str(key or "").strip()
    if not server or not key:
        raise EngineError("thieu server hoac key")

    giu = [d for d in (dong_hien_co or [])
           if not any(d.lstrip().startswith(k) and "=" in d
                      and d.split("=", 1)[0].strip() == k for k in KHOA_SERVER)]

    them = [f"custom-rendezvous-server = '{server}'",
            f"relay-server = '{server}'",
            f"key = '{key}'"]

    # Tìm dòng [options]; nếu chưa có thì thêm.
    idx = next((i for i, d in enumerate(giu) if d.strip() == "[options]"), None)
    if idx is None:
        giu.append("[options]")
        idx = len(giu) - 1
    ket_qua = giu[:idx + 1] + them + giu[idx + 1:]
    return "\n".join(ket_qua).rstrip("\n") + "\n"


def lenh_get_id(exe: str) -> list:
    """Lệnh lấy ID. Chạy được với **user thường** (đã đo)."""
    return [exe, "--get-id"]


def lenh_password(exe: str, mat_khau: str) -> list:
    """Lệnh đặt mật khẩu không giám sát. **ĐÒI QUYỀN ADMIN** (đã đo).

    Trả về LIST (không phải chuỗi): `subprocess` với list không đi qua shell, nên
    một mật khẩu chứa ký tự đặc biệt không thể biến thành lệnh khác. Đây là khác
    biệt giữa 'trích dẫn cẩn thận' và 'không có chỗ để tiêm'.
    """
    if not mat_khau:
        raise EngineError("mat khau rong")
    return [exe, "--password", mat_khau]


# ── Lớp CHẠY mỏng: nhận `runner` để test không cần RustDesk ───────────────────

def _chay(runner, argv: list) -> str:
    ma, ra = runner(argv)
    if ma != 0:
        raise EngineError(f"lenh that bai (ma {ma}): {str(ra)[:200]}")
    return str(ra or "").strip()


def lay_id(exe: str, *, runner) -> str:
    """ID của máy này. Chạy được ở Agent thường."""
    out = _chay(runner, lenh_get_id(exe))
    # RustDesk in ID dạng số. Lọc lấy token số đầu tiên cho chắc — bản có thể in
    # thêm dòng log ra stdout (đã thấy "set plugin ... unusable" ở V4).
    for token in out.split():
        if token.isdigit():
            return token
    raise EngineError(f"khong doc duoc ID tu output: {out[:120]}")


def dat_mat_khau(exe: str, mat_khau: str, *, runner) -> None:
    """Đặt mật khẩu không giám sát. **Phải chạy với quyền admin.**

    RustDesk in `Done!` khi thành công; dưới user thường nó in *"administrative
    privileges required!"*. Ta bắt cả hai để lỗi quyền không bị nuốt thành 'im
    lặng mà không đặt được'.
    """
    out = _chay(runner, lenh_password(exe, mat_khau))
    if "Done" not in out:
        if "privile" in out.lower():
            raise EngineError(
                "dat mat khau doi quyen admin — Agent nay khong du quyen "
                "(xem N3_2_ENGINE §V8)")
        raise EngineError(f"dat mat khau khong xac nhan duoc: {out[:120]}")


def xoay_mat_khau(exe: str, *, runner, do_dai: int = 20) -> str:
    """Sinh một mật khẩu mới, đặt nó, trả về nó. **Phải chạy với quyền admin.**

    Đây là cách dựng lại tính 'vé một lần' của Q93 bằng cơ chế của RustDesk:
    mỗi phiên một mật khẩu mới, phiên cũ hết giá trị. Trả mật khẩu để tầng gọi
    chuyển cho bên điều khiển qua đúng đường vé của server — **không** ghi nó ra
    log, không cất nó xuống đĩa.
    """
    mk = sinh_mat_khau_phien(do_dai)
    dat_mat_khau(exe, mk, runner=runner)
    return mk


__all__ = ["EngineError", "KHOA_SERVER", "dat_mat_khau", "lay_id",
           "lenh_get_id", "lenh_password", "noi_dung_config",
           "sinh_mat_khau_phien", "xoay_mat_khau"]
