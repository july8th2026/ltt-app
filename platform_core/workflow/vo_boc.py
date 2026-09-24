"""**Vỏ bọc** cho mã piece không tin cậy: AppContainer + Job Object — spec §11.2.

🔴 **Đây là RANH GIỚI AN NINH của cả phase connector.** Mọi lớp khác (vá
   `net.Socket.prototype.connect` trong preload, undici dispatcher, `dns.lookup`)
   là **phòng thủ theo chiều sâu**: chúng chặn piece *viết ẩu*, không chặn piece
   *cố ý*. Đo được, hai lần, ở hai spike:

       node -r preload-socket-only.js piece-https.js          -> EGRESS_BLOCKED
       node -r preload-socket-only.js piece-child-process.js  -> CHILD_REACHED 200

   `-r <preload>` là cờ của **tiến trình đó**; nó không đi theo `spawn`. Cùng
   điều đội Activepieces nói trong `activepieces/activepieces#11547`, dẫn
   CVE-2025-68668 (n8n, Pyodide sandbox escape, CVSS 9.9).

## Vì sao AppContainer, ⛔ không phải tường lửa

Spike P6B đo bốn hướng (`docs/superpowers/reports/p6b-ranh-gioi-os/spike.md`):

| | piece thường | `spawn` con | IP trần | native |
|---|---|---|---|---|
| tường lửa theo **đường dẫn** | chặn | chặn | chặn | 🔴 **THỦNG** (`curl.exe`) |
| tường lửa theo **SID** | chặn | chặn | chặn | chặn — nhưng **cần một tài khoản Windows mới** |
| **AppContainer, 0 capability** | chặn | **chặn: `spawn` trả `ENOENT`** | chặn | chặn |
| WSL2 netns | chặn | chặn | chặn | 🔴 thủng qua WSL interop |

⭐ Quyết định: AppContainer, vì nó **không cần một luật tường lửa nào và không
   cần tài khoản nào**. Máy A là **production đang phục vụ khách VPS** và phải
   giữ bốn đường ra (SSH 22 → cổng vào OVH · Proxmox 8006 · `*.api.ovh.com` ·
   HTTPS của `cloudflared`, cộng WireGuard UDP 42817). Một cơ chế ràng buộc
   **tiến trình được phóng vào vỏ** không đụng tới lưu lượng của máy; một luật
   tường lửa đặt sai phạm vi thì cắt cụm VPS đang có khách trả tiền.

## Đường ra hợp lệ đi bằng gì

Vỏ **không** có capability `internetClient` ⇒ piece không tự ra Internet được.
Lưu lượng hợp lệ đi qua **proxy trên loopback** (`proxy_egress.py`) chạy NGOÀI
vỏ, nơi danh sách miền được áp: `ap_dung_loopback()` mở đúng loopback cho SID
của vỏ và **không mở gì khác**. Mô hình này chính là thứ `activepieces#11547`
đề xuất (*"lọc domain ngoài tiến trình"*), khác ở chỗ ta không cần microVM.

⚠️ **IPv6: CHƯA BIẾT, ⛔ không phải "đã chặn".** Máy A không có địa chỉ IPv6
   toàn cục và không có route `::/0` — nên **đối chứng cũng hỏng**: một lượt
   `curl -6` trả `000` ngay cả khi không có vỏ. Kênh đó chưa nói được gì. Muốn
   phủ phải đo trên máy có IPv6 thật.

## Giá phải trả — đã đo, phải biết trước khi sửa tệp này

- Piece **không** chạy được tiến trình con (`spawn` → `ENOENT`). Đó là tính
  năng, không phải lỗi; piece nào cần `spawn` sẽ hỏng và phải bị loại.
- `node` cần `--preserve-symlinks-main`: thiếu nó Node `realpath` lên tận gốc
  và chết `EPERM: lstat 'C:\'`.
- **Ống (pipe) treo cứng trong vỏ** — đo ở spike. Nên giao thức §11.1 đi bằng
  **tệp** (`vao.json` / `ra.json`) chứ không phải stdin/stdout. Đây là chỗ mã
  này **cố ý lệch spec**, và lý do là một phép đo, không phải sở thích.
- Thư mục runner + `tmp_dir` phải cấp ACL cho SID của vỏ.
"""
from __future__ import annotations

import ctypes
import os
import subprocess
from ctypes import wintypes
from dataclasses import dataclass, field

from platform_core.workflow import job_object

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
userenv = ctypes.WinDLL("userenv", use_last_error=True)

