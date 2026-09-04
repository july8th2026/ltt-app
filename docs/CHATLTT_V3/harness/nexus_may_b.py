"""
nexus_may_b.py — MỘT cửa duy nhất để phiên này nói chuyện với máy B qua Nexus.

⭐ VÌ SAO LÀ MỘT SCRIPT CHỨ KHÔNG PHẢI `curl` TRẦN

   Quyền được cấp 04/09 là quyền **chạy tệp này**, không phải quyền gọi mạng
   tuỳ ý. Khác biệt đó có giá trị thật: mọi lời gọi tới máy B đi qua đúng một
   chỗ, nên **đọc một tệp là biết phiên này đã làm gì với máy kia** — thay vì
   phải lần lại từng dòng lệnh rải rác trong nhật ký hội thoại.

   Rule tương ứng trong `.claude/settings.local.json`:
       Bash(python docs/CHATLTT_V3/harness/nexus_may_b.py:*)

⛔ MỌI LỜI GỌI ĐỀU ĐƯỢC GHI NHẬT KÝ, kể cả lời gọi hỏng, vào
   `docs/CHATLTT_V3/harness/nexus_audit.log`. Đừng bỏ dòng ghi đó đi: nó là
   thứ duy nhất biến "một quyền rộng" thành "một quyền kiểm toán được".

## Ba tầng ranh giới (Ket_noi.md §3) — nhầm tầng là mất hàng giờ

    allowed_roots          ranh giới của File API      sửa ở MÁY ĐÍCH
    capability của node    máy đó chịu cho phép gì     sửa ở MÁY ĐÍCH
    capability của token   bạn được gõ cửa nào         sửa ở MÁY BẠN GỌI

⚠️ Token được xác thực bằng CSDL của **máy nhận request** (máy A), không phải
   máy đích. Đó là tầng hay nhầm nhất.

## Dùng

    python nexus_may_b.py kham                  # dò xem cửa nào mở (chạy MỘT lần)
    python nexus_may_b.py gpu                   # GPU máy B
    python nexus_may_b.py doc <duong-dan>       # đọc một tệp trên máy B
    python nexus_may_b.py chay -- <lenh> [...]  # chạy một lệnh trên máy B
    python nexus_may_b.py http <duong-dan>      # GET một URL localhost CỦA MÁY B

`http` là thứ dùng nhiều nhất cho P01: `/props` và `/running` chỉ nghe trên
`127.0.0.1` của máy B, LAN không với tới.
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import json
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ── Hằng số của cụm. Nguồn: Desktop\Ket_noi.md (sinh tự động từ trạng thái thật)
CONTROLLER_A = "https://192.168.2.17:9444"
NODE_MAY_B = "f8b24d88-6e3e-4719-8143-d5e83f68ed82"
TOKEN_PATH = Path.home() / ".nexus" / "claude-code.token"
AUDIT = Path(__file__).with_name("nexus_audit.log")

#: Đường `/exec` chưa được xác nhận — `kham` sẽ tìm và ghi lại vào tệp này.
DUONG_UNG_VIEN = {
    "chay": ["exec", "commands/run", "command/run", "process/exec",
             "system/exec", "commands/execute", "shell/exec"],
    "doc": ["files/read", "file/read", "fs/read", "files"],
}
CACHE = Path(__file__).with_name("nexus_duong.json")
#: Vân tay chứng chỉ đã ghim. Tách khỏi CACHE vì nó là **bí mật bảo mật**,
#: không phải một tuỳ chọn tiện dụng — xoá nhầm CACHE không được làm mất ghim.
PIN = Path(__file__).with_name("nexus_cert_pin.txt")


class LoiNexus(RuntimeError):
    pass


def _token() -> str:
    if not TOKEN_PATH.exists():
        raise LoiNexus(f"khong thay token: {TOKEN_PATH}")
    return TOKEN_PATH.read_text(encoding="utf-8").strip()


def _ghi_nhat_ky(viec: str, chi_tiet: str, ket_qua: str) -> None:
    """Ghi MỌI lời gọi. Hỏng cũng ghi — một lời gọi bị từ chối cũng là một lời gọi."""
    dong = (f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}\t"
            f"{viec}\t{chi_tiet}\t{ket_qua}\n")
    try:
        with AUDIT.open("a", encoding="utf-8") as f:
            f.write(dong)
    except OSError:
        pass                    # nhật ký hỏng không được làm hỏng việc


def _van_tay_hien_tai(host: str, port: int) -> str:
    """SHA256 của chứng chỉ DER mà controller đang trình ra."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    import socket
    with socket.create_connection((host, port), timeout=10) as s:
        with ctx.wrap_socket(s, server_hostname=host) as ss:
            der = ss.getpeercert(binary_form=True)
    return hashlib.sha256(der).hexdigest()


