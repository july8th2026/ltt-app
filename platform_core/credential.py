"""Kho credential của khách — spec §9. **Một cửa duy nhất** vào bí mật.

🔴 VÌ SAO CÓ MÔ-ĐUN NÀY (và vì sao `core.http` bị khoá tới 24/09/2026)

   Trước hôm nay, chỗ duy nhất một workflow cất được header `Authorization` là
   `params` của node — tức **bên trong `workflow_version`**. Bảng ấy được nhân
   bản khi khách "Save as", được trả nguyên vẹn cho trình soạn thảo, và đi theo
   mọi bản xuất. Một bí mật nằm trong một bản ghi **thiết kế để đem đi chỗ
   khác** là một bí mật đã rò, chỉ là chưa ai đọc.

   ⇒ Workflow chỉ lưu `credential_ref`. Bí mật sống ở bảng `credential`, mã hoá
   at-rest, và **chỉ tiến trình job** mới gọi `lay_de_dung`.

## Ranh giới — ⛔ đọc trước khi thêm hàm vào đây

- **Động cơ, validator, API không bao giờ giải mã.** Validator dùng `kiem_ref`
  (chỉ hỏi *"ref này có hợp lệ với chủ workflow không"*); API dùng `liet_ke`
  (chỉ `preview` + `meta`). Đúng một hàm trả bản rõ, và tên nó nói rõ nó dành
  cho ai: `lay_de_dung`.
- **`meta` là công khai.** Nó ra tới trình duyệt. Một `refresh_token` lọt vào
  `meta` là một bí mật nằm **ngoài** lớp mã hoá — `_kiem_meta` chặn cơ học,
  không bằng lời dặn.
- **Thu hồi là XOÁ bí mật**, không phải `enabled = False`. Một cờ thì có ngày
  bị ai đó lật lại; một cột rỗng thì không.

## Hình dạng bí mật

`bi_mat_ma_hoa` giữ **một chuỗi JSON đã mã hoá**, không phải chuỗi thô: một
credential `basic` có hai phần, một `oauth2` có ba (access/refresh/token_type).
Một kho chỉ chứa nổi một chuỗi thì `oauth2` sẽ phải nhét token thứ hai vào
`meta` — tức ra ngoài lớp mã hoá. Đó là lý do lớp bọc này có từ đầu, không đợi
tới lúc làm OAuth.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from platform_core import secretbox
from platform_core.models import Credential, CredentialNhatKy

#: Danh sách ĐÓNG (spec §9.1). Một `kieu` lạ là một credential mà không node
#: nào biết tiêm ra sao — nó sẽ ngồi trong kho tới khi có người debug.
KIEU = ("api_key", "bearer", "basic", "oauth2", "google_service_account",
        "piece_custom")

#: Hành động ghi nhật ký. Cũng là danh sách đóng, cùng lý do.
HANH_DONG = ("tao", "sua", "thu_hoi", "lam_moi", "dung")

#: Khoá bị cấm xuất hiện trong `meta` — ⛔ cơ học, không phải lời dặn. Mỗi khoá
#: ở đây là một chỗ một bí mật **đã từng** bị nhét nhầm vào ô công khai.
META_CAM = ("access_token", "refresh_token", "client_secret", "password",
            "api_key", "private_key", "secret", "bi_mat")

#: Làm mới token OAuth khi còn dưới ngần này (spec §9.3). Không phải "khi đã
#: hết hạn": một job bắt đầu lúc T và gọi API lúc T+2 phút thì token hợp lệ lúc
#: kiểm đã chết lúc dùng.
LE_LAM_MOI = timedelta(minutes=5)


class LoiCredential(Exception):
    """`ma` thuộc {khong_thay, credential_bi_thu_hoi, kieu_sai, meta_co_bi_mat,
    het_han, lam_moi_that_bai}."""

    def __init__(self, ma: str, thong_bao: str = "") -> None:
        self.ma = ma
        super().__init__(thong_bao or ma)


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc)


def _aware(t: datetime | None) -> datetime | None:
    """SQLite trả `datetime` **naive** cho cột `DateTime(timezone=True)`.

    ⚠️ So một naive với một aware ném `TypeError`, và nó ném ở **đường làm mới
       token** — tức lúc một job của khách đang chạy. Chuẩn hoá ở một chỗ."""
    if t is not None and t.tzinfo is None:
        return t.replace(tzinfo=timezone.utc)
    return t


def _kiem_meta(meta: dict) -> dict:
    meta = dict(meta or {})
    xau = sorted(k for k in meta if str(k).lower() in META_CAM)
    if xau:
        raise LoiCredential(
            "meta_co_bi_mat",
            f"`meta` la o CONG KHAI, khong duoc mang: {xau}")
    return meta


def _ghi_nhat_ky(db: Session, cred_id: str, hanh_dong: str, *,
                 run_id: str = "", node_id: str = "") -> None:
    if hanh_dong not in HANH_DONG:
        raise LoiCredential("kieu_sai", f"hanh dong la: {hanh_dong!r}")
    db.add(CredentialNhatKy(credential_id=cred_id, hanh_dong=hanh_dong,
                            run_id=str(run_id or ""),
                            node_id=str(node_id or "")))


def _dong_goi(bi_mat) -> str:
    """Bí mật (chuỗi hoặc dict) thành chuỗi JSON để mã hoá."""
    if isinstance(bi_mat, dict):
        return json.dumps(bi_mat, ensure_ascii=False, sort_keys=True)
    return json.dumps({"gia_tri": str(bi_mat)}, ensure_ascii=False)


def _mo_goi(tho: str):
    goi = json.loads(tho)
    if isinstance(goi, dict) and set(goi) == {"gia_tri"}:
        return goi["gia_tri"]
    return goi


def _preview(bi_mat) -> str:
    chuoi = bi_mat if isinstance(bi_mat, str) else json.dumps(
        bi_mat, sort_keys=True)
    return secretbox.preview(chuoi)


def tao(db: Session, *, owner_id: str, kieu: str, nha_cung_cap: str = "",
        ten: str = "", bi_mat, pham_vi=(), meta: dict | None = None,
        het_han_luc: datetime | None = None) -> Credential:
    """Tạo một credential. `bi_mat` là chuỗi hoặc dict (xem docstring mô-đun)."""
    if kieu not in KIEU:
        raise LoiCredential("kieu_sai", f"kieu khong duoc phep: {kieu!r}")
    c = Credential(
        owner_id=str(owner_id), kieu=kieu, nha_cung_cap=str(nha_cung_cap or ""),
        ten=str(ten or ""), bi_mat_ma_hoa=secretbox.ma_hoa(_dong_goi(bi_mat)),
        preview=_preview(bi_mat), pham_vi=list(pham_vi or []),
        meta=_kiem_meta(meta or {}), het_han_luc=het_han_luc)
    db.add(c)
    db.flush()
    _ghi_nhat_ky(db, c.id, "tao")
    return c


def _hang(db: Session, ref: str, owner_id: str, *,
          khoa: bool = False) -> Credential:
    """Một hàng của ĐÚNG chủ đó, hoặc `khong_thay`.

    ⛔ Không phân biệt "không có" với "của người khác": phân biệt hai ca đó là
       một máy đếm cho người ngoài biết id nào tồn tại (cùng bài với
       `public_api/keys.py`).
    """
    q = db.query(Credential).filter(Credential.id == str(ref),
                                    Credential.owner_id == str(owner_id))
    if khoa:
        # `FOR UPDATE` (spec §9.3): hai job cùng chạm một credential OAuth thì
        # một người làm mới, người kia đọc token mới — không phải cả hai cùng
        # gọi Google và người thua ghi đè token của người thắng.
        # SQLite không có `FOR UPDATE`; `with_for_update` bị bỏ qua ở đó, và
        # đó là chấp nhận được vì SQLite không phải production.
        q = q.with_for_update()
    c = q.one_or_none()
    if c is None:
        raise LoiCredential("khong_thay", "credential khong ton tai")
    return c


def kiem_ref(db: Session, ref: str, *, owner_id: str,
             kieu_cho_phep=()) -> Credential:
    """Validator lúc **publish** (spec §9.1). ⛔ Không giải mã gì cả.

    Ba điều kiện của spec, đúng thứ tự người soạn gặp: ref thuộc chủ workflow,
    chưa thu hồi, `kieu` nằm trong `NodeDefinition.credential`.
    """
    c = _hang(db, ref, owner_id)
    if c.thu_hoi_luc is not None:
        raise LoiCredential("credential_bi_thu_hoi", "credential da thu hoi")
    if kieu_cho_phep and c.kieu not in tuple(kieu_cho_phep):
        raise LoiCredential(
            "kieu_sai",
            f"node nay nhan {tuple(kieu_cho_phep)}, credential la {c.kieu!r}")
    return c


def liet_ke(db: Session, owner_id: str) -> list[dict]:
    """Bề mặt CÔNG KHAI. ⛔ Liệt kê tường minh từng khoá — một cột mới thêm vào
    `Credential` không được tự chảy ra Internet (cùng luật
    `palette_v3.sang_json`)."""
    hang = (db.query(Credential)
            .filter(Credential.owner_id == str(owner_id))
            .order_by(Credential.created_at.desc()).all())
    return [{"id": c.id, "kieu": c.kieu, "nha_cung_cap": c.nha_cung_cap,
             "ten": c.ten, "preview": c.preview,
             "pham_vi": list(c.pham_vi or []), "meta": dict(c.meta or {}),
             "het_han_luc": c.het_han_luc, "thu_hoi_luc": c.thu_hoi_luc,
             "dung_lan_cuoi": c.dung_lan_cuoi, "created_at": c.created_at}
            for c in hang]


def thay_bi_mat(db: Session, ref: str, *, owner_id: str, bi_mat,
                meta: dict | None = None) -> Credential:
    c = _hang(db, ref, owner_id)
    if c.thu_hoi_luc is not None:
        raise LoiCredential("credential_bi_thu_hoi", "credential da thu hoi")
    c.bi_mat_ma_hoa = secretbox.ma_hoa(_dong_goi(bi_mat))
    c.preview = _preview(bi_mat)
    if meta is not None:
        c.meta = _kiem_meta(meta)
    c.updated_at = _bay_gio()
    _ghi_nhat_ky(db, c.id, "sua")
    return c


def thu_hoi(db: Session, ref: str, *, owner_id: str) -> Credential:
    """Thu hồi = **xoá bí mật** + đóng dấu thời gian (spec §9.1)."""
    c = _hang(db, ref, owner_id)
    c.bi_mat_ma_hoa = ""
    c.preview = ""
    c.thu_hoi_luc = _bay_gio()
    c.updated_at = c.thu_hoi_luc
    _ghi_nhat_ky(db, c.id, "thu_hoi")
    return c


def lay_de_dung(db: Session, ref: str, *, owner_id: str, run_id: str = "",
                node_id: str = "", lam_moi=None):
    """⭐ **Hàm DUY NHẤT trả bản rõ.** Chỉ tiến trình job được gọi (spec §9.4).

    `lam_moi` là một callable `(bi_mat, credential) -> (bi_mat_moi, meta_moi,
    het_han_moi)` do lớp OAuth truyền vào — ⛔ mô-đun này **không** biết gì về
    Google, và không được biết: kho credential mà nhập khẩu một nhà cung cấp cụ
    thể thì nhà cung cấp thứ hai sẽ được thêm bằng một câu `if`.
    """
    c = _hang(db, ref, owner_id, khoa=True)
    if c.thu_hoi_luc is not None or not c.bi_mat_ma_hoa:
        raise LoiCredential("credential_bi_thu_hoi", "credential da thu hoi")
    bi_mat = _mo_goi(secretbox.giai_ma(c.bi_mat_ma_hoa))

    het_han = _aware(c.het_han_luc)
    if het_han is not None and het_han <= _bay_gio() + LE_LAM_MOI:
        if lam_moi is None:
            raise LoiCredential("het_han", "credential het han")
        try:
            bi_mat, meta_moi, het_han_moi = lam_moi(bi_mat, c)
        except LoiCredential:
            raise
        except Exception as exc:                      # nguồn ngoài, mọi thứ
            raise LoiCredential(
                "lam_moi_that_bai", f"{type(exc).__name__}") from exc
        c.bi_mat_ma_hoa = secretbox.ma_hoa(_dong_goi(bi_mat))
        c.preview = _preview(bi_mat)
        c.meta = _kiem_meta(meta_moi or {})
        c.het_han_luc = het_han_moi
        c.updated_at = _bay_gio()
        _ghi_nhat_ky(db, c.id, "lam_moi", run_id=run_id, node_id=node_id)
        # ⭐ "commit ngắn" của spec §9.3: nhả khoá hàng NGAY, đừng giữ nó suốt
        #    lượt gọi HTTP của node. Một `FOR UPDATE` giữ qua một request mạng
        #    là một hàng đợi trá hình.
        db.commit()

    c.dung_lan_cuoi = _bay_gio()
    _ghi_nhat_ky(db, c.id, "dung", run_id=run_id, node_id=node_id)
    return bi_mat


def xoay_khoa(db: Session) -> int:
    """Mã hoá lại **mọi** hàng bằng khoá đời mới. Trả số hàng đã xoay.

    ⛔ Bản rõ không bao giờ thành một biến ở đây: `secretbox.xoay` dùng
       `MultiFernet.rotate`. Công cụ dòng lệnh: `tools/xoay_khoa_credential.py`.
    """
    dem = 0
    for c in db.query(Credential).filter(Credential.bi_mat_ma_hoa != "").all():
        c.bi_mat_ma_hoa = secretbox.xoay(c.bi_mat_ma_hoa)
        dem += 1
    return dem


__all__ = ["HANH_DONG", "KIEU", "LE_LAM_MOI", "LoiCredential", "META_CAM",
           "kiem_ref", "lay_de_dung", "liet_ke", "tao", "thay_bi_mat",
           "thu_hoi", "xoay_khoa"]
