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
import pathlib
import sys

GOC = pathlib.Path(__file__).resolve().parents[1]
THU_MUC_GUI = pathlib.Path(__file__).resolve().parent / "gui"


def _nap_loi():
    """Nap `cam_cli` nhu mot module, chay duoc ca khi da dong goi thanh .exe."""
    try:
        import cam_cli                                        # noqa: F401
        return cam_cli
    except ImportError:
        pass
    spec = importlib.util.spec_from_file_location(
        "cam_cli", pathlib.Path(__file__).resolve().parent / "cam_cli.py")
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


class Cau:
    """Cầu nối JS -> Python. **Bốn hàm, không hơn.**"""

    def __init__(self, loi):
        self._loi = loi

    # ── mỗi hàm bắt output của lõi rồi trả về cho JS, thay vì in ra ──────────
    def _chay(self, ham, *a):
        import contextlib
        import io
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                ma = ham(*a)
        except Exception as exc:                              # noqa: BLE001
            # ⛔ Mot ngoai le KHONG duoc lam cua so trang. Khach phai thay chuyen
            #    gi da xay ra, ke ca khi do la mot loi ta chua nghi toi.
            return {"ma": 1, "dong": [f"[LOI] {type(exc).__name__}: {exc}"]}
        return {"ma": ma, "dong": buf.getvalue().splitlines()}

    def xem(self) -> dict:
        return self._chay(self._loi.lenh_xem, _Args())

    def cam(self, khoa: str, toan_cuc: bool) -> dict:
        return self._chay(self._loi.lenh_cam,
                          _Args(khoa=(khoa or "").strip(),
                                goc=self._loi.GOC_MAC_DINH,
                                toan_cuc=bool(toan_cuc)))

    def go(self) -> dict:
        return self._chay(self._loi.lenh_go, _Args())

    def kiem(self) -> dict:
        return self._chay(self._loi.lenh_kiem, _Args())


#: Danh sách **chốt cứng** những gì cầu nối được phép lộ ra. `test_284` so danh
#: sách này với các phương thức công khai thật của `Cau`; thêm hàm thứ năm mà
#: quên khai ở đây là test đỏ.
HAM_CHO_PHEP = ("xem", "cam", "go", "kiem")


def main(argv=None) -> int:
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
        "LTT Studios - Cam cong cu viet ma",
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
