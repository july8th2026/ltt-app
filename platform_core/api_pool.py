"""
api_pool.py — cấp phát API key (H8). App xin key ở đây theo (provider, category,
model); nền tảng chọn key khả dụng, đếm tải (rpm/tpm/token) và đánh dấu lỗi để tự
nghỉ/tắt.

KHÁC hàng đợi job: một API key CHIA SẺ được cho nhiều request đồng thời, nên
KHÔNG cần khoá độc quyền (`FOR UPDATE`) — chỉ chọn theo priority rồi cập nhật
trạng thái. Không tự commit (caller quyết định transaction).

Pha 2 thêm:
- **Telemetry rpm/tpm/token** — cửa sổ cố định 60s ngay trong hàng: allocator bỏ
  qua key đã chạm `rpm_limit`/`tpm_limit` trong cửa sổ hiện tại, tự reset khi quá
  hạn. `danh_dau_thanh_cong(..., tokens=)` kế toán token.
- **Cascade đa-provider** — `chon_key(category=..., thu_tu_provider=[...])` gom key
  MỌI provider phục vụ category, nên một provider cạn key KHÔNG làm chết cả loại.

Phân loại lỗi (học BOT GEMINI, đã kiểm chứng ở đó):
- 401/403 → auth_error; cooldown ngắn, DISABLE sau `AUTH_DISABLE_THRESHOLD` lần
  liên tiếp (chống một key hỏng làm chết mọi request);
- 429     → cooldown theo retry-after (mặc định `DEFAULT_COOLDOWN_S`);
- 4xx khác → LỖI CỦA TA (bad request) → KHÔNG phạt key;
- 5xx/mạng → error; sang trạng thái error sau nhiều lần.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from platform_core.models import (APIKEY_ACTIVE, APIKEY_COOLDOWN,
                                  APIKEY_DISABLED, APIKEY_ERROR, ApiKey)

AUTH_DISABLE_THRESHOLD = 5
DEFAULT_COOLDOWN_S = 60
ERROR_TO_STATUS_THRESHOLD = 5
WINDOW_S = 60          # cửa sổ đo rpm/tpm (giây)


class ThieuKeyError(Exception):
    """Không có API key khả dụng cho yêu cầu — app phải báo lỗi rõ, không gọi API."""


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _cuon_cua_so(key: ApiKey, now: datetime) -> None:
    """Reset cửa sổ đếm khi đã quá `WINDOW_S`. Gọi trước khi đọc/tăng bộ đếm."""
    ws = _aware(key.window_start)
    if ws is None or (now - ws).total_seconds() >= WINDOW_S:
        key.window_start = now
        key.window_requests = 0
        key.window_tokens = 0


def _dinh_muc_con(key: ApiKey) -> bool:
    """True nếu key CÒN quota trong cửa sổ hiện tại (đã cuộn cửa sổ trước khi gọi)."""
    if key.rpm_limit and key.window_requests >= key.rpm_limit:
        return False
    if key.tpm_limit and key.window_tokens >= key.tpm_limit:
        return False
    return True


#: ── PHẠM VI CẤP KHOÁ (H43/Q120, O15) ────────────────────────────────────────
#:
#: 🔴 VÌ SAO PHẢI CÓ, VÀ VÌ SAO NÓ TỪNG LÀ MỘT LỖ.
#:
#:    `ApiKey.owner_user_id` tồn tại từ migration đầu tiên của bảng này
#:    (`20260731_1600_them_bang_api_keys.py:24`, có index) và được `tao_key()`
#:    ghi. Nhưng **không nơi nào ĐỌC nó** — `_ung_vien` lọc theo enabled/status/
#:    categories/supported_models/rpm/tpm và không hề lọc theo chủ sở hữu. Nghĩa
#:    là một khoá RIÊNG của khách sẽ được cấp cho lượt gọi của bất kỳ ai.
#:
#: ⭐ Hôm nay điều đó **chưa** rò rỉ, và nói cho đúng thì phải nói rõ vì sao:
#:    không đường ghi nào trong kho đặt `owner_user_id`. Trang admin
#:    (`server/admin.py:734`) không truyền tham số đó, hai công cụ nạp khoá cũng
#:    không. Nên mọi dòng đang tồn tại đều mang chuỗi rỗng.
#:
#: ⇒ Định nghĩa rỗng = POOL NỀN TẢNG là **thiết lập** ngữ nghĩa cho một cột chưa
#:   có ngữ nghĩa, không phải diễn giải lại một cột đang có. Không dòng nào đổi
#:   hành vi, nên hợp đồng O15 ("tương thích ngược") được giữ nguyên vẹn.
PHAM_VI_POOL = "platform_pool"     # khoá của nền tảng, dùng chung
PHAM_VI_RIENG = "user_owned"       # khoá do chính người dùng cung cấp
PHAM_VI_HOP_LE = frozenset({PHAM_VI_POOL, PHAM_VI_RIENG})


class PhamViError(ValueError):
    """Yêu cầu cấp khoá có phạm vi không hợp lệ. Fail-closed."""


def _ung_vien(db: DbSession, now: datetime, *, providers: Optional[Sequence[str]],
              category: Optional[str], model: Optional[str],
              pham_vi: str = PHAM_VI_POOL,
              owner_user_id: str = "") -> list:
    """Gom key khả dụng (tự hồi cooldown + cuộn cửa sổ). Lọc provider/category/model
    và bỏ key đã chạm rpm/tpm. KHÔNG sắp xếp — caller quyết thứ tự.

    🔑 Phép lọc chủ sở hữu chạy **trong câu truy vấn**, trước mọi phép xếp hạng.
       Đặt nó ở đây chứ không ở chỗ gọi vì một lý do: chủ sở hữu hiệu lực phải
       được biết **TRƯỚC KHI CHỌN** (Prompt 07 mục 3). Lọc sau khi chọn nghĩa là
       đã có một lượt chọn sai xảy ra rồi mới sửa, và một ngày nào đó ai đó sẽ
       quên bước sửa.
    """
    stmt = select(ApiKey).where(ApiKey.enabled.is_(True))
    if providers:
        stmt = stmt.where(ApiKey.provider.in_(list(providers)))

    if pham_vi == PHAM_VI_RIENG:
        # ⛔ KHÔNG BAO GIỜ rơi về pool nền tảng. Khách chọn khoá riêng là để
        #    hạn mức và hoá đơn thuộc về họ; lặng lẽ dùng khoá nhà là tiêu tiền
        #    của nền tảng cho một yêu cầu đã nói rõ không muốn thế.
        stmt = stmt.where(ApiKey.owner_user_id == owner_user_id)
    else:
        # Pool nền tảng KHÔNG bao giờ chạm khoá riêng của ai (I7).
        stmt = stmt.where(ApiKey.owner_user_id == "")

    rows = db.execute(stmt).scalars().all()

    out = []
    for k in rows:
        # Tự hồi cooldown đã hết hạn.
        if k.status == APIKEY_COOLDOWN and k.cooldown_until and _aware(k.cooldown_until) <= now:
            k.status = APIKEY_ACTIVE
            k.cooldown_until = None
        if k.status != APIKEY_ACTIVE:
            continue
        if category and k.categories and category not in k.categories:
            continue
        if model and k.supported_models and model not in k.supported_models:
            continue
        _cuon_cua_so(k, now)
        if not _dinh_muc_con(k):
            continue          # đã chạm rpm/tpm trong cửa sổ này -> tạm bỏ
        out.append(k)
    return out


def chon_key(db: DbSession, *, category: Optional[str] = None,
             model: Optional[str] = None,
             thu_tu_provider: Optional[Sequence[str]] = None,
             loai_tru: Optional[Sequence[str]] = None,
             pham_vi: str = PHAM_VI_POOL,
             owner_user_id: str = "") -> ApiKey:
    """Chọn một API key khả dụng cho `category` (tuỳ `model`), CASCADE nhiều provider.

    `thu_tu_provider`: thứ tự ưu tiên provider (vd ["gemini","apiai"]); None = xét
    mọi provider. Xếp: provider theo thứ tự cho trước → `priority` cao → `health`
    cao → ít tải nhất (cửa sổ) → ít dùng nhất. Raise `ThieuKeyError` nếu cạn.

    `loai_tru`: id các key **đã thử và hỏng trong chính lượt gọi này**. Xem
    `thu_lan_luot()` để biết vì sao cần.
    """
    if pham_vi not in PHAM_VI_HOP_LE:
        raise PhamViError(f"pham vi cap khoa khong hop le: {pham_vi!r}")
    owner_user_id = (owner_user_id or "").strip()
    if pham_vi == PHAM_VI_RIENG and not owner_user_id:
        # Fail-closed. Xin khoá riêng mà không nói của ai thì câu trả lời đúng là
        # từ chối — nếu đoán, đường đoán an toàn nhất vẫn là cấp một khoá của
        # người khác hoặc của nền tảng, tức đúng hai thứ bất biến I7 cấm.
        raise PhamViError("pham vi user_owned bat buoc phai co owner_user_id")

    order = [(p or "").strip().lower() for p in (thu_tu_provider or []) if p]
    bo_qua = {str(x) for x in (loai_tru or [])}
    now = _bay_gio()
    ung_vien = _ung_vien(db, now, providers=(order or None),
                         category=category, model=model,
                         pham_vi=pham_vi, owner_user_id=owner_user_id)
    if bo_qua:
        ung_vien = [k for k in ung_vien if k.id not in bo_qua]
    if not ung_vien:
        raise ThieuKeyError(
            f"khong co API key kha dung: pham_vi={pham_vi} "
            f"providers={order or 'moi'} category={category} model={model}")

    def _rank_prov(p: str) -> int:
        if not order:
            return 0
        try:
            return order.index(p)
        except ValueError:
            return len(order)

    ung_vien.sort(key=lambda k: (_rank_prov(k.provider), -k.priority,
                                 -k.health_score, k.window_requests, k.total_requests))
    chon = ung_vien[0]
    chon.last_used_at = now
    chon.total_requests += 1
    _cuon_cua_so(chon, now)      # bảo đảm cửa sổ hợp lệ trước khi tăng
    chon.window_requests += 1
    db.flush()
    return chon


def lay_key(db: DbSession, provider: str, *, category: Optional[str] = None,
            model: Optional[str] = None,
            loai_tru: Optional[Sequence[str]] = None,
            pham_vi: str = PHAM_VI_POOL,
            owner_user_id: str = "") -> ApiKey:
    """Chọn key cho MỘT provider cụ thể (tương thích Pha 1). Nội bộ gọi `chon_key`
    với thứ tự provider = [provider], nên rpm/tpm/telemetry áp dụng như nhau."""
    provider = (provider or "").strip().lower()
    return chon_key(db, category=category, model=model,
                    thu_tu_provider=[provider], loai_tru=loai_tru,
                    pham_vi=pham_vi, owner_user_id=owner_user_id)


def thu_lan_luot(db: DbSession, *, provider: Optional[str] = None,
                 category: Optional[str] = None, model: Optional[str] = None,
                 so_lan: int = 3,
                 pham_vi: str = PHAM_VI_POOL,
                 owner_user_id: str = ""):
    """Sinh lần lượt các key khả dụng, **không bao giờ trả lại key đã thử**.

        for key in api_pool.thu_lan_luot(db, provider="gemini", category="image"):
            try:
                return goi_nha_cung_cap(key)
            except LoiCoTheThuLai as e:
                api_pool.danh_dau_loi(db, key, http_status=e.status)
        raise RuntimeError("het key")

    ⛔ VÌ SAO CẦN — KHOẢNG TRỐNG THẬT SO VỚI LiteLLM Router.

       Hôm nay **không có chuỗi thử lại nào**. `apps/taoanh/jobs.py` lấy key **một
       lần** trước vòng lặp ảnh; key đó cạn hạn mức ở ảnh thứ hai thì **cả job
       hỏng**, dù tài khoản còn ba key Gemini khác đang rảnh. Khách mất một job vì
       hết quota của *một tài khoản*, không phải vì hết quota.

       LiteLLM Router loại deployment vừa hỏng khỏi **các bước sau của cùng một
       request**, và loại trừ **tích luỹ** qua từng bước — nên nó không bao giờ
       quay lại thứ vừa chết.

    ⭐ RANH GIỚI PHẢI GIỮ (D-042): đây là dự phòng ở tầng **TÀI KHOẢN**, không phải
       tầng **sản phẩm**. Khách gọi `gemini-3-pro-image` thì vẫn nhận đúng model
       đó — ta chỉ đổi **khoá nào** của Gemini phục vụ lượt gọi. Đừng dùng hàm này
       để nhảy sang một model khác: đó là đánh tráo sản phẩm.

    ⚠️ Bên gọi **phải** gọi `danh_dau_loi()` khi một key hỏng. Không gọi thì key đó
       vẫn `active`, và lượt sau lại chọn đúng nó — vòng lặp này chỉ tránh lặp
       *trong một lượt*, nó không thay việc ghi nhận sức khoẻ.
    """
    da_thu: list[str] = []
    for _ in range(max(1, int(so_lan))):
        try:
            key = (lay_key(db, provider, category=category, model=model,
                           loai_tru=da_thu, pham_vi=pham_vi,
                           owner_user_id=owner_user_id)
                   if provider else
                   chon_key(db, category=category, model=model, loai_tru=da_thu,
                            pham_vi=pham_vi, owner_user_id=owner_user_id))
        except ThieuKeyError:
            return          # het key kha dung -> dung, khong nem
        da_thu.append(key.id)
        yield key


def danh_dau_thanh_cong(db: DbSession, key: ApiKey, *, tokens: int = 0) -> None:
    key.total_success += 1
    key.error_count = 0
    key.auth_error_count = 0
    key.health_score = min(100, key.health_score + 5)
    if tokens:
        now = _bay_gio()
        _cuon_cua_so(key, now)
        key.window_tokens += int(tokens)
        key.total_tokens += int(tokens)
    if key.status == APIKEY_ERROR:
        key.status = APIKEY_ACTIVE
    db.flush()


def danh_dau_loi(db: DbSession, key: ApiKey, *, http_status: Optional[int] = None,
                 retry_after_s: Optional[int] = None, message: str = "") -> None:
    key.total_failed += 1
    key.last_error = (message or "")[:500]
    s = http_status

    if s in (401, 403):
        key.auth_error_count += 1
        key.health_score = max(0, key.health_score - 10)
        if key.auth_error_count >= AUTH_DISABLE_THRESHOLD:
            key.status = APIKEY_DISABLED       # hỏng thật -> tắt hẳn, chờ admin
        else:
            key.status = APIKEY_COOLDOWN       # có thể chỉ trục trặc tạm
            key.cooldown_until = _bay_gio() + timedelta(seconds=DEFAULT_COOLDOWN_S)
    elif s == 429:
        cd = int(retry_after_s) if retry_after_s else DEFAULT_COOLDOWN_S
        key.status = APIKEY_COOLDOWN
        key.cooldown_until = _bay_gio() + timedelta(seconds=cd)
        key.health_score = max(0, key.health_score - 5)
    elif s is not None and 400 <= s < 500:
        # Bad request CỦA TA — không phải lỗi của key. KHÔNG phạt.
        pass
    else:
        # 5xx hoặc lỗi mạng.
        key.error_count += 1
        key.health_score = max(0, key.health_score - 10)
        if key.error_count >= ERROR_TO_STATUS_THRESHOLD:
            key.status = APIKEY_ERROR
    db.flush()


def rpm(key: ApiKey, *, now: Optional[datetime] = None) -> int:
    """Số request trong cửa sổ 60s hiện tại (0 nếu cửa sổ đã cũ)."""
    now = now or _bay_gio()
    ws = _aware(key.window_start)
    if ws is None or (now - ws).total_seconds() >= WINDOW_S:
        return 0
    return key.window_requests


def tpm(key: ApiKey, *, now: Optional[datetime] = None) -> int:
    """Số token trong cửa sổ 60s hiện tại (0 nếu cửa sổ đã cũ)."""
    now = now or _bay_gio()
    ws = _aware(key.window_start)
    if ws is None or (now - ws).total_seconds() >= WINDOW_S:
        return 0
    return key.window_tokens


def pham_vi_cua(key: ApiKey) -> str:
    """Phạm vi thực tế của một khoá, suy từ DỮ LIỆU chứ không từ lời gọi."""
    return PHAM_VI_RIENG if (key.owner_user_id or "").strip() else PHAM_VI_POOL


def mo_ta_an_toan(key: ApiKey) -> dict:
    """Mô tả một khoá cho log/telemetry/màn admin — KHÔNG BAO GIỜ có bí mật.

    ⛔ Không có `credential`, không có `credential_enc`. `key_preview` do
       `secretbox.preview()` sinh ra và vốn được thiết kế để in ra được; mọi thứ
       còn lại ở đây là siêu dữ liệu.

    ⭐ Có hàm này để nơi gọi khỏi phải tự dựng một dict — và mỗi lần tự dựng là
       một cơ hội cho `credential` lọt vào một dòng log. Bất biến I16 nói "không
       bí mật thô nào bị ghi lại"; cách giữ nó là làm cho đường đúng thành đường
       sẵn có.

    `chu_so_huu` rút gọn còn 8 ký tự: đủ để đối chiếu hai dòng log với nhau,
    không đủ để dùng làm định danh ở chỗ khác.
    """
    chu = (key.owner_user_id or "").strip()
    return {
        "key_id": key.id,
        "provider": key.provider,
        "pham_vi": pham_vi_cua(key),
        "chu_so_huu": (chu[:8] + "…") if chu else "",
        "preview": key.key_preview or "",
        "status": key.status,
        "health": key.health_score,
        "rpm": rpm(key),
        "tpm": tpm(key),
    }
