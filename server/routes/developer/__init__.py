"""``/developers`` — the portal where a customer manages their API keys.

This is the **session** surface, not the API one, and the difference is the
whole point:

* it authenticates with the platform's login session and therefore **must** have
  CSRF protection on every state-changing POST — a browser attaches session
  cookies to cross-site requests automatically. ``/api/v1`` is the opposite: it
  refuses cookies and needs no CSRF (see ``server/api/auth.py``);
* it is the only place a developer key is ever created, and the plaintext is
  shown **once**, on the response to the request that created it. A refresh
  cannot bring it back, because nothing on the server can reproduce it.

Deliberately not here: any provider credential. ``platform_core.api_keys`` holds
the platform's own keys for Gemini and friends; a customer has no business
seeing that they exist, let alone their preview.


⛔ Import cac module nhom duoi day la BAT BUOC, khong phai thua: handler chi
   duoc dang ky vao `router` khi module chua no duoc NAP. Bo mot dong la lam
   bien mat lang le mot nhom route — `test_197` chot 32 route de chan dieu do.
"""
from server.routes.developer._chung import (  # noqa: F401
    CHA_CUA, MUC_CON, NHOM_NAV, RECENT_JOBS, SECTIONS, TRANG_CONG_KHAI,
    _overview_counts, require_account, router, tai_khoan_tuy_chon)
from server.routes.developer import (  # noqa: F401
    cong_cu, khoa_du_an, rieng_tu, su_dung, trang, webhook)

#: ⛔ BE MAT CU PHAI GIU NGUYEN. Truoc khi che, `server/routes/developer.py` la
#:    mot module, nen `from server.routes.developer import SECTIONS` chay duoc.
#:    Che thanh package ma khong xuat lai cac ten nay se lam GAY nhung noi goi
#:    tu ben ngoai — va no gay o cho khong lien quan gi den viec che.
#:
#:    Da dinh that ngay 26/08: `test_197` va `test_300` do voi ImportError ngay
#:    luot chay dau tien sau khi che.
#:
#: ⭐ Mot lan che dung nghia la NGUOI GOI KHONG BIET no da xay ra. Danh sach nay
#:    la thu bao dam dieu do.
__all__ = ["router", "SECTIONS", "TRANG_CONG_KHAI", "NHOM_NAV", "CHA_CUA",
           "MUC_CON", "RECENT_JOBS", "require_account", "tai_khoan_tuy_chon"]