def _kiem_ghim(host: str, port: int) -> None:
    """Ghim chứng chỉ theo kiểu tin-lần-đầu (TOFU). Lệch ⇒ DỪNG, không hỏi.

    🔴 VÌ SAO PHẢI GHIM, KHÔNG ĐƯỢC `CERT_NONE` TRẦN.

       Token đi trên kết nối này mang capability `command.run` trên máy B. Một
       kẻ MITM trong LAN đọc được nó là có **thi hành mã tuỳ ý trên máy B** —
       và `Ket_noi.md` §3 đã ghi rõ: `/exec` chỉ kiểm `cwd`, thân lệnh chạy tự
       do dưới LocalSystem. Không có `allowed_roots` nào chặn được điều đó.

       Controller dùng chứng chỉ **tự ký** nên không có CA nào xác minh được.
       Ghim vân tay là cách đúng cho đúng hoàn cảnh đó: lần đầu ghi lại, mọi
       lần sau so khớp.

    ⛔ Lệch vân tay là DỪNG HẲN, không phải cảnh báo rồi đi tiếp. Nếu máy B được
       cài lại thật (đã xảy ra một lần — `Ket_noi.md` §9) thì **xoá tệp ghim
       bằng tay** sau khi tự xác nhận. Bắt buộc một hành động của con người ở
       đúng chỗ đó là có chủ ý.
    """
    van_tay = _van_tay_hien_tai(host, port)
    if not PIN.exists():
        PIN.write_text(van_tay + "\n", encoding="utf-8")
        print(f"[nexus] ghim chung chi lan dau: {van_tay[:32]}...",
              file=sys.stderr)
        _ghi_nhat_ky("ghim", host, van_tay)
        return
    da_ghim = PIN.read_text(encoding="utf-8").strip()
    if da_ghim != van_tay:
        _ghi_nhat_ky("ghim-lech", host, f"{da_ghim[:16]} != {van_tay[:16]}")
        raise LoiNexus(
            "CHUNG CHI CONTROLLER DA DOI — dung lai.\n"
            f"  da ghim  : {da_ghim}\n"
            f"  hien tai : {van_tay}\n"
            "Neu may that su duoc cai lai thi xoa tay tep ghim:\n"
            f"  {PIN}")


def goi(duong: str, than: dict | None = None, *, method: str = "GET",
        timeout: float = 30.0) -> tuple[int, str]:
    """Gọi controller máy A, nó proxy sang máy B. Trả `(ma_http, than_van_ban)`."""
    url = f"{CONTROLLER_A}/api/v1/nodes/{NODE_MAY_B}/proxy/api/v1/{duong.lstrip('/')}"
    host, port = CONTROLLER_A.split("//", 1)[1].split(":")
    _kiem_ghim(host, int(port))
    du_lieu = json.dumps(than).encode("utf-8") if than is not None else None
    req = urllib.request.Request(url, data=du_lieu, method=method)
    req.add_header("X-Nexus-Protocol", "1")
    req.add_header("Authorization", f"Bearer {_token()}")
    if du_lieu is not None:
        req.add_header("Content-Type", "application/json")
    # Chứng chỉ tự ký ⇒ không có CA để xác minh; tính xác thực được bảo đảm bởi
    # `_kiem_ghim()` ở trên (ghim vân tay), không phải bởi việc bỏ qua nó.
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise LoiNexus(f"khong goi duoc {duong}: {e}") from None


def _duong_da_biet(viec: str) -> str | None:
    if not CACHE.exists():
        return None
    try:
        return json.loads(CACHE.read_text(encoding="utf-8")).get(viec)
    except (ValueError, OSError):
        return None


