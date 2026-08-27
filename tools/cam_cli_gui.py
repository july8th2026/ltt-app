"""cam_cli_gui.py - vo GUI cho `cam_cli`. (C15-GUI / U2)

    python tools\\cam_cli_gui.py

* VO MONG. Moi nghiep vu nam trong `cam_cli.py` (da co 12 test, trong do co mot
  test chot rang GO RA tra tep ve BANG TUNG BYTE). Tep nay chi lam ba viec: dung
  cua so, noi JS voi bon ham cua loi, va dich ket qua thanh mot dict cho JS doc.

! KHONG LAP LAI NGHIEP VU O DAY. Neu thay minh sap viet mot `if` ve cau hinh
  trong tep nay thi do la dau hieu no thuoc ve `cam_cli.py`, va no phai co test
  o do chu khong phai duoc goi qua mot cua so.

* VI SAO pywebview CHU KHONG PHAI MOT MAY CHU HTTP CUC BO.

  Cong cu nay ghi tep cau hinh trong thu muc nha cua khach VA giu mot khoa API
  tieu duoc tien. Mot may chu HTTP cuc bo lam hai viec do la dung mo ta cua mot
  lop lo hong da co CVE that (CVE-2025-49596, MCP Inspector): trang web bat ky
  ma khach dang mo co the goi sang `127.0.0.1`, va DNS rebinding lam token CSRF
  vo dung vi trinh duyet khong coi do la cross-origin.

  pywebview KHONG mo cong nao. No goi Python qua `window.pywebview.api` - mot
  cau noi TRONG TIEN TRINH. Khong co cong de quet, khong co Origin de gia.
  => Ca lop lo hong bien mat THEO THIET KE, khong phai theo phong thu.

! MAT TIEP XUC HEP CO CHU Y: DUNG BON HAM.
  Moi ham them vao `Cau` la mot ham ma JS goi duoc. Khong `doc_tep`, khong
  `chay_lenh`, khong `mo_thu_muc`. Co test chot dieu nay (test_284).
"""
from __future__ import annotations

import importlib.util
import os
import pathlib
import sys
import time

def _thu_muc_goc() -> pathlib.Path:
    """Thư mục chứa tài sản, đúng ở **cả hai** chế độ chạy.

    🔴 ĐÂY LÀ MỘT CÁI BẪY THẬT, không phải phòng xa. Khi đóng gói bằng
       PyInstaller, `__file__` **không còn** trỏ tới `tools/`: mã chạy từ trong
       gói và tài sản nằm ở `sys._MEIPASS`. Nên đường dẫn tính từ `__file__` sẽ
       trỏ vào chỗ không có gì.

    ⛔ Và hỏng theo kiểu tệ nhất: `.exe` **dựng thành công**, **chạy được**, cửa
       sổ **mở ra** — rồi **trắng trơn**. Không lỗi nào, không log nào. Cùng lớp
       với luật *"đừng neo đường dẫn bằng `Path(__file__).parents[n]`"* trong
       CLAUDE.md: nó hỏng lặng lẽ, trang vẫn trả 200, chỉ là vỏ trống.
    """
    tam = getattr(sys, "_MEIPASS", None)          # PyInstaller
    if tam:
        return pathlib.Path(tam)
    # !! Nuitka KHONG dat `sys.frozen` - no dat `__compiled__` o cap module. Ban
    #    dau toi kiem `sys.frozen` va ban Nuitka bao "dong bang: False"; no van
    #    tim thay tai san, nhung DO MAY: `__file__` tinh co tro dung vao .dist.
    #    Mot phep do noi sai ma van ra ket qua dung la thu de tin nham nhat.
    if "__compiled__" in globals() or getattr(sys, "frozen", False):
        return pathlib.Path(sys.executable).resolve().parent
    return pathlib.Path(__file__).resolve().parent


THU_MUC_GOC = _thu_muc_goc()
THU_MUC_GUI = THU_MUC_GOC / "gui"