EXTENDED_STARTUPINFO_PRESENT = 0x00080000
CREATE_UNICODE_ENVIRONMENT = 0x00000400
CREATE_SUSPENDED = 0x00000004
CREATE_NO_WINDOW = 0x08000000
PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES = 0x00020009
STARTF_USESTDHANDLES = 0x00000100
GENERIC_WRITE = 0x40000000
GENERIC_READ = 0x80000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
CREATE_ALWAYS = 2
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80
SE_GROUP_ENABLED = 0x00000004
ERROR_ALREADY_EXISTS_HR = 0x800700B7

#: SID capability cố định (Microsoft Learn, *well-known capability SIDs*).
#: ⛔ Danh sách ĐÓNG và cố tình ngắn: mỗi dòng thêm vào đây là một lỗ mở cho
#:    mã không tin cậy. `internetClient` chỉ có mặt để **đối chứng** đo được —
#:    đường production dùng `caps=()`.
SID_CAPABILITY = {
    "internetClient": "S-1-15-3-1",
    "privateNetworkClientServer": "S-1-15-3-3",
}

#: Tên vỏ mặc định. Một tên = một hồ sơ AppContainer = một SID ổn định, nên
#: ACL cấp một lần dùng được cho mọi lượt chạy.
TEN_VO_MAC_DINH = "ltt-connector-runner"


class LoiVoBoc(OSError):
    """Không dựng được vỏ. ⛔ Không có đường lui "chạy không vỏ": chạy mã
    piece ngoài vỏ trên máy production là đúng thứ phase này sinh ra để cấm."""


class SID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", wintypes.DWORD)]


class SECURITY_CAPABILITIES(ctypes.Structure):
    _fields_ = [("AppContainerSid", ctypes.c_void_p),
                ("Capabilities", ctypes.POINTER(SID_AND_ATTRIBUTES)),
                ("CapabilityCount", wintypes.DWORD),
                ("Reserved", wintypes.DWORD)]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR),
                ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
                ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
                ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
                ("dwXCountChars", wintypes.DWORD),
                ("dwYCountChars", wintypes.DWORD),
                ("dwFillAttribute", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("wShowWindow", wintypes.WORD),
                ("cbReserved2", wintypes.WORD),
                ("lpReserved2", ctypes.POINTER(ctypes.c_byte)),
                ("hStdInput", wintypes.HANDLE),
                ("hStdOutput", wintypes.HANDLE),
                ("hStdError", wintypes.HANDLE)]


class STARTUPINFOEXW(ctypes.Structure):
    _fields_ = [("StartupInfo", STARTUPINFOW),
                ("lpAttributeList", ctypes.c_void_p)]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
                ("dwProcessId", wintypes.DWORD),
                ("dwThreadId", wintypes.DWORD)]


class SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("nLength", wintypes.DWORD),
                ("lpSecurityDescriptor", ctypes.c_void_p),
                ("bInheritHandle", wintypes.BOOL)]


advapi32.ConvertSidToStringSidW.argtypes = [
    ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
advapi32.ConvertStringSidToSidW.argtypes = [
    wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)]
advapi32.ConvertStringSidToSidW.restype = wintypes.BOOL
userenv.CreateAppContainerProfile.argtypes = [
    wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR,
    ctypes.POINTER(SID_AND_ATTRIBUTES), wintypes.DWORD,
    ctypes.POINTER(ctypes.c_void_p)]
userenv.CreateAppContainerProfile.restype = ctypes.c_long
userenv.DeriveAppContainerSidFromAppContainerName.argtypes = [
    wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)]
userenv.DeriveAppContainerSidFromAppContainerName.restype = ctypes.c_long
userenv.DeleteAppContainerProfile.argtypes = [wintypes.LPCWSTR]
userenv.DeleteAppContainerProfile.restype = ctypes.c_long


def _sid_sang_chuoi(psid) -> str:
    ra = wintypes.LPWSTR()
    if not advapi32.ConvertSidToStringSidW(psid, ctypes.byref(ra)):
        raise ctypes.WinError(ctypes.get_last_error())
    return ra.value


def _chuoi_sang_sid(s: str):
    psid = ctypes.c_void_p()
    if not advapi32.ConvertStringSidToSidW(s, ctypes.byref(psid)):
        raise ctypes.WinError(ctypes.get_last_error())
    return psid