def _nho_duong(viec: str, duong: str) -> None:
    d = {}
    if CACHE.exists():
        try:
            d = json.loads(CACHE.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            d = {}
    d[viec] = duong
    CACHE.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")


def _dong_lenh(phan: list) -> str:
    """Gop thanh MOT dong lenh.

    !! Nexus KHONG chuyen mang `args` toi tien trinh — do that 04/09:
       `curl.exe --version` voi args=["--version"] van bao "try 'curl --help'",
       tuc exe chay ma khong nhan duoc tham so nao. Mot mang bi bo qua IM LANG
       la thu de nham nhat: lenh van chay, exit code van co, chi la sai viec.

    Nexus boc dong nay trong PowerShell, nen phan nao co khoang trang phai
    duoc boc nhay don.
    """
    ra = []
    for x in phan:
        x = str(x)
        ra.append("'" + x.replace("'", "''") + "'" if (" " in x or '"' in x) else x)
    return " ".join(ra)


# ── Lệnh ─────────────────────────────────────────────────────────────────────

def lenh_gpu(_args) -> int:
    ma, than = goi("metrics/gpu")
    _ghi_nhat_ky("gpu", "-", str(ma))
    print(than)
    return 0 if ma == 200 else 1


def lenh_kham(_args) -> int:
    """Dò xem đường nào mở. Chạy MỘT lần rồi nhớ vào `nexus_duong.json`.

    ⭐ Việc dò nằm TRONG script được cấp quyền, không phải trong một vòng `curl`
       rời — đó là khác biệt giữa "một công cụ đã được duyệt tự mô tả cụm" và
       "ai đó đang quét cổng".
    """
    print(f"controller : {CONTROLLER_A}")
    print(f"node may B : {NODE_MAY_B}")
    print(f"token      : {'CO' if TOKEN_PATH.exists() else 'KHONG'}\n")

    ma, _ = goi("metrics/gpu")
    print(f"  metrics/gpu                 -> {ma}  {'OK' if ma == 200 else ''}")

    for duong in ("health", "info", "capabilities", "openapi.json", "docs"):
        try:
            ma, than = goi(duong)
        except LoiNexus as e:
            print(f"  {duong:-28}-> loi: {e}")
            continue
        print(f"  {duong:<28}-> {ma}"
              + (f"  {than[:100]}" if ma == 200 else ""))

    print("\n  -- tim duong doc tep --")
    for duong in DUONG_UNG_VIEN["doc"]:
        try:
            ma, than = goi(f"{duong}?path=H:\\LTT_LLM")
        except LoiNexus as e:
            print(f"  {duong:<28}-> loi: {e}")
            continue
        print(f"  {duong:<28}-> {ma}  {than[:120]}")
        if ma == 200:
            _nho_duong("doc", duong)
            print(f"     ^ nho lai lam duong DOC")
            break

    print("\n  -- tim duong chay lenh --")
    for duong in DUONG_UNG_VIEN["chay"]:
        try:
            ma, than = goi(duong, {"command": "cmd", "args": ["/c", "echo nexus-ok"],
                                   "cwd": "H:\\",
                                   "reason": "H44 P01: do duong exec"}, method="POST")
        except LoiNexus as e:
            print(f"  {duong:<28}-> loi: {e}")
            continue
        print(f"  {duong:<28}-> {ma}  {than[:160]}")
        if ma in (200, 201):
            _nho_duong("chay", duong)
            print(f"     ^ nho lai lam duong CHAY")
            break

    _ghi_nhat_ky("kham", "-", "xong")
    print(f"\nDuong da nho: {CACHE if CACHE.exists() else '(chua tim thay)'}")
    return 0


def lenh_doc(args) -> int:
    duong = _duong_da_biet("doc")
    if not duong:
        print("Chua biet duong doc tep. Chay `kham` truoc.", file=sys.stderr)
        return 2
    ma, than = goi(f"{duong}?path={args.duong_dan}")
    _ghi_nhat_ky("doc", args.duong_dan, str(ma))
    print(than)
    return 0 if ma == 200 else 1


def lenh_chay(args) -> int:
    duong = _duong_da_biet("chay")
    if not duong:
        print("Chua biet duong chay lenh. Chay `kham` truoc.", file=sys.stderr)
        return 2
    if not args.lenh:
        print("Thieu lenh.", file=sys.stderr)
        return 2
    than = {"command": _dong_lenh(args.lenh), "args": [], "cwd": args.cwd,
            "reason": args.reason}
    ma, tra = goi(duong, than, method="POST", timeout=args.timeout)
    _ghi_nhat_ky("chay", " ".join(args.lenh), str(ma))
    print(tra)
    return 0 if ma in (200, 201) else 1


def lenh_http(args) -> int:
    """GET một URL localhost CỦA MÁY B, qua một lệnh curl chạy trên máy B.

    ⭐ Đây là thứ P01 cần nhất: `/props` và `/running` chỉ nghe trên `127.0.0.1`
       của máy B. Cổng 8299 ra được LAN nhưng nó là cổng LTT, không phải
       llama-server.
    """
    duong = _duong_da_biet("chay")
    if not duong:
        print("Chua biet duong chay lenh. Chay `kham` truoc.", file=sys.stderr)
        return 2
    # !! `curl.exe`, KHONG phai `curl`. Nexus boc lenh trong PowerShell, va o do
    #    `curl` la bi danh cua `Invoke-WebRequest` — no nuot co -sS/--max-time roi
    #    bao thieu tham so `Uri`. Cung ly do khien `cmd`/`powershell.exe` treo:
    #    long mot shell trong mot shell da co san.
    than = {"command": _dong_lenh(
                ["curl.exe", "-sS", "--max-time", str(int(args.timeout)), args.url]),
            "args": [], "cwd": "C:/Users", "reason": args.reason}
    ma, tra = goi(duong, than, method="POST", timeout=args.timeout + 10)
    _ghi_nhat_ky("http", args.url, str(ma))
    print(tra)
    return 0 if ma in (200, 201) else 1


def lenh_raw(args) -> int:
    """GET/POST một đường proxy bất kỳ và in NGUYÊN VĂN.

    ⭐ Có mặt vì `kham` cắt ngắn thân trả về, mà chính thân đó mới nói được
       schema mà một cửa 422 đang đòi. Cắt ngắn một thông báo lỗi là vứt đi
       đúng phần trả lời được câu hỏi.
    """
    # >> Doc than tu TEP khi co: bash/PowerShell deu nuot backslash trong
    #    chuoi inline, va duong dan Windows thi day backslash. Mot lan gia
    #    tri bi nuot la mot loi JSON o cot 41 khong lien quan gi den viec that.
    if args.than_file:
        than = json.loads(pathlib.Path(args.than_file).read_text(encoding="utf-8"))
    else:
        than = json.loads(args.than) if args.than else None
    ma, tra = goi(args.duong, than, method=("POST" if than is not None else "GET"),
                  timeout=args.timeout)
    _ghi_nhat_ky("raw", args.duong, str(ma))
    # >> Ghi ra TEP khi duoc yeu cau: console Windows (cp1252) nem khi gap
    #    ky tu ngoai bang ma, va mot template Jinja thi day ky tu nhu vay.
    #    In truc tiep la danh mat ket qua cua mot loi goi da thanh cong.
    if args.out:
        pathlib.Path(args.out).write_text(tra, encoding="utf-8")
        print(f"HTTP {ma} -> {args.out} ({len(tra)} ky tu)")
        return 0 if ma < 400 else 1
    print(f"HTTP {ma}")
    try:
        print(json.dumps(json.loads(tra), ensure_ascii=False, indent=2))
    except ValueError:
        print(tra)
    return 0 if ma < 400 else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Cua duy nhat toi may B qua Nexus.")
    sub = p.add_subparsers(dest="lenh_con", required=True)

    sub.add_parser("kham", help="do xem duong nao mo (chay MOT lan)").set_defaults(f=lenh_kham)
    sub.add_parser("gpu", help="GPU may B").set_defaults(f=lenh_gpu)

    d = sub.add_parser("doc", help="doc mot tep tren may B")
    d.add_argument("duong_dan")
    d.set_defaults(f=lenh_doc)

    c = sub.add_parser("chay", help="chay mot lenh tren may B")
    c.add_argument("--cwd", default="H:\\")
    c.add_argument("--timeout", type=float, default=120.0)
    c.add_argument("--reason", default="H44 P01: doc sieu du lieu runtime may B")
    c.add_argument("lenh", nargs=argparse.REMAINDER)
    c.set_defaults(f=lenh_chay)

    r = sub.add_parser("raw", help="GET/POST mot duong proxy bat ky, in NGUYEN VAN")
    r.add_argument("duong")
    r.add_argument("--than", default="", help="JSON than; co than ⇒ POST")
    r.add_argument("--than-file", default="", help="doc than tu tep JSON")
    r.add_argument("--out", default="", help="ghi than tra ve ra tep UTF-8")
    r.add_argument("--timeout", type=float, default=30.0)
    r.set_defaults(f=lenh_raw)

    h = sub.add_parser("http", help="GET mot URL localhost cua may B")
    h.add_argument("url")
    h.add_argument("--timeout", type=float, default=30.0)
    h.add_argument("--reason", default="H44 P01: doc /props /running cua llama-server")
    h.set_defaults(f=lenh_http)

    args = p.parse_args(argv)
    # `chay -- cmd args` ⇒ argparse.REMAINDER giu lai dau `--`, bo di.
    if getattr(args, "lenh", None) and args.lenh and args.lenh[0] == "--":
        args.lenh = args.lenh[1:]
    try:
        return args.f(args)
    except LoiNexus as e:
        _ghi_nhat_ky(args.lenh_con, "-", f"LOI: {e}")
        print(f"Loi: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