def _nap_loi():
    """Nap `cam_cli` nhu mot module, chay duoc ca khi da dong goi thanh .exe."""
    try:
        import cam_cli                                        # noqa: F401
        return cam_cli
    except ImportError:
        pass
    spec = importlib.util.spec_from_file_location(
        "cam_cli", THU_MUC_GOC / "cam_cli.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Args:
    """`cam_cli` nhan mot object kieu argparse. Dung mot vo toi thieu thay vi
    doi chu ky ham cua loi - loi da co test, dung dong vao no vi mot cai vo."""

    def __init__(self, **kw):
        self.khoa = kw.get("khoa", "")
        self.goc = kw.get("goc", "")
        self.toan_cuc = kw.get("toan_cuc", False)
        self.vscode = kw.get("vscode", False)
        self.muc = kw.get("muc")


class Cau:
    """Cầu nối JS -> Python. **Bốn hàm, không hơn.**"""

    def __init__(self, loi):
        self._loi = loi

    # ── mỗi hàm bắt output của lõi rồi trả về cho JS, thay vì in ra ──────────
    def _chay(self, ham, *a):
        import contextlib
        import io
        buf = io.StringIO()
        bat_dau = time.monotonic()
        try:
            with contextlib.redirect_stdout(buf):
                ma = ham(*a)
        except Exception as exc:                              # noqa: BLE001
            # ⛔ Mot ngoai le KHONG duoc lam cua so trang. Khach phai thay chuyen
            #    gi da xay ra, ke ca khi do la mot loi ta chua nghi toi.
            return {"ma": 1, "dong": [f"[LOI] {type(exc).__name__}: {exc}"],
                    "giay": round(time.monotonic() - bat_dau, 2)}
        return {"ma": ma, "dong": buf.getvalue().splitlines(),
                "giay": round(time.monotonic() - bat_dau, 2)}

    def xem(self) -> dict:
        kq = self._chay(self._loi.lenh_xem, _Args())
        kq["phien_ban"] = getattr(self._loi, "PHIEN_BAN", "?")
        try:
            kq["trang_thai"] = self._loi.trang_thai_thuc()
        except Exception as exc:                              # noqa: BLE001
            kq["trang_thai"] = {"dang_cam": False, "muc": {},
                                  "loi": f"{type(exc).__name__}: {exc}"}
        return kq

    def cam(self, khoa: str, lua_chon=None) -> dict:
        chon = lua_chon if isinstance(lua_chon, dict) else {}
        muc = []
        codex = chon.get("codex", "profile")
        if codex == "profile":
            muc.append(self._loi.MUC_CODEX_CLI)
        elif codex == "vscode":
            muc.append(self._loi.MUC_CODEX_VSCODE)
        if chon.get("claude_cli", True):
            muc.append(self._loi.MUC_CLAUDE_CLI)
        if chon.get("claude_vscode", True):
            muc.append(self._loi.MUC_CLAUDE_VSCODE)
        if chon.get("claude_desktop", True):
            muc.append(self._loi.MUC_CLAUDE_DESKTOP)
        return self._chay(self._loi.lenh_cam,
                          _Args(khoa=(khoa or "").strip(),
                                goc=self._loi.GOC_MAC_DINH,
                                toan_cuc=bool(chon.get("toan_cuc", False)),
                                vscode=(codex == "vscode"), muc=muc))

    def go(self) -> dict:
        return self._chay(self._loi.lenh_go, _Args())

    def kiem(self) -> dict:
        return self._chay(self._loi.lenh_kiem, _Args())


#: Danh sách **chốt cứng** những gì cầu nối được phép lộ ra. `test_284` so danh
#: sách này với các phương thức công khai thật của `Cau`; thêm hàm thứ năm mà
#: quên khai ở đây là test đỏ.
HAM_CHO_PHEP = ("xem", "cam", "go", "kiem")


def tu_kiem() -> int:
    """Bản đóng gói **tự chứng minh** nó tìm được tài sản của mình.

    🔴 VÌ SAO CẦN. `.exe` dựng xong, Defender báo sạch, kích thước đúng — **và
       vẫn có thể mở ra một cửa sổ trắng** nếu `index.html` không đi theo gói
       hoặc đường dẫn tính sai ở chế độ đóng băng.

       Ba dấu hiệu quen thuộc (dựng OK / quét sạch / chạy được) **không cái nào**
       chạm tới câu hỏi thật: *tài sản có ở đó không?* Và một cửa sổ trắng thì
       không có log để mà đọc.

    ⇒ Chạy `LTTStudios-CamCLI.exe --tu-kiem` sau khi đóng gói. Nó không mở cửa
      sổ, chỉ in ra đường dẫn thật rồi trả mã 0/1 — dùng được trong kịch bản
      dựng, không cần ai ngồi nhìn.
    """
    print(f"che do dong bang : {bool(getattr(sys, 'frozen', False)) or bool(getattr(sys, '_MEIPASS', None))}")
    print(f"thu muc goc      : {THU_MUC_GOC}")
    thieu = []
    for ten in ("gui/index.html", "gui/ltt.css", "cam_cli.py"):
        d = THU_MUC_GOC / ten
        print(f"  {'[OK]' if d.exists() else '[THIEU]'} {ten}")
        if not d.exists():
            thieu.append(ten)
    try:
        loi = _nap_loi()
        print(f"  [OK] nap duoc loi (GOC_MAC_DINH={loi.GOC_MAC_DINH})")
    except Exception as exc:                                  # noqa: BLE001
        print(f"  [THIEU] khong nap duoc cam_cli: {exc}")
        thieu.append("cam_cli")
    try:
        import webview                                        # noqa: F401
        print("  [OK] co pywebview")
    except ImportError:
        print("  [!!] khong co pywebview - se lui ve dong lenh")
    if thieu:
        print("")
        print(f"THIEU: {thieu}. Ban dong goi nay se mo ra mot CUA SO TRANG.")
        return 1
    print("")
    print("Du tai san.")
    return 0


#: Lenh dong lenh ban dong goi nhan duoc, chuyen thang xuong loi.
#:
#: ⭐ VÌ SAO BẢN `.exe` PHẢI CHẠY ĐƯỢC TỪ DÒNG LỆNH, không chỉ mở cửa sổ.
#:
#:    ① **Thử được bản thật.** Không có đường này thì phép nghiệm thu chỉ chạy
#:       được trên mã nguồn, còn thứ khách thật sự cài thì không ai đo. Đó đúng
#:       là khoảng cách đã sinh ra mọi lỗi khó nhất trong dự án này.
#:    ② **Khách triển khai hàng loạt.** Một công ty cắm cho 20 máy không ngồi
#:       bấm 20 lần; họ chạy một dòng lệnh.
#:
#: ⛔ Nhưng **không** phát minh giao diện dòng lệnh thứ hai: chuyển thẳng cho
#:    `cam_cli.main()`, để chỉ có **một** định nghĩa về các lệnh.
LENH_DONG_LENH = ("xem", "cam", "go", "kiem")


def main(argv=None) -> int:
    tham = list(argv if argv is not None else sys.argv[1:])
    if "--tu-kiem" in tham:
        return tu_kiem()
    if tham and tham[0] in LENH_DONG_LENH:
        # Ban GUI duoc dung voi `--windowed`, nen stdout khong co console.
        # Launcher .bat dat duong dan nay de lay ket qua ve va in ra. Tep chi
        # chua trang thai, KHONG chua khoa (loi khong bao gio in khoa).
        tep_ra = (os.environ.get("LTT_CAM_CLI_OUTPUT") or "").strip()
        if not tep_ra:
            return _nap_loi().main(tham)
        import contextlib
        try:
            with pathlib.Path(tep_ra).open("w", encoding="utf-8") as f:
                with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
                    return _nap_loi().main(tham)
        except OSError:
            return 1
    try:
        import webview
    except ImportError:
        # ⛔ ĐƯỜNG LÙI (U5). Không có `pywebview` thì công cụ KHÔNG được chết:
        #    dòng lệnh đã chạy được và đã có test. GUI là tiện nghi.
        print("Khong co `pywebview` nen khong mo duoc cua so.")
        print("Cai bang:  pip install pywebview")
        print("Hoac dung dong lenh:  python tools\\cam_cli.py xem")
        return 2

    loi = _nap_loi()
    trang = THU_MUC_GUI / "index.html"
    if not trang.exists():
        print(f"Khong thay {trang}. Chay: python tools\\dong_goi_gui.py")
        return 1

    webview.create_window(
        f"LTT Studios - Cam cong cu viet ma  v{getattr(loi, 'PHIEN_BAN', '?')}",
        str(trang),
        js_api=Cau(loi),
        width=760, height=720, min_size=(680, 600),
        background_color="#08090a",          # khop --surface-canvas cua ltt.css
    )
    # `debug=False`: tat DevTools trong ban phat hanh. Mot cua so co DevTools la
    # mot cua so ai cung goi duoc cau noi bang tay.
    webview.start(debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