def sid_cua_vo(ten: str = TEN_VO_MAC_DINH) -> str:
    """SID chuỗi của vỏ, tạo hồ sơ nếu chưa có. Luỹ đẳng."""
    psid = ctypes.c_void_p()
    hr = userenv.CreateAppContainerProfile(
        ten, ten, "LTT connector runner (ma piece khong tin cay)",
        None, 0, ctypes.byref(psid))
    if hr & 0xFFFFFFFF == ERROR_ALREADY_EXISTS_HR:
        hr2 = userenv.DeriveAppContainerSidFromAppContainerName(
            ten, ctypes.byref(psid))
        if hr2 != 0:
            raise LoiVoBoc(f"DeriveAppContainerSid hr=0x{hr2 & 0xFFFFFFFF:08X}")
    elif hr != 0:
        raise LoiVoBoc(f"CreateAppContainerProfile hr=0x{hr & 0xFFFFFFFF:08X}")
    return _sid_sang_chuoi(psid)


def xoa_vo(ten: str = TEN_VO_MAC_DINH) -> int:
    """Xoá hồ sơ AppContainer. Dùng khi gỡ; luỹ đẳng."""
    return int(userenv.DeleteAppContainerProfile(ten)) & 0xFFFFFFFF


def cap_acl(duong: str, sid: str, quyen: str = "(OI)(CI)(RX)") -> None:
    """Cấp quyền đọc/chạy cho SID của vỏ trên MỘT thư mục.

    ⛔ Cấp cho **SID của vỏ**, ⛔ không cho `ALL APPLICATION PACKAGES`
       (`S-1-15-2-1`): cái sau mở thư mục cho **mọi** ứng dụng đóng gói trên
       máy, tức rộng hơn hẳn thứ ta cần. Hẹp hơn thì đo vẫn ra cùng kết quả —
       spike đã chạy cả hai.
    """
    r = subprocess.run(["icacls", duong, "/grant", f"*{sid}:{quyen}", "/T",
                        "/C", "/Q"], capture_output=True, text=True)
    if r.returncode != 0:
        raise LoiVoBoc(f"icacls that bai tren {duong}: {r.stderr.strip()[:300]}")


def go_acl(duong: str, sid: str) -> None:
    """Gỡ ACL đã cấp. Dùng trong đường dọn dẹp / lệnh gỡ của báo cáo."""
    subprocess.run(["icacls", duong, "/remove", f"*{sid}", "/T", "/C", "/Q"],
                   capture_output=True, text=True)


def ap_dung_loopback(sid: str) -> bool:
    """Miễn trừ loopback cho vỏ ⇒ piece nối được **127.0.0.1 và chỉ thế**.

    ⭐ Project Zero, *Understanding Network Access in Windows AppContainers*
       (2021-08): loopback bị chặn mặc định **độc lập** với capability, miễn
       trừ bằng `CheckNetIsolation.exe LoopbackExempt`. Nên một vỏ **không có**
       `internetClient` **có** miễn trừ loopback = đúng hình dạng ta cần: ra
       Internet chỉ qua proxy của ta, nơi danh sách miền được áp.

    Trả `True` nếu lệnh chạy được. ⚠️ Cần quyền quản trị; gọi nơi không có
    quyền sẽ trả `False` và **người gọi phải coi đó là lỗi**, không phải cảnh
    báo — không có loopback thì mọi lệnh connector sẽ hết giờ.
    """
    r = subprocess.run(["CheckNetIsolation.exe", "LoopbackExempt", "-a",
                        f"-p={sid}"], capture_output=True, text=True)
    return r.returncode == 0


def go_loopback(sid: str) -> bool:
    r = subprocess.run(["CheckNetIsolation.exe", "LoopbackExempt", "-d",
                        f"-p={sid}"], capture_output=True, text=True)
    return r.returncode == 0


@dataclass
class KetQuaVo:
    ma_thoat: int
    het_gio: bool
    so_lieu: dict = field(default_factory=dict)
    sid: str = ""


def _khoi_moi_truong(moi_truong: dict) -> ctypes.Array:
    dem = "".join(f"{k}={v}\0" for k, v in moi_truong.items()) + "\0"
    return ctypes.create_unicode_buffer(dem)


def _dong_lenh(argv) -> str:
    # ⛔ Không `subprocess.list2cmdline` — nó không phải hợp đồng công khai cho
    #    `CreateProcessW` và đã đổi hành vi giữa các bản Python. Bọc ngoặc kép
    #    tường minh, và cấm ngoặc kép trong tham số (runner chỉ nhận đường dẫn).
    ra = []
    for a in argv:
        s = str(a)
        if '"' in s:
            raise LoiVoBoc(f"tham so chua dau nhay kep: {s!r}")
        ra.append(f'"{s}"')
    return " ".join(ra)


