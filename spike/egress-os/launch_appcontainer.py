"""Chay mot lenh BEN TRONG mot AppContainer, khong tao tai khoan Windows, khong doi
cai dat he thong, khong dat luat tuong lua nao.

Y tuong do: AppContainer KHONG co capability `internetClient` (S-1-15-3-1) thi WFP
chan egress ngay tu goc, va token AppContainer di theo tien trinh con -> tra loi
duoc dung cau hoi cua spike: "spawn con co thoat ra khong?".

Dung:
    python launch_appcontainer.py --ten <ten-container> --caps none|internetClient \
        --ra <tep-ghi-stdout> -- <duong-dan-exe> [tham so...]

Don dep (xoa profile AppContainer da tao):
    python launch_appcontainer.py --xoa <ten-container>
"""

import argparse
import ctypes
import os
import sys
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
userenv = ctypes.WinDLL("userenv", use_last_error=True)

EXTENDED_STARTUPINFO_PRESENT = 0x00080000
CREATE_UNICODE_ENVIRONMENT = 0x00000400
PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES = 0x00020009
STARTF_USESTDHANDLES = 0x00000100
GENERIC_WRITE = 0x40000000
GENERIC_READ = 0x80000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
CREATE_ALWAYS = 2
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80
INFINITE = 0xFFFFFFFF
ERROR_ALREADY_EXISTS_HR = 0x800700B7  # HRESULT_FROM_WIN32(ERROR_ALREADY_EXISTS)


class SID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", wintypes.DWORD)]


class SECURITY_CAPABILITIES(ctypes.Structure):
    _fields_ = [
        ("AppContainerSid", ctypes.c_void_p),
        ("Capabilities", ctypes.POINTER(SID_AND_ATTRIBUTES)),
        ("CapabilityCount", wintypes.DWORD),
        ("Reserved", wintypes.DWORD),
    ]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.POINTER(ctypes.c_byte)),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class STARTUPINFOEXW(ctypes.Structure):
    _fields_ = [("StartupInfo", STARTUPINFOW), ("lpAttributeList", ctypes.c_void_p)]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


class SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("nLength", wintypes.DWORD),
        ("lpSecurityDescriptor", ctypes.c_void_p),
        ("bInheritHandle", wintypes.BOOL),
    ]


advapi32.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
advapi32.ConvertStringSidToSidW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)]
advapi32.ConvertStringSidToSidW.restype = wintypes.BOOL

userenv.CreateAppContainerProfile.argtypes = [
    wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR,
    ctypes.POINTER(SID_AND_ATTRIBUTES), wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p),
]
userenv.CreateAppContainerProfile.restype = ctypes.c_long
userenv.DeriveAppContainerSidFromAppContainerName.argtypes = [
    wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)
]
userenv.DeriveAppContainerSidFromAppContainerName.restype = ctypes.c_long
userenv.DeleteAppContainerProfile.argtypes = [wintypes.LPCWSTR]
userenv.DeleteAppContainerProfile.restype = ctypes.c_long


def sid_to_str(psid):
    out = wintypes.LPWSTR()
    if not advapi32.ConvertSidToStringSidW(psid, ctypes.byref(out)):
        raise ctypes.WinError(ctypes.get_last_error())
    return out.value


def str_to_sid(s):
    psid = ctypes.c_void_p()
    if not advapi32.ConvertStringSidToSidW(s, ctypes.byref(psid)):
        raise ctypes.WinError(ctypes.get_last_error())
    return psid


CAP_SIDS = {
    # SID capability co dinh, tra tu tai lieu Microsoft (well-known capability SIDs)
    "internetClient": "S-1-15-3-1",
    "internetClientServer": "S-1-15-3-2",
    "privateNetworkClientServer": "S-1-15-3-3",
}


def tao_hoac_lay_sid(ten):
    psid = ctypes.c_void_p()
    hr = userenv.CreateAppContainerProfile(ten, ten, "spike p6b ranh gioi egress", None, 0, ctypes.byref(psid))
    if hr & 0xFFFFFFFF == ERROR_ALREADY_EXISTS_HR:
        hr2 = userenv.DeriveAppContainerSidFromAppContainerName(ten, ctypes.byref(psid))
        if hr2 != 0:
            raise OSError(f"DeriveAppContainerSidFromAppContainerName hr=0x{hr2 & 0xFFFFFFFF:08X}")
    elif hr != 0:
        raise OSError(f"CreateAppContainerProfile hr=0x{hr & 0xFFFFFFFF:08X}")
    return psid


