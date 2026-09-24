"""OAuth2 Google cho kho credential — spec §9.3, plan wf-v2 P5c/T3.

## Ai làm gì

- **Chủ dự án** đăng ký app OAuth trên Google Cloud Console và dán
  `client_id`/`client_secret` vào `secrets/app.env`. Đó là việc **thủ công**:
  ⛔ Claude không tự tạo tài khoản, không tự nhập bí mật. Script dẫn từng bước:
  `tools/wizard_oauth_google.sh`.
- **Mô-đun này** dựng URL uỷ quyền, giữ `oauth_state`, đổi `code` lấy token và
  làm mới token. Nó **không** biết gì về node hay workflow.
- **`platform_core/credential.py`** giữ bí mật. Mô-đun này chỉ gọi vào đó.

## Dùng lại, không tự viết

`authlib` ≥ 1.6.9 (cài 1.8.0 trên máy này) lo hai thứ dễ làm sai:

- `authlib.oauth2.rfc7636.create_s256_code_challenge` — PKCE S256 (RFC 7636
  §4.2): base64url **không đệm** của SHA-256 của verifier. Cái đệm `=` là chỗ
  người ta sai, và sai thì Google trả `invalid_grant` không nói vì sao.
- `authlib.oauth2.client.OAuth2Client.create_authorization_url` — RFC 6749
  §4.1.1: thứ tự tham số, mã hoá URL, sinh `state`.

⛔ **Không** dùng `authlib.integrations.httpx_client`: bản 1.8.0 in
`AuthlibDeprecationWarning: The httpx module is deprecated; please use httpx2
instead` — nối vào một lớp tích hợp đang bị khai tử là tự hẹn một lần di trú.
Lượt POST tới điểm token đi thẳng bằng `httpx` (đã là phụ thuộc), và phần
"phân tích phản hồi token" là RFC 6749 §5.1: một JSON phẳng.

## Ba chỗ dễ mất tiền, viết ra để khỏi phải nhớ

1. **`access_type=offline` + `prompt=consent`.** Không có cặp này, Google chỉ
   phát `refresh_token` ở lần cấp quyền **đầu tiên** của một tài khoản. Lần thứ
   hai khách bấm "Kết nối lại" sẽ về một credential **không làm mới được**, và
   nó chỉ lộ ra một giờ sau.
2. **Lượt làm mới KHÔNG trả lại `refresh_token`.** Ghi đè bí mật bằng phản hồi
   làm mới là xoá mất đường sống của credential. `_hop_nhat` giữ lại.
3. **`invalid_grant` là dứt điểm**, không phải lỗi tạm: token đã bị thu hồi
   hoặc app còn ở chế độ Testing (refresh token hết hạn sau **7 ngày** — đã tra
   22/09, spec §9.3). ⇒ đặt `meta.can_ket_noi_lai`, để UI mời khách nối lại,
   ⛔ không thử lại trong im lặng.
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone

import httpx
from authlib.oauth2.client import OAuth2Client
from authlib.oauth2.rfc7636 import create_s256_code_challenge
from sqlalchemy.orm import Session

from platform_core import credential as kho_credential
from platform_core import secretbox
from platform_core.models import Credential, OAuthState

PROVIDER = "google"
DIEM_UY_QUYEN = "https://accounts.google.com/o/oauth2/v2/auth"
DIEM_TOKEN = "https://oauth2.googleapis.com/token"

#: Vòng đầu (spec §9.3). ⚠️ `youtube.upload` là scope **nhạy cảm**: app phải
#: được Google xác minh mới lên Production — việc của chủ dự án.
PHAM_VI_MAC_DINH = (
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
)

#: Spec §9.3. Một lượt uỷ quyền dài hơn ngần này là một tab khách để quên.
HAN_STATE = timedelta(minutes=10)

#: Verifier PKCE: 48 byte → 64 ký tự, nằm trong khoảng 43–128 của RFC 7636 §4.1.
DAI_VERIFIER = 48

ENV_CLIENT_ID = "LTT_GOOGLE_OAUTH_CLIENT_ID"
ENV_CLIENT_SECRET = "LTT_GOOGLE_OAUTH_CLIENT_SECRET"
ENV_REDIRECT_URI = "LTT_GOOGLE_OAUTH_REDIRECT_URI"


class LoiOAuth(Exception):
    """`ma` thuộc {chua_cau_hinh, state_khong_hop_le, state_het_han,
    invalid_grant, doi_token_that_bai}."""

    def __init__(self, ma: str, thong_bao: str = "") -> None:
        self.ma = ma
        super().__init__(thong_bao or ma)


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc)


def _aware(t: datetime | None) -> datetime | None:
    if t is not None and t.tzinfo is None:
        return t.replace(tzinfo=timezone.utc)
    return t


def _bam(state: str) -> str:
    return hashlib.sha256(str(state).encode("utf-8")).hexdigest()


def cau_hinh() -> tuple[str, str, str]:
    """`(client_id, client_secret, redirect_uri)` từ `secrets/app.env`.

    ⛔ Không có mặc định nào cho `client_secret`: một chuỗi rỗng đi tới Google
       trả về `invalid_client`, và người đọc log sẽ đi tìm lỗi ở chỗ khác.
       Fail-closed ngay, nói rõ thiếu biến nào.
    """
    cid = os.environ.get(ENV_CLIENT_ID, "").strip()
    secret = os.environ.get(ENV_CLIENT_SECRET, "").strip()
    redirect = os.environ.get(ENV_REDIRECT_URI, "").strip()
    thieu = [ten for ten, gt in ((ENV_CLIENT_ID, cid),
                                 (ENV_CLIENT_SECRET, secret),
                                 (ENV_REDIRECT_URI, redirect)) if not gt]
    if thieu:
        raise LoiOAuth("chua_cau_hinh",
                       f"thieu bien moi truong: {', '.join(thieu)}")
    return cid, secret, redirect


def bat_dau(db: Session, *, owner_id: str, redirect_after: str = "",
            pham_vi=None) -> tuple[str, str]:
    """Mở một lượt uỷ quyền. Trả `(url, state)`. ⛔ Nơi gọi phải `commit`.

    `state` **thô** chỉ đi ra ngoài (URL của Google). Trong CSDL chỉ có bản băm
    — cùng lý do với token waitpoint: thứ ta lưu đủ để **so khớp**, không đủ để
    **phát lại**.
    """
    cid, secret, redirect = cau_hinh()
    scope = list(pham_vi or PHAM_VI_MAC_DINH)
    from authlib.common.security import generate_token

    verifier = generate_token(DAI_VERIFIER)
    client = OAuth2Client(session=None, client_id=cid, client_secret=secret,
                          redirect_uri=redirect, scope=" ".join(scope),
                          code_challenge_method="S256")
    url, state = client.create_authorization_url(
        DIEM_UY_QUYEN, code_verifier=verifier,
        # ⭐ Xem docstring mô-đun, mục 1. Bỏ cặp này là mất `refresh_token`.
        access_type="offline", prompt="consent")
    db.add(OAuthState(
        state_hash=_bam(state), owner_id=str(owner_id), provider=PROVIDER,
        pkce_verifier_ma_hoa=secretbox.ma_hoa(verifier),
        redirect_after=str(redirect_after or "")[:500], pham_vi=scope,
        het_han_luc=_bay_gio() + HAN_STATE))
    db.flush()
    # ⚠️ Kiểm PKCE ngay ở đây chứ không tin URL: `create_s256_code_challenge`
    #    là thứ Google sẽ đối chiếu, và nếu nó không khớp verifier ta cất thì
    #    lỗi chỉ lộ ra ở bước đổi code — sau khi khách đã bấm đồng ý.
    assert create_s256_code_challenge(verifier) in url
    return url, state


def _lay_state(db: Session, state: str) -> OAuthState:
    hang = db.query(OAuthState).filter(
        OAuthState.state_hash == _bam(state)).one_or_none()
    if hang is None or hang.dung_luc is not None:
        # ⛔ Một `state` quay lại lần hai là **phát lại**, không phải một lần
        #    bấm F5 vô hại — và ta không phân biệt nó với "chưa từng có", đúng
        #    lý do `credential._hang` không phân biệt "không có" với "của
        #    người khác".
        raise LoiOAuth("state_khong_hop_le", "state khong hop le")
    if _aware(hang.het_han_luc) <= _bay_gio():
        raise LoiOAuth("state_het_han", "luot uy quyen da qua han")
    return hang


def noi_quay_ve(db: Session, *, state: str) -> str:
    """Nơi khách phải quay về sau khi nối xong. ⛔ Đọc TRƯỚC `hoan_tat`.

    ⭐ `hoan_tat` đánh dấu `state` đã dùng và xoá verifier — sau nó, hàng vẫn
       còn nhưng `_lay_state` sẽ từ chối. Hỏi sau là hỏi một cánh cửa đã khoá.
    """
    return str(_lay_state(db, state).redirect_after or "")


def _doi_token(goi_token, **tham) -> dict:
    """Gọi điểm token. `goi_token` để test cắm vào mà không đụng mạng."""
    if goi_token is not None:
        return dict(goi_token(**tham))
    try:
        r = httpx.post(DIEM_TOKEN, data=tham, timeout=30.0)
    except httpx.HTTPError as exc:
        raise LoiOAuth("doi_token_that_bai", type(exc).__name__) from exc
    try:
        goi = r.json()
    except ValueError as exc:
        raise LoiOAuth("doi_token_that_bai", f"HTTP {r.status_code}") from exc
    if r.status_code >= 400 or "error" in goi:
        ma = str(goi.get("error") or f"http_{r.status_code}")
        # RFC 6749 §5.2: `invalid_grant` là DỨT ĐIỂM, không phải lỗi tạm.
        raise LoiOAuth("invalid_grant" if ma == "invalid_grant"
                       else "doi_token_that_bai", ma)
    return goi


def _het_han_tu(goi: dict) -> datetime | None:
    giay = goi.get("expires_in")
    try:
        giay = int(giay)
    except (TypeError, ValueError):
        return None
    return _bay_gio() + timedelta(seconds=giay)


def _meta_tu(goi: dict, cu: dict | None = None) -> dict:
    """`meta` CÔNG KHAI. ⛔ Không `access_token`, không `refresh_token` —
    `credential._kiem_meta` chặn cơ học, đây chỉ là nơi không đưa chúng vào."""
    meta = dict(cu or {})
    meta.pop("can_ket_noi_lai", None)
    meta["pham_vi"] = str(goi.get("scope") or "")
    meta["token_type"] = str(goi.get("token_type") or "Bearer")
    return meta


def _hop_nhat(goi: dict, cu: dict | None = None) -> dict:
    """Bí mật mới. ⭐ Giữ `refresh_token` cũ khi phản hồi không mang cái mới —
    xem docstring mô-đun, mục 2."""
    cu = dict(cu or {})
    moi = {"access_token": str(goi.get("access_token") or ""),
           "token_type": str(goi.get("token_type") or "Bearer"),
           "refresh_token": str(goi.get("refresh_token")
                                or cu.get("refresh_token") or "")}
    return moi


def hoan_tat(db: Session, *, state: str, code: str, ten: str = "",
             goi_token=None) -> Credential:
    """Đổi `code` lấy token và cất thành credential `oauth2`."""
    cid, secret, redirect = cau_hinh()
    hang = _lay_state(db, state)
    verifier = secretbox.giai_ma(hang.pkce_verifier_ma_hoa)
    goi = _doi_token(goi_token, grant_type="authorization_code", code=str(code),
                     client_id=cid, client_secret=secret,
                     redirect_uri=redirect, code_verifier=verifier)
    # ⭐ Đánh dấu ĐÃ DÙNG trước khi tạo credential: nếu bước sau ném, `state`
    #    vẫn phải chết. Một `state` sống sót sau một lần đổi là một lần phát lại.
    hang.dung_luc = _bay_gio()
    hang.pkce_verifier_ma_hoa = ""
    c = kho_credential.tao(
        db, owner_id=hang.owner_id, kieu="oauth2", nha_cung_cap=PROVIDER,
        ten=str(ten or "Google"), bi_mat=_hop_nhat(goi),
        pham_vi=list(hang.pham_vi or []), meta=_meta_tu(goi),
        het_han_luc=_het_han_tu(goi))
    return c


def bo_lam_moi(goi_token=None):
    """Callable `lam_moi` cho `credential.lay_de_dung` (spec §9.3).

    ⭐ Trả về một hàm thay vì để `credential.py` gọi thẳng vào đây: kho
       credential **không được** biết tên một nhà cung cấp nào. Nhà cung cấp
       thứ hai sẽ là một mô-đun thứ hai, không phải một câu `if`.
    """
    def lam_moi(bi_mat, c: Credential):
        cid, secret, _redirect = cau_hinh()
        refresh = (bi_mat or {}).get("refresh_token") if isinstance(
            bi_mat, dict) else ""
        if not refresh:
            raise LoiOAuth("invalid_grant", "credential khong co refresh token")
        try:
            goi = _doi_token(goi_token, grant_type="refresh_token",
                             refresh_token=refresh, client_id=cid,
                             client_secret=secret)
        except LoiOAuth as exc:
            if exc.ma != "invalid_grant":
                raise
            # ⭐ Dứt điểm (docstring mô-đun, mục 3): Google đã từ chối chính
            #    `refresh_token`. Thử lại là gọi lại để bị từ chối lại.
            from sqlalchemy.orm import object_session

            phien = object_session(c)
            if phien is not None:
                danh_dau_can_ket_noi_lai(phien, c)
            raise kho_credential.LoiCredential(
                "credential_bi_thu_hoi",
                "Google tu choi refresh token — khach phai ket noi lai") from exc
        return (_hop_nhat(goi, bi_mat), _meta_tu(goi, c.meta),
                _het_han_tu(goi))
    return lam_moi


def danh_dau_can_ket_noi_lai(db: Session, c: Credential) -> None:
    """`invalid_grant` ⇒ credential này chết cho tới khi khách nối lại.

    ⛔ Không xoá hàng: khách phải thấy nó trong danh sách với một nút "Kết nối
       lại". Một credential biến mất im lặng là một workflow hỏng không có
       nguyên nhân.
    """
    meta = dict(c.meta or {})
    meta["can_ket_noi_lai"] = True
    c.meta = meta
    c.thu_hoi_luc = _bay_gio()
    c.bi_mat_ma_hoa = ""
    c.preview = ""
    c.updated_at = c.thu_hoi_luc


def don_state_het_han(db: Session) -> int:
    """Xoá các lượt uỷ quyền đã quá hạn. Gọi từ vòng bảo trì của worker.

    ⭐ Hàng quá hạn mang một **PKCE verifier đã mã hoá** không ai còn cần —
       giữ nó lại là giữ một bí mật quá hạn sử dụng của chính nó.
    """
    hang = (db.query(OAuthState)
            .filter(OAuthState.het_han_luc <= _bay_gio()).all())
    for h in hang:
        db.delete(h)
    return len(hang)


__all__ = ["DIEM_TOKEN", "DIEM_UY_QUYEN", "HAN_STATE", "LoiOAuth",
           "PHAM_VI_MAC_DINH", "PROVIDER", "bat_dau", "bo_lam_moi",
           "cau_hinh", "danh_dau_can_ket_noi_lai", "don_state_het_han",
           "hoan_tat"]