def chay(argv, *, ra_log: str, ten_vo: str = TEN_VO_MAC_DINH,
         caps=(), moi_truong=None, han_ms: int = 120000,
         bo_nho_mb: int = job_object.BO_NHO_MAC_DINH_MB,
         so_tien_trinh: int = job_object.SO_TIEN_TRINH_MAC_DINH,
         thu_muc: str = "") -> KetQuaVo:
    """Chạy `argv` **bên trong** vỏ, ghi stdout+stderr vào `ra_log`.

    `han_ms` là thời gian **trôi**, không phải CPU (xem `job_object`). Hết giờ
    ⇒ `TerminateJobObject` giết **cả cây**, không chỉ tiến trình gốc.
    """
    sid = sid_cua_vo(ten_vo)
    psid = _chuoi_sang_sid(sid)

    mang_cap = None
    if caps:
        arr = (SID_AND_ATTRIBUTES * len(caps))()
        for i, ten in enumerate(caps):
            if ten not in SID_CAPABILITY:
                raise LoiVoBoc(f"capability khong nam trong danh sach dong: {ten!r}")
            arr[i].Sid = _chuoi_sang_sid(SID_CAPABILITY[ten])
            arr[i].Attributes = SE_GROUP_ENABLED
        mang_cap = arr

    sc = SECURITY_CAPABILITIES()
    sc.AppContainerSid = psid
    sc.Capabilities = (ctypes.cast(mang_cap, ctypes.POINTER(SID_AND_ATTRIBUTES))
                       if mang_cap else None)
    sc.CapabilityCount = len(caps)
    sc.Reserved = 0

    kich_thuoc = ctypes.c_size_t(0)
    kernel32.InitializeProcThreadAttributeList(None, 1, 0,
                                               ctypes.byref(kich_thuoc))
    bo_dem = ctypes.create_string_buffer(kich_thuoc.value)
    if not kernel32.InitializeProcThreadAttributeList(
            bo_dem, 1, 0, ctypes.byref(kich_thuoc)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not kernel32.UpdateProcThreadAttribute(
            bo_dem, 0, ctypes.c_size_t(PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES),
            ctypes.byref(sc), ctypes.sizeof(sc), None, None):
        raise ctypes.WinError(ctypes.get_last_error())

    sa = SECURITY_ATTRIBUTES()
    sa.nLength = ctypes.sizeof(sa)
    sa.lpSecurityDescriptor = None
    sa.bInheritHandle = True

    h_out = kernel32.CreateFileW(
        ra_log, GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE,
        ctypes.byref(sa), CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, None)
    if h_out in (None, wintypes.HANDLE(-1).value):
        raise ctypes.WinError(ctypes.get_last_error())
    # ⛔ stdin là NUL, ⛔ không phải một ống: ống treo cứng trong vỏ (spike).
    #    Giao thức §11.1 đi bằng TỆP — xem docstring mô-đun.
    h_in = kernel32.CreateFileW(
        "NUL", GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE,
        ctypes.byref(sa), OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None)

    si = STARTUPINFOEXW()
    si.StartupInfo.cb = ctypes.sizeof(STARTUPINFOEXW)
    si.StartupInfo.dwFlags = STARTF_USESTDHANDLES
    si.StartupInfo.hStdInput = h_in
    si.StartupInfo.hStdOutput = h_out
    si.StartupInfo.hStdError = h_out
    si.lpAttributeList = ctypes.cast(bo_dem, ctypes.c_void_p)

    moi = dict(moi_truong or {})
    khoi_env = _khoi_moi_truong(moi) if moi else None

    pi = PROCESS_INFORMATION()
    lenh = ctypes.create_unicode_buffer(_dong_lenh(argv))
    h_job = job_object.tao(bo_nho_mb=bo_nho_mb, so_tien_trinh=so_tien_trinh)
    ok = kernel32.CreateProcessW(
        None, lenh, None, None, True,
        (EXTENDED_STARTUPINFO_PRESENT | CREATE_UNICODE_ENVIRONMENT
         | CREATE_SUSPENDED | CREATE_NO_WINDOW),
        khoi_env, thu_muc or None, ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        loi = ctypes.get_last_error()
        kernel32.CloseHandle(h_out)
        kernel32.CloseHandle(h_in)
        kernel32.DeleteProcThreadAttributeList(bo_dem)
        raise LoiVoBoc(
            f"CreateProcessW that bai win32={loi} "
            f"({ctypes.WinError(loi).strerror})")

    try:
        # ⭐ Gán job KHI TIẾN TRÌNH CÒN TREO. Gán sau `ResumeThread` để hở một
        #    khoảng trong đó mã không tin cậy chạy NGOÀI mọi hạn mức.
        job_object.gan(h_job, pi.hProcess)
        if kernel32.ResumeThread(pi.hThread) == 0xFFFFFFFF:
            raise ctypes.WinError(ctypes.get_last_error())
        doi = kernel32.WaitForSingleObject(pi.hProcess, int(han_ms))
        het_gio = doi != 0
        if het_gio:
            job_object.giet(h_job, 9)
            kernel32.WaitForSingleObject(pi.hProcess, 5000)
        ma = wintypes.DWORD()
        kernel32.GetExitCodeProcess(pi.hProcess, ctypes.byref(ma))
        try:
            so = job_object.so_lieu(h_job)
        except Exception:  # noqa: BLE001 — số đo không được làm hỏng lượt chạy
            so = {}
        return KetQuaVo(ma_thoat=int(ma.value), het_gio=het_gio,
                        so_lieu=so, sid=sid)
    finally:
        kernel32.CloseHandle(pi.hProcess)
        kernel32.CloseHandle(pi.hThread)
        kernel32.CloseHandle(h_out)
        kernel32.CloseHandle(h_in)
        kernel32.DeleteProcThreadAttributeList(bo_dem)
        # ⭐ Đóng handle job SAU CÙNG: `KILL_ON_JOB_CLOSE` giết mọi tiến trình
        #    còn sót ngay tại đây, kể cả khi lượt này ném giữa chừng.
        kernel32.CloseHandle(int(h_job))


def moi_truong_toi_thieu(*, proxy: str = "", them=None) -> dict:
    """Môi trường cho tiến trình runner. ⛔ **KHÔNG** kế thừa môi trường của
    worker: môi trường của nền tảng mang bí mật (`app.env` nạp 97 biến vào
    tiến trình worker), và mã piece là mã của bên thứ ba.
    """
    ra = {
        # 🔴 `LOCALAPPDATA` LÀ BẮT BUỘC — đo 24/09, ⛔ không phải suy luận.
        #    Một khối môi trường tuỳ biến thiếu nó làm `CreateProcessW` của
        #    một tiến trình AppContainer trả **win32=203
        #    ERROR_ENVVAR_NOT_FOUND** ("The system could not find the
        #    environment option that was entered") — một câu lỗi không hề nhắc
        #    tới AppContainer, nên nó tốn một vòng dò. Spike P6B không gặp vì
        #    nó truyền `lpEnvironment=NULL` (kế thừa 90 biến của worker), tức
        #    đúng thứ ta KHÔNG được làm: môi trường worker mang bí mật.
        #    Đo thu hẹp: chỉ `LOCALAPPDATA` là đủ cho `CreateProcessW`;
        #    `SystemRoot` là thứ Node cần thêm (thiếu nó Node thoát mã 134).
        "LOCALAPPDATA": os.environ.get(
            "LOCALAPPDATA", os.path.expandvars(r"%USERPROFILE%\AppData\Local")),
        "SystemRoot": os.environ.get("SystemRoot", r"C:\Windows"),
        "SystemDrive": os.environ.get("SystemDrive", "C:"),
        "windir": os.environ.get("windir", r"C:\Windows"),
        "NODE_OPTIONS": "--max-old-space-size=384",
        # Node 24: bắt `fetch`/undici đi theo biến proxy của môi trường.
        "NODE_USE_ENV_PROXY": "1",
    }
    if proxy:
        ra["HTTP_PROXY"] = proxy
        ra["HTTPS_PROXY"] = proxy
        ra["http_proxy"] = proxy
        ra["https_proxy"] = proxy
        ra["NO_PROXY"] = ""
    ra.update(them or {})
    return ra


__all__ = ["KetQuaVo", "LoiVoBoc", "SID_CAPABILITY", "TEN_VO_MAC_DINH",
           "ap_dung_loopback", "cap_acl", "chay", "go_acl", "go_loopback",
           "moi_truong_toi_thieu", "sid_cua_vo", "xoa_vo"]