def chay(ten, caps, ra, argv, cho_ms=60000):
    psid = tao_hoac_lay_sid(ten)
    sid_str = sid_to_str(psid)

    cap_array = None
    cap_count = 0
    if caps and caps != "none":
        names = [c.strip() for c in caps.split(",") if c.strip()]
        arr = (SID_AND_ATTRIBUTES * len(names))()
        for i, n in enumerate(names):
            if n not in CAP_SIDS:
                raise SystemExit(f"capability chua biet: {n}")
            arr[i].Sid = str_to_sid(CAP_SIDS[n])
            arr[i].Attributes = 0x00000004  # SE_GROUP_ENABLED
        cap_array = arr
        cap_count = len(names)

    sc = SECURITY_CAPABILITIES()
    sc.AppContainerSid = psid
    sc.Capabilities = ctypes.cast(cap_array, ctypes.POINTER(SID_AND_ATTRIBUTES)) if cap_array else None
    sc.CapabilityCount = cap_count
    sc.Reserved = 0

    size = ctypes.c_size_t(0)
    kernel32.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(size))
    buf = ctypes.create_string_buffer(size.value)
    if not kernel32.InitializeProcThreadAttributeList(buf, 1, 0, ctypes.byref(size)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not kernel32.UpdateProcThreadAttribute(
        buf, 0, ctypes.c_size_t(PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES),
        ctypes.byref(sc), ctypes.sizeof(sc), None, None
    ):
        raise ctypes.WinError(ctypes.get_last_error())

    sa = SECURITY_ATTRIBUTES()
    sa.nLength = ctypes.sizeof(sa)
    sa.lpSecurityDescriptor = None
    sa.bInheritHandle = True

    h_out = kernel32.CreateFileW(
        ra, GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, ctypes.byref(sa),
        CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, None,
    )
    if h_out == wintypes.HANDLE(-1).value or h_out is None:
        raise ctypes.WinError(ctypes.get_last_error())
    h_in = kernel32.CreateFileW(
        "NUL", GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, ctypes.byref(sa),
        OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None,
    )

    si = STARTUPINFOEXW()
    si.StartupInfo.cb = ctypes.sizeof(STARTUPINFOEXW)
    si.StartupInfo.dwFlags = STARTF_USESTDHANDLES
    si.StartupInfo.hStdInput = h_in
    si.StartupInfo.hStdOutput = h_out
    si.StartupInfo.hStdError = h_out
    si.lpAttributeList = ctypes.cast(buf, ctypes.c_void_p)

    pi = PROCESS_INFORMATION()
    cmd = ctypes.create_unicode_buffer(" ".join(f'"{a}"' for a in argv))
    ok = kernel32.CreateProcessW(
        None, cmd, None, None, True,
        EXTENDED_STARTUPINFO_PRESENT | CREATE_UNICODE_ENVIRONMENT,
        None, None, ctypes.byref(si), ctypes.byref(pi),
    )
    if not ok:
        err = ctypes.get_last_error()
        kernel32.CloseHandle(h_out)
        print(f"APPCONTAINER_SID={sid_str}")
        print(f"CREATEPROCESS_FAILED win32={err} ({ctypes.WinError(err).strerror})")
        return 3

    doi = kernel32.WaitForSingleObject(pi.hProcess, cho_ms)
    if doi != 0:  # WAIT_OBJECT_0 = 0; khac 0 nghia la het gio -> giet cho khoi mo coi
        kernel32.TerminateProcess(pi.hProcess, 9)
        kernel32.WaitForSingleObject(pi.hProcess, 5000)
        print(f"HET_GIO sau {cho_ms} ms - da TerminateProcess")
    code = wintypes.DWORD()
    kernel32.GetExitCodeProcess(pi.hProcess, ctypes.byref(code))
    kernel32.CloseHandle(pi.hProcess)
    kernel32.CloseHandle(pi.hThread)
    kernel32.CloseHandle(h_out)
    kernel32.CloseHandle(h_in)
    kernel32.DeleteProcThreadAttributeList(buf)

    print(f"APPCONTAINER_SID={sid_str}")
    print(f"EXITCODE={code.value}")
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ten", default="ltt-p6b-spike")
    p.add_argument("--caps", default="none")
    p.add_argument("--ra", default=None)
    p.add_argument("--xoa", default=None)
    p.add_argument("--chi-sid", action="store_true")
    p.add_argument("--cho-ms", type=int, default=60000)
    p.add_argument("lenh", nargs=argparse.REMAINDER)
    a = p.parse_args()

    if a.xoa:
        hr = userenv.DeleteAppContainerProfile(a.xoa)
        print(f"DeleteAppContainerProfile({a.xoa}) hr=0x{hr & 0xFFFFFFFF:08X}")
        return 0
    if a.chi_sid:
        print(sid_to_str(tao_hoac_lay_sid(a.ten)))
        return 0

    argv = [x for x in a.lenh if x != "--"]
    if not argv:
        p.error("thieu lenh sau --")
    if not a.ra:
        p.error("thieu --ra")
    return chay(a.ten, a.caps, os.path.abspath(a.ra), argv, a.cho_ms)


if __name__ == "__main__":
    sys.exit(main())
